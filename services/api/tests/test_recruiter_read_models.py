from __future__ import annotations

from datetime import UTC, datetime, timedelta


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
        },
    }


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
