from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from app.platform import new_id

ID_PATTERN = re.compile(r"^(?:obs|fnd|inc|evt)_[0-9a-f]{32}$")


def _observation(key: str, observed_at: datetime, value: float) -> dict:
    timestamp = observed_at.isoformat().replace("+00:00", "Z")
    return {
        "idempotency_key": key,
        "observed_at": timestamp,
        "asset_ref": {"site_id": "sonoran-west", "asset_id": "primary-crusher-01"},
        "kind": "telemetry",
        "metric": "motor_current_amps",
        "value": value,
        "unit": "A",
        "source_recorded_at": timestamp,
        "attributes": {},
    }


def test_platform_id_factory_fits_string_36() -> None:
    for prefix in ("fnd", "inc", "evt"):
        generated = new_id(prefix)
        assert len(generated) == 36
        assert ID_PATTERN.fullmatch(generated)


def test_ingestion_and_detector_ids_fit_postgres_columns(client) -> None:
    now = datetime.now(UTC)
    values = (100.0, 101.0, 99.0, 180.0)
    body = {
        "contract_version": "1.0",
        "source": {
            "source_id": "id-length-detector-source",
            "source_type": "telemetry",
            "received_via": "api",
        },
        "observations": [
            _observation(f"id-length-{index}", now + timedelta(seconds=index), value)
            for index, value in enumerate(values)
        ],
    }

    response = client.post(
        "/api/v1/ingestion/observations",
        json=body,
        headers={"Idempotency-Key": "id-length-batch"},
    )
    assert response.status_code == 201, response.text
    observation_ids = [item["observation_id"] for item in response.json()["observations"]]
    assert all(len(value) == 36 and ID_PATTERN.fullmatch(value) for value in observation_ids)

    findings = client.get("/api/v1/findings").json()["items"]
    assert any(item["detector"]["name"] == "public-telemetry-deviation" for item in findings)
    assert all(len(item["finding_id"]) == 36 for item in findings)
    assert all(ID_PATTERN.fullmatch(item["finding_id"]) for item in findings)

    incidents = client.get("/api/v1/incidents").json()["items"]
    assert incidents
    assert all(len(item["incident_id"]) == 36 for item in incidents)
    assert all(ID_PATTERN.fullmatch(item["incident_id"]) for item in incidents)

    detail = client.get(f"/api/v1/incidents/{incidents[0]['incident_id']}").json()
    timeline_ids = [item["timeline_entry_id"] for item in detail["timeline"]]
    assert timeline_ids
    assert all(len(value) == 36 and ID_PATTERN.fullmatch(value) for value in timeline_ids)
