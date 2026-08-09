from __future__ import annotations

from datetime import UTC, datetime, timedelta


def create_quality_incident(client) -> str:
    timestamp = (datetime.now(UTC) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    body = {
        "contract_version": "1.0",
        "source": {
            "source_id": "telemetry-belt-01",
            "source_type": "telemetry",
            "received_via": "api",
        },
        "observations": [
            {
                "idempotency_key": "late-reading",
                "observed_at": timestamp,
                "asset_ref": {"site_id": "sonoran-west", "asset_id": "belt-01"},
                "kind": "telemetry",
                "metric": "belt_speed_mps",
                "value": 3.0,
                "unit": "m/s",
                "source_recorded_at": timestamp,
                "attributes": {},
            }
        ],
    }
    response = client.post(
        "/api/v1/ingestion/observations", json=body, headers={"Idempotency-Key": "ingest-late"}
    )
    assert response.status_code == 201
    incidents = client.get("/api/v1/incidents")
    assert incidents.status_code == 200
    return incidents.json()["items"][0]["incident_id"]


def test_incident_aggregates_findings_and_keeps_audited_transition_timeline(client) -> None:
    incident_id = create_quality_incident(client)
    before = client.get(f"/api/v1/incidents/{incident_id}")
    assert before.status_code == 200
    assert before.json()["status"] == "open"
    assert len(before.json()["finding_ids"]) == 1
    assert len(before.json()["linked_findings"]) == 1
    linked_finding = before.json()["linked_findings"][0]
    assert linked_finding["detector"] == {"name": "ingestion-quality", "version": "1.0.0"}
    assert linked_finding["evaluated_window"]["start_at"]
    assert linked_finding["evaluated_window"]["end_at"]
    assert linked_finding["rationale"]
    assert linked_finding["data_quality_summary"]["status"] == "degraded"
    assert linked_finding["data_quality_summary"]["flags"] == ["late_arrival"]
    assert len(before.json()["linked_observations"]) == 1
    linked_observation = before.json()["linked_observations"][0]
    trigger_observation_id = linked_finding["evidence"][0]["observation_id"]
    assert linked_observation["observation_id"] == trigger_observation_id
    assert before.json()["timeline"][0]["actor"] == "system:ingestion"

    transition = {"to_status": "acknowledged", "actor": "operator:matt"}
    headers = {"Idempotency-Key": "transition-ack-1"}
    changed = client.post(
        f"/api/v1/incidents/{incident_id}/transitions", json=transition, headers=headers
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "acknowledged"
    assert len(changed.json()["timeline"]) == 2

    replay = client.post(
        f"/api/v1/incidents/{incident_id}/transitions", json=transition, headers=headers
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "acknowledged"
    assert len(replay.json()["timeline"]) == 2


def test_incident_enforces_lifecycle_and_reason_requirements(client) -> None:
    incident_id = create_quality_incident(client)
    no_reason = client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"to_status": "mitigated", "actor": "operator:matt"},
        headers={"Idempotency-Key": "transition-no-reason"},
    )
    assert no_reason.status_code == 409  # open must be acknowledged before mitigation

    acknowledged = client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"to_status": "acknowledged", "actor": "operator:matt"},
        headers={"Idempotency-Key": "transition-ack"},
    )
    assert acknowledged.status_code == 200

    no_reason = client.post(
        f"/api/v1/incidents/{incident_id}/transitions",
        json={"to_status": "mitigated", "actor": "operator:matt"},
        headers={"Idempotency-Key": "transition-mitigated"},
    )
    assert no_reason.status_code == 422
    assert no_reason.json()["error"]["code"] == "request_error"
