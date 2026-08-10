"""Read models that make the public demo's evidence and limits explicit."""

from __future__ import annotations

from collections import Counter
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Incident, Observation
from app.platform import ACTIVE_INCIDENT_STATES
from app.schemas import (
    AnalyticsPointResponse,
    AssetBriefingResponse,
    AssetFlagCountResponse,
    CountResponse,
    DataQualityFlagCountResponse,
    IncidentCountResponse,
    MetricSeriesResponse,
    OperationsBriefingResponse,
    ProcessNodeResponse,
    ProductionBaselineResponse,
    ProductionPointResponse,
    ProductionSummaryResponse,
    ReplayBoundaryResponse,
    VisualAnalyticsResponse,
)

MAX_METRIC_SERIES = 24
MAX_POINTS_PER_SERIES = 60


def operations_briefing_response(session: Session, site_id: str) -> OperationsBriefingResponse:
    """Return only facts calculated from stored rows for one site.

    This deliberately does not infer operational availability, planned output, model
    confidence, or causal diagnoses. Those values are not persisted as observations.
    """

    assets = list(
        session.scalars(select(Asset).where(Asset.site_id == site_id).order_by(Asset.asset_id))
    )
    observations = list(
        session.scalars(
            select(Observation)
            .join(Observation.asset)
            .where(Asset.site_id == site_id)
            .order_by(Observation.observed_at, Observation.observation_id)
        )
    )
    active_incident_counts = Counter(
        session.scalars(
            select(Incident.asset_id)
            .join(Incident.asset)
            .where(Asset.site_id == site_id, Incident.status.in_(ACTIVE_INCIDENT_STATES))
        )
    )
    site_incidents = list(
        session.scalars(select(Incident).join(Incident.asset).where(Asset.site_id == site_id))
    )

    flagged = [item for item in observations if _is_flagged(item)]
    flag_counts = Counter(flag for item in observations for flag in item.quality_flags)
    production_observations = [
        item
        for item in observations
        if item.kind == "production_record" and _throughput_value(item) is not None
    ]
    production_points = [_production_point(item) for item in production_observations]
    clean_values = [
        point.value
        for observation, point in zip(production_observations, production_points, strict=True)
        if not _is_flagged(observation)
    ]
    baseline_value = float(median(clean_values)) if clean_values else None
    current = production_points[-1] if production_points else None
    delta = (
        current.value - baseline_value
        if current is not None and baseline_value is not None
        else None
    )

    observations_by_asset: dict[str, list[Observation]] = {asset.asset_id: [] for asset in assets}
    for observation in observations:
        observations_by_asset.setdefault(observation.asset_id, []).append(observation)

    return OperationsBriefingResponse(
        site_id=site_id,
        replay_boundary=ReplayBoundaryResponse(
            mode="stored_observation_replay",
            observation_time_field="observed_at",
            production_series_definition="production_record.attributes.throughput_tph",
            window_start_at=observations[0].observed_at if observations else None,
            window_end_at=observations[-1].observed_at if observations else None,
            calculation_note=(
                "Counts, production values, and the clean-record median are calculated from "
                "stored observation rows for this site."
            ),
        ),
        observation_count=len(observations),
        flagged_observation_count=len(flagged),
        oldest_observed_at=observations[0].observed_at if observations else None,
        latest_observed_at=observations[-1].observed_at if observations else None,
        production=ProductionSummaryResponse(
            series=production_points,
            current=current,
            baseline=ProductionBaselineResponse(
                method="median_of_clean_production_records",
                value=baseline_value,
                sample_count=len(clean_values),
            ),
            delta_vs_baseline=delta,
        ),
        data_quality_flag_counts=[
            DataQualityFlagCountResponse(flag=flag, observation_count=count)
            for flag, count in sorted(flag_counts.items())
        ],
        assets=[
            AssetBriefingResponse(
                asset_id=asset.asset_id,
                observation_count=len(asset_observations),
                flagged_observation_count=sum(
                    1 for item in asset_observations if _is_flagged(item)
                ),
                active_incident_count=active_incident_counts[asset.asset_id],
                latest_observed_at=(
                    max(
                        (item.observed_at for item in asset_observations),
                        default=None,
                    )
                ),
            )
            for asset in assets
            for asset_observations in [observations_by_asset.get(asset.asset_id, [])]
        ],
        visual_analytics=_visual_analytics(
            observations, assets, site_incidents, active_incident_counts
        ),
    )


def linked_observation_ids(incident: Incident) -> set[str]:
    """Return public observation references made by linked findings only."""

    return {
        evidence["observation_id"]
        for link in incident.finding_links
        for evidence in link.finding.evidence
        if isinstance(evidence, dict) and isinstance(evidence.get("observation_id"), str)
    }


def _is_flagged(observation: Observation) -> bool:
    return observation.quality_status != "accepted" or bool(observation.quality_flags)


def _throughput_value(observation: Observation) -> float | None:
    value = observation.attributes.get("throughput_tph")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _production_point(observation: Observation) -> ProductionPointResponse:
    value = _throughput_value(observation)
    assert value is not None
    return ProductionPointResponse(
        observation_id=observation.observation_id,
        observed_at=observation.observed_at,
        value=value,
        unit=observation.unit,
        quality_status=observation.quality_status,
        quality_flags=observation.quality_flags,
    )


def _visual_analytics(
    observations: list[Observation],
    assets: list[Asset],
    site_incidents: list[Incident],
    active_incident_counts: Counter[str],
) -> VisualAnalyticsResponse:
    """Bounded chart/table facts directly traceable to stored rows."""
    series_groups: dict[tuple[str, str, str | None], list[Observation]] = {}
    for item in observations:
        if item.metric is not None and item.value is not None:
            series_groups.setdefault((item.asset_id, item.metric, item.unit), []).append(item)
    metric_series = [
        MetricSeriesResponse(
            asset_id=asset_id,
            metric=metric,
            unit=unit,
            points=[
                AnalyticsPointResponse(
                    observed_at=item.observed_at, value=item.value, quality_flags=item.quality_flags
                )
                for item in _downsample(items, MAX_POINTS_PER_SERIES)
            ],
        )
        for (asset_id, metric, unit), items in sorted(series_groups.items())[:MAX_METRIC_SERIES]
    ]
    kind_counts = Counter(item.kind for item in observations)
    flags_by_asset = Counter(
        (item.asset_id, flag) for item in observations for flag in item.quality_flags
    )
    incidents = Counter((item.asset_id, item.severity, item.status) for item in site_incidents)
    # Active counts above deliberately remain scoped to persisted incident rows; grouped status
    # detail is supplied by the caller's existing incident query contract.
    nodes = [
        ProcessNodeResponse(
            asset_id=asset.asset_id,
            observation_count=sum(1 for item in observations if item.asset_id == asset.asset_id),
            latest_observed_at=max(
                (item.observed_at for item in observations if item.asset_id == asset.asset_id),
                default=None,
            ),
            active_incident_count=active_incident_counts[asset.asset_id],
            flagged_observation_count=sum(
                1 for item in observations if item.asset_id == asset.asset_id and _is_flagged(item)
            ),
        )
        for asset in assets
    ]
    return VisualAnalyticsResponse(
        metric_series=metric_series,
        observation_kind_counts=[
            CountResponse(key=key, count=value) for key, value in sorted(kind_counts.items())
        ],
        quality_flag_counts_by_asset=[
            AssetFlagCountResponse(asset_id=asset_id, flag=flag, observation_count=count)
            for (asset_id, flag), count in sorted(flags_by_asset.items())
        ],
        incident_counts=[
            IncidentCountResponse(asset_id=asset_id, severity=severity, status=status, count=count)
            for (asset_id, severity, status), count in sorted(incidents.items())
        ],
        process_nodes=nodes,
    )


def _downsample(items: list[Observation], limit: int) -> list[Observation]:
    if len(items) <= limit:
        return items
    step = (len(items) - 1) / (limit - 1)
    return [items[round(index * step)] for index in range(limit)]
