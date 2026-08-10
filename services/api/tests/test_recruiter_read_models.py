from __future__ import annotations

# ruff: noqa: E501, E702
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Asset, Finding, Incident, IncidentFinding, Observation


def _production_observation(
    *,
    key: str,
    observed_at: datetime,
    throughput: float,
    source_recorded_at: datetime | None = None,
) -> dict:
    return {
        "idempotency_key": key,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "asset_ref": {"site_id": "sonoran-west", "asset_id": "stockpile-01"},
        "kind": "production_record",
        "record_type": "production_summary",
        "source_recorded_at": (source_recorded_at or observed_at)
        .isoformat()
        .replace("+00:00", "Z"),
        "attributes": {"throughput_tph": throughput},
    }


def _ingest_production_records(client) -> None:
    now = datetime.now(UTC)
    response = client.post(
        "/api/v1/ingestion/observations",
        headers={"Idempotency-Key": "production-replay"},
        json={
            "contract_version": "1.0",
            "source": {
                "source_id": "production-export",
                "source_type": "file",
                "received_via": "file_adapter",
            },
            "observations": [
                _production_observation(
                    key="production-100", observed_at=now - timedelta(minutes=4), throughput=100
                ),
                _production_observation(
                    key="production-120", observed_at=now - timedelta(minutes=3), throughput=120
                ),
                _production_observation(
                    key="production-50-late",
                    observed_at=now - timedelta(minutes=2),
                    source_recorded_at=now - timedelta(minutes=12),
                    throughput=50,
                ),
                _production_observation(
                    key="production-130", observed_at=now - timedelta(minutes=1), throughput=130
                ),
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["flagged_count"] == 1


def test_operations_briefing_is_traceable_to_stored_rows(client) -> None:
    _ingest_production_records(client)

    response = client.get("/api/v1/operations/briefing", params={"site_id": "sonoran-west"})

    assert response.status_code == 200
    briefing = response.json()
    assert briefing["site_id"] == "sonoran-west"
    assert briefing["observation_count"] == 4
    assert briefing["flagged_observation_count"] == 1
    assert briefing["replay_boundary"] == {
        "mode": "stored_observation_replay",
        "observation_time_field": "observed_at",
        "production_series_definition": "production_record.attributes.throughput_tph",
        "window_start_at": briefing["oldest_observed_at"],
        "window_end_at": briefing["latest_observed_at"],
        "calculation_note": (
            "Counts, production values, and the clean-record median are calculated from "
            "stored observation rows for this site."
        ),
    }
    assert [point["value"] for point in briefing["production"]["series"]] == [100, 120, 50, 130]
    assert briefing["production"]["current"]["value"] == 130
    assert briefing["production"]["baseline"] == {
        "method": "median_of_clean_production_records",
        "value": 120,
        "sample_count": 3,
    }
    assert briefing["production"]["delta_vs_baseline"] == 10
    assert briefing["data_quality_flag_counts"] == [
        {"flag": "late_arrival", "observation_count": 1}
    ]
    assert briefing["assets"] == [
        {
            "asset_id": "stockpile-01",
            "observation_count": 4,
            "flagged_observation_count": 1,
            "active_incident_count": 1,
            "latest_observed_at": briefing["latest_observed_at"],
        }
    ]


def test_operations_briefing_does_not_substitute_unstored_operating_claims(client) -> None:
    response = client.get("/api/v1/operations/briefing", params={"site_id": "empty-site"})

    assert response.status_code == 200
    assert response.json() == {
        "site_id": "empty-site",
        "replay_boundary": {
            "mode": "stored_observation_replay",
            "observation_time_field": "observed_at",
            "production_series_definition": "production_record.attributes.throughput_tph",
            "window_start_at": None,
            "window_end_at": None,
            "calculation_note": (
                "Counts, production values, and the clean-record median are calculated from "
                "stored observation rows for this site."
            ),
        },
        "observation_count": 0,
        "flagged_observation_count": 0,
        "oldest_observed_at": None,
        "latest_observed_at": None,
        "production": {
            "series": [],
            "current": None,
            "baseline": {
                "method": "median_of_clean_production_records",
                "value": None,
                "sample_count": 0,
            },
            "delta_vs_baseline": None,
        },
        "data_quality_flag_counts": [],
        "assets": [],
        "visual_analytics": {
            "metric_series": [],
            "observation_kind_counts": [],
            "quality_flag_counts_by_asset": [],
            "incident_counts": [],
            "process_nodes": [],
            "sensor_states": [],
        },
    }


def test_sensor_states_are_evidence_scoped_and_do_not_claim_safety(client) -> None:
    response = client.get("/api/v1/operations/briefing", params={"site_id": "empty-site"})
    states = response.json()["visual_analytics"]["sensor_states"]
    assert states == []
    rendered = str(response.json()).lower()
    assert "healthy" not in rendered and "safe" not in rendered


def test_sensor_states_include_no_data_for_persisted_asset(client) -> None:
    with Session(client.app.state.engine) as session:
        session.add(Asset(asset_id="empty-sensor", site_id="sensor-site"))
        session.commit()
    response = client.get("/api/v1/operations/briefing", params={"site_id": "sensor-site"})
    states = response.json()["visual_analytics"]["sensor_states"]
    assert states == [
        {
            "asset_id": "empty-sensor", "metric": "no_metric_observed", "unit": None,
            "latest_value": None, "latest_observed_at": None, "latest_quality_flags": [],
            "flagged_observation_count": 0, "observation_count": 0,
            "linked_active_incident_count": 0, "linked_active_incident_highest_severity": None,
            "linked_finding_count": 0, "state": "no_data",
            "reason": "No stored metric observation is available for this asset.",
        }
    ]


def test_sensor_state_precedence_and_evidence_scoping(client) -> None:
    at = datetime(2020, 1, 1, tzinfo=UTC)
    with Session(client.app.state.engine) as session:
        assets = [Asset(asset_id=name, site_id="sensor-site") for name in ("critical", "attention", "quality", "clear", "empty")]
        assets.append(Asset(asset_id="other", site_id="other-site"))
        session.add_all(assets)
        rows = []
        for name in ("critical", "attention", "quality", "clear"):
            rows.append(Observation(observation_id=f"obs-{name}", idempotency_key=f"key-{name}", source_id="test", source_type="telemetry", received_via="api", asset_id=name, kind="telemetry", metric="signal", value=1.0, unit="u", record_type=None, attributes={}, observed_at=at, source_recorded_at=at, ingested_at=at, quality_status="accepted", quality_flags=[]))
        rows.append(Observation(observation_id="obs-other", idempotency_key="key-other", source_id="test", source_type="telemetry", received_via="api", asset_id="other", kind="telemetry", metric="signal", value=1.0, unit="u", record_type=None, attributes={}, observed_at=at, source_recorded_at=at, ingested_at=at, quality_status="accepted", quality_flags=[]))
        session.add_all(rows)
        findings = [
            Finding(finding_id="f-critical", finding_type="anomaly", status="active", asset_id="critical", detector_name="d", detector_version="1", window_start_at=at, window_end_at=at, severity="critical", rationale="r", evidence=[{"observation_id": "obs-critical"}], data_quality_status="good", data_quality_flags=[]),
            Finding(finding_id="f-attention", finding_type="anomaly", status="active", asset_id="attention", detector_name="d", detector_version="1", window_start_at=at, window_end_at=at, severity="warning", rationale="r", evidence=[{"observation_id": "obs-attention"}], data_quality_status="good", data_quality_flags=[]),
            Finding(finding_id="f-quality", finding_type="data_quality", status="active", asset_id="quality", detector_name="d", detector_version="1", window_start_at=at, window_end_at=at, severity="warning", rationale="r", evidence=[{"observation_id": "obs-quality"}], data_quality_status="review", data_quality_flags=["late_arrival"]),
            Finding(finding_id="f-other", finding_type="anomaly", status="active", asset_id="other", detector_name="d", detector_version="1", window_start_at=at, window_end_at=at, severity="critical", rationale="r", evidence=[{"observation_id": "obs-critical"}], data_quality_status="good", data_quality_flags=[]),
        ]
        session.add_all(findings)
        incident = Incident(incident_id="i-critical", asset_id="critical", status="open", title="i", severity="critical", opened_at=at, updated_at=at)
        session.add(incident); session.flush()
        session.add(IncidentFinding(incident_id="i-critical", finding_id="f-critical", linked_at=at))
        session.commit()
    states = client.get("/api/v1/operations/briefing", params={"site_id": "sensor-site"}).json()["visual_analytics"]["sensor_states"]
    by_asset = {item["asset_id"]: item for item in states}
    assert by_asset["critical"]["state"] == "critical" and by_asset["critical"]["linked_active_incident_count"] == 1
    assert by_asset["attention"]["state"] == "attention"
    assert by_asset["quality"]["state"] == "data_quality"
    assert by_asset["clear"]["state"] == "no_issue"
    assert by_asset["empty"]["state"] == "no_data"
    assert "other" not in by_asset


def test_private_truth_fields_are_rejected_and_never_reappear_in_briefing(client) -> None:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    rejected = client.post(
        "/api/v1/ingestion/observations",
        headers={"Idempotency-Key": "private-truth-attempt"},
        json={
            "contract_version": "1.0",
            "source": {
                "source_id": "production-export",
                "source_type": "file",
                "received_via": "file_adapter",
            },
            "observations": [
                {
                    "idempotency_key": "private-row",
                    "observed_at": now,
                    "asset_ref": {"site_id": "sonoran-west", "asset_id": "stockpile-01"},
                    "kind": "production_record",
                    "record_type": "production_summary",
                    "source_recorded_at": now,
                    "attributes": {"throughput_tph": 100, "scenario_id": "not-public"},
                }
            ],
        },
    )

    assert rejected.status_code == 422
    briefing = client.get("/api/v1/operations/briefing", params={"site_id": "sonoran-west"})
    assert briefing.status_code == 200
    assert "scenario_id" not in briefing.text
    assert "not-public" not in briefing.text
