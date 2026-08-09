from __future__ import annotations

from datetime import UTC, datetime, timedelta


def telemetry_batch(
    *,
    key: str,
    recorded_at: datetime,
    value: float = 327.4,
    unit: str = "A",
    metric: str = "motor_current_amps",
    source_id: str = "telemetry-crusher-01",
    asset_id: str = "primary-crusher-01",
) -> dict:
    timestamp = recorded_at.isoformat().replace("+00:00", "Z")
    return {
        "contract_version": "1.0",
        "source": {
            "source_id": source_id,
            "source_type": "telemetry",
            "received_via": "api",
        },
        "observations": [
            {
                "idempotency_key": key,
                "observed_at": timestamp,
                "asset_ref": {"site_id": "sonoran-west", "asset_id": asset_id},
                "kind": "telemetry",
                "metric": metric,
                "value": value,
                "unit": unit,
                "source_recorded_at": timestamp,
                "attributes": {"sample_interval_seconds": 60},
            }
        ],
    }


def ingest(client, body: dict, key: str = "batch-1"):
    return client.post(
        "/api/v1/ingestion/observations", json=body, headers={"Idempotency-Key": key}
    )


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_allows_configured_local_web_origin(client) -> None:
    response = client.options(
        "/api/v1/incidents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_ingests_observations_and_exposes_asset_and_read_model(client) -> None:
    now = datetime.now(UTC) - timedelta(seconds=30)
    response = ingest(client, telemetry_batch(key="reading-1", recorded_at=now))

    assert response.status_code == 201
    payload = response.json()
    assert payload["accepted_count"] == 1
    assert payload["flagged_count"] == 0
    assert payload["observations"][0]["quality_status"] == "accepted"

    assets = client.get("/api/v1/assets")
    assert assets.status_code == 200
    assert assets.json()["items"] == [{"site_id": "sonoran-west", "asset_id": "primary-crusher-01"}]

    observations = client.get("/api/v1/observations", params={"asset_id": "primary-crusher-01"})
    assert observations.status_code == 200
    assert observations.json()["items"][0]["idempotency_key"] == "reading-1"


def test_idempotency_marks_duplicate_and_creates_explainable_quality_finding(client) -> None:
    now = datetime.now(UTC) - timedelta(seconds=30)
    body = telemetry_batch(key="replayed-reading", recorded_at=now)
    assert ingest(client, body, "batch-original").status_code == 201

    duplicate = ingest(client, body, "batch-retry")
    assert duplicate.status_code == 201
    assert duplicate.json()["accepted_count"] == 0
    assert duplicate.json()["duplicate_count"] == 1
    assert duplicate.json()["observations"][0]["quality_flags"] == ["duplicate"]

    findings = client.get("/api/v1/findings")
    assert findings.status_code == 200
    finding = findings.json()["items"][0]
    assert finding["finding_type"] == "data_quality"
    assert finding["detector"]["name"] == "ingestion-quality"
    assert "idempotency key" in finding["rationale"]


def test_flags_out_of_order_invalid_unit_and_range_without_truth_data(client) -> None:
    now = datetime.now(UTC)
    assert (
        ingest(
            client, telemetry_batch(key="later", recorded_at=now - timedelta(seconds=30))
        ).status_code
        == 201
    )

    response = ingest(
        client,
        telemetry_batch(
            key="earlier-invalid",
            recorded_at=now - timedelta(seconds=90),
            value=1500,
            unit="kW",
        ),
        "batch-earlier",
    )
    assert response.status_code == 201
    assert set(response.json()["observations"][0]["quality_flags"]) == {
        "invalid_unit",
        "out_of_order",
    }

    findings = client.get("/api/v1/findings")
    item = findings.json()["items"][0]
    assert item["data_quality_summary"]["status"] == "unusable"
    assert item["evidence"][0]["role"] == "trigger"

    range_response = ingest(
        client,
        telemetry_batch(
            key="out-of-range",
            recorded_at=now,
            value=1500,
            unit="A",
        ),
        "batch-range",
    )
    assert range_response.status_code == 201
    assert range_response.json()["observations"][0]["quality_flags"] == ["out_of_range"]


def test_rejects_scenario_private_fields(client) -> None:
    now = datetime.now(UTC) - timedelta(seconds=30)
    body = telemetry_batch(key="private-field", recorded_at=now)
    body["observations"][0]["attributes"] = {"hidden_truth": "not permitted"}

    response = ingest(client, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_creates_explainable_public_telemetry_deviation_finding(client) -> None:
    now = datetime.now(UTC)
    for index, value in enumerate((100.0, 102.0, 98.0)):
        response = ingest(
            client,
            telemetry_batch(
                key=f"baseline-{index}",
                recorded_at=now - timedelta(seconds=90 - index),
                value=value,
            ),
            f"baseline-batch-{index}",
        )
        assert response.status_code == 201

    spike = ingest(
        client,
        telemetry_batch(key="spike", recorded_at=now, value=160.0),
        "spike-batch",
    )
    assert spike.status_code == 201

    findings = client.get("/api/v1/findings").json()["items"]
    anomaly = next(
        item for item in findings if item["detector"]["name"] == "public-telemetry-deviation"
    )
    assert anomaly["finding_type"] == "anomaly"
    assert "previous 3 observed readings" in anomaly["rationale"]
    assert anomaly["data_quality_summary"]["status"] == "good"
    assert anomaly["data_quality_summary"]["flags"] == []


def test_creates_degraded_anomaly_from_late_and_out_of_order_public_evidence(client) -> None:
    now = datetime.now(UTC)
    for index, value in enumerate((100.0, 102.0, 98.0)):
        response = ingest(
            client,
            telemetry_batch(
                key=f"late-baseline-{index}",
                recorded_at=now - timedelta(minutes=12 - index),
                value=value,
                asset_id="timing-evidence-crusher",
                source_id="timing-evidence-source",
            ),
            f"late-baseline-batch-{index}",
        )
        assert response.status_code == 201
        assert response.json()["observations"][0]["quality_flags"] == ["late_arrival"]

    spike = ingest(
        client,
        telemetry_batch(
            key="late-out-of-order-spike",
            recorded_at=now - timedelta(minutes=13),
            value=160.0,
            asset_id="timing-evidence-crusher",
            source_id="timing-evidence-source",
        ),
        "late-out-of-order-spike-batch",
    )
    assert spike.status_code == 201
    assert set(spike.json()["observations"][0]["quality_flags"]) == {
        "late_arrival",
        "out_of_order",
    }

    findings = client.get("/api/v1/findings").json()["items"]
    anomaly = next(
        item for item in findings if item["detector"]["name"] == "public-telemetry-deviation"
    )
    assert anomaly["data_quality_summary"] == {
        "status": "degraded",
        "flags": ["late_arrival", "out_of_order"],
    }
    assert "Timing/order quality caveat" in anomaly["rationale"]
    assert {item["role"] for item in anomaly["evidence"]} == {"trigger", "baseline"}


def test_excludes_invalid_and_duplicate_telemetry_from_anomaly_evidence(client) -> None:
    now = datetime.now(UTC)
    asset_id = "trusted-evidence-crusher"
    source_id = "trusted-evidence-source"
    # This first spike lacks a baseline. Its replay makes it duplicate, so it must stay
    # excluded when later readings establish a baseline.
    first_spike = telemetry_batch(
        key="duplicate-spike", recorded_at=now - timedelta(seconds=80), value=160.0,
        asset_id=asset_id, source_id=source_id,
    )
    assert ingest(client, first_spike, "duplicate-spike-original").status_code == 201
    assert ingest(client, first_spike, "duplicate-spike-replay").json()["duplicate_count"] == 1

    for index, value in enumerate((100.0, 102.0, 98.0)):
        assert ingest(
            client,
            telemetry_batch(
                key=f"trusted-baseline-{index}",
                recorded_at=now - timedelta(seconds=60 - index),
                value=value,
                asset_id=asset_id,
                source_id=source_id,
            ),
            f"trusted-baseline-batch-{index}",
        ).status_code == 201

    invalid = ingest(
        client,
        telemetry_batch(
            key="invalid-spike",
            recorded_at=now - timedelta(seconds=10),
            value=160.0,
            unit="kW",
            asset_id=asset_id,
            source_id=source_id,
        ),
        "invalid-spike-batch",
    )
    assert invalid.status_code == 201
    assert invalid.json()["observations"][0]["quality_flags"] == ["invalid_unit"]

    clean_spike = ingest(
        client,
        telemetry_batch(
            key="clean-spike",
            recorded_at=now,
            value=160.0,
            asset_id=asset_id,
            source_id=source_id,
        ),
        "clean-spike-batch",
    )
    assert clean_spike.status_code == 201
    findings = client.get("/api/v1/findings").json()["items"]
    anomalies = [
        item
        for item in findings
        if item["detector"]["name"] == "public-telemetry-deviation"
    ]
    assert len(anomalies) == 1
    assert anomalies[0]["data_quality_summary"]["status"] == "good"
    assert "invalid_unit" not in anomalies[0]["data_quality_summary"]["flags"]


def test_classifies_multi_source_staleness_from_observed_timestamps(client) -> None:
    now = datetime.now(UTC)
    for source_id in ("source-a", "source-b"):
        response = ingest(
            client,
            telemetry_batch(
                key=f"{source_id}-stale",
                recorded_at=now - timedelta(minutes=10),
                source_id=source_id,
            ),
            f"{source_id}-batch",
        )
        assert response.status_code == 201

    fresh = ingest(
        client,
        telemetry_batch(key="source-c-fresh", recorded_at=now, source_id="source-c"),
        "source-c-batch",
    )
    assert fresh.status_code == 201

    findings = client.get("/api/v1/findings").json()["items"]
    source_health = next(
        item for item in findings if item["detector"]["name"] == "multi-source-freshness"
    )
    assert source_health["finding_type"] == "data_quality"
    assert source_health["data_quality_summary"]["flags"] == ["stale_source"]
    assert "not a plant condition" in source_health["rationale"]
