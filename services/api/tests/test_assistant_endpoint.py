from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Finding, Incident, Observation


def _ingest(
    client,
    *,
    key: str,
    site_id: str,
    asset_id: str,
    unit: str = "m/s",
) -> None:
    moment = datetime.now(UTC)
    body = {
        "contract_version": "1.0",
        "source": {
            "source_id": f"assistant-api-{site_id}",
            "source_type": "telemetry",
            "received_via": "api",
        },
        "observations": [
            {
                "idempotency_key": key,
                "observed_at": moment.isoformat().replace("+00:00", "Z"),
                "asset_ref": {"site_id": site_id, "asset_id": asset_id},
                "kind": "telemetry",
                "metric": "belt_speed_mps",
                "value": 3.0,
                "unit": unit,
                "source_recorded_at": moment.isoformat().replace("+00:00", "Z"),
                "attributes": {},
            }
        ],
    }
    response = client.post(
        "/api/v1/ingestion/observations", json=body, headers={"Idempotency-Key": key}
    )
    assert response.status_code == 201


def _counts(client) -> tuple[int, int, int]:
    with Session(client.app.state.engine) as session:
        return tuple(
            session.scalar(select(func.count(column)).select_from(model))
            for column, model in (
                (Observation.observation_id, Observation),
                (Finding.finding_id, Finding),
                (Incident.incident_id, Incident),
            )
        )


def test_assistant_endpoint_allowlist_contract_and_site_scoping(client) -> None:
    _ingest(
        client,
        key="west-invalid",
        site_id="sonoran-west",
        asset_id="west-belt",
        unit="A",
    )
    _ingest(
        client,
        key="east-invalid",
        site_id="other-site",
        asset_id="east-belt",
        unit="A",
    )
    base = {"site_id": "sonoran-west"}
    expected_fields = {
        "mode",
        "tool_name",
        "site_id",
        "records",
        "citations",
        "uncertainty_notes",
        "truncated",
    }

    incidents = client.post(
        "/api/v1/assistant/tools/list_recent_incidents", json={**base, "arguments": {}}
    )
    assert incidents.status_code == 200
    assert set(incidents.json()) == expected_fields
    assert incidents.json()["mode"] == "deterministic_evidence_tool"
    assert incidents.json()["site_id"] == "sonoran-west"
    assert {item["asset_id"] for item in incidents.json()["records"]} == {"west-belt"}
    incident_id = incidents.json()["records"][0]["incident_id"]

    calls = {
        "get_incident_evidence": {"incident_id": incident_id},
        "query_observations": {
            "asset_id": "west-belt",
            "metric": "belt_speed_mps",
            "start_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "end_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
        },
        "list_recent_findings": {},
        "compare_observation_periods": {
            "asset_id": "west-belt",
            "metric": "belt_speed_mps",
            "baseline_start_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "baseline_end_at": datetime.now(UTC).isoformat(),
            "comparison_start_at": datetime.now(UTC).isoformat(),
            "comparison_end_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
        },
    }
    for tool_name, arguments in calls.items():
        response = client.post(
            f"/api/v1/assistant/tools/{tool_name}", json={**base, "arguments": arguments}
        )
        assert response.status_code == 200
        assert set(response.json()) == expected_fields
        assert response.json()["tool_name"] == tool_name

    east_incidents = client.post(
        "/api/v1/assistant/tools/list_recent_incidents",
        json={"site_id": "other-site", "arguments": {}},
    )
    assert east_incidents.status_code == 200
    east_incident_id = east_incidents.json()["records"][0]["incident_id"]
    cross_site = client.post(
        "/api/v1/assistant/tools/get_incident_evidence",
        json={**base, "arguments": {"incident_id": east_incident_id}},
    )
    assert cross_site.status_code == 200
    assert cross_site.json()["records"] == []

    east_query = client.post(
        "/api/v1/assistant/tools/query_observations",
        json={
            **base,
            "arguments": {
                "asset_id": "east-belt",
                "start_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                "end_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            },
        },
    )
    assert east_query.status_code == 200
    assert east_query.json()["records"] == []
    assert "No platform-visible" in east_query.json()["uncertainty_notes"][-1]


def test_assistant_endpoint_rejects_unknown_or_unsafe_arguments_without_mutation(client) -> None:
    _ingest(
        client,
        key="endpoint-invalid",
        site_id="sonoran-west",
        asset_id="endpoint-belt",
        unit="A",
    )
    before = _counts(client)
    requests = (
        ("not_registered", {"site_id": "sonoran-west", "arguments": {}}),
        (
            "query_observations",
            {
                "site_id": "sonoran-west",
                "arguments": {"asset_id": "endpoint-belt; DROP TABLE observations"},
            },
        ),
        (
            "list_recent_incidents",
            {"site_id": "sonoran-west", "arguments": {"operation": "delete"}},
        ),
    )
    for tool_name, body in requests:
        response = client.post(f"/api/v1/assistant/tools/{tool_name}", json=body)
        assert response.status_code == 422
    assert _counts(client) == before


def test_assistant_endpoint_has_no_private_field_leakage_or_state_mutation(client) -> None:
    _ingest(
        client,
        key="private-safe-invalid",
        site_id="sonoran-west",
        asset_id="private-safe-belt",
        unit="A",
    )
    before = _counts(client)
    response = client.post(
        "/api/v1/assistant/tools/list_recent_findings",
        json={"site_id": "sonoran-west", "arguments": {}},
    )
    assert response.status_code == 200
    assert _counts(client) == before
    rendered = json.dumps(response.json()).lower()
    assert all(
        term not in rendered
        for term in (
            "hidden_truth",
            "scenario_id",
            "scenario_seed",
            "ground_truth",
            "expected_answer",
        )
    )
