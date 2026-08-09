from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime, timedelta
from statistics import fmean
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, Finding, Incident, IncidentFinding, IncidentTimelineEntry, Observation
from app.schemas import (
    AssetRef,
    AssetResponse,
    FindingResponse,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentTransitionRequest,
    ObservationInput,
    ObservationResponse,
    TimelineEntryResponse,
)

METRIC_RULES: dict[str, tuple[str, float, float]] = {
    "motor_current_amps": ("A", 0.0, 1000.0),
    "throughput_tph": ("t/h", 0.0, 2000.0),
    "vibration_mm_s": ("mm/s", 0.0, 50.0),
    "bearing_temperature_c": ("C", -40.0, 200.0),
    "belt_speed_mps": ("m/s", 0.0, 20.0),
}
ACTIVE_INCIDENT_STATES = ("open", "acknowledged", "investigating", "mitigated")
TIMING_QUALITY_FLAGS = frozenset({"late_arrival", "out_of_order"})
TRANSITIONS = {
    "open": {"acknowledged", "dismissed"},
    "acknowledged": {"investigating", "mitigated", "dismissed"},
    "investigating": {"mitigated", "dismissed"},
    "mitigated": {"investigating", "resolved", "dismissed"},
    "resolved": set(),
    "dismissed": set(),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4()}"


def evaluate_quality(
    session: Session, observation: ObservationInput, source_id: str, now: datetime
) -> list[str]:
    flags: list[str] = []
    if now - observation.source_recorded_at > timedelta(seconds=300):
        flags.append("late_arrival")
    if observation.kind == "telemetry" and observation.metric in METRIC_RULES:
        expected_unit, low, high = METRIC_RULES[observation.metric]
        if observation.unit != expected_unit:
            flags.append("invalid_unit")
        elif observation.value is not None and not low <= observation.value <= high:
            flags.append("out_of_range")
    if observation.metric:
        prior = session.scalar(
            select(Observation)
            .where(
                Observation.source_id == source_id,
                Observation.asset_id == observation.asset_ref.asset_id,
                Observation.metric == observation.metric,
            )
            .order_by(Observation.source_recorded_at.desc())
            .limit(1)
        )
        if prior is not None and observation.source_recorded_at < as_utc(prior.source_recorded_at):
            flags.append("out_of_order")
    return flags


def ensure_asset(session: Session, asset_ref: AssetRef) -> Asset:
    asset = session.get(Asset, asset_ref.asset_id)
    if asset is None:
        asset = Asset(asset_id=asset_ref.asset_id, site_id=asset_ref.site_id)
        session.add(asset)
    elif asset.site_id != asset_ref.site_id:
        raise HTTPException(
            status_code=409, detail="asset_id is already associated with another site"
        )
    return asset


def _quality_rationale(flags: list[str]) -> str:
    readable = {
        "duplicate": "A matching idempotency key was received more than once.",
        "late_arrival": (
            "The source-recorded timestamp arrived more than five minutes after it occurred."
        ),
        "out_of_order": (
            "The source-recorded timestamp is earlier than a previously received reading "
            "for this metric."
        ),
        "invalid_unit": "The unit does not match the documented unit for this metric.",
        "out_of_range": (
            "The observed value is outside the documented plausible range for this metric."
        ),
    }
    return " ".join(readable[flag] for flag in flags)


def _quality_severity(flags: list[str]) -> str:
    if {"invalid_unit", "out_of_range"}.intersection(flags):
        return "warning"
    return "info"


def create_quality_finding(
    session: Session, observation: Observation, flags: list[str], now: datetime
) -> Finding:
    finding = Finding(
        finding_id=new_id("fnd"),
        finding_type="data_quality",
        status="active",
        asset_id=observation.asset_id,
        detector_name="ingestion-quality",
        detector_version="1.0.0",
        window_start_at=observation.source_recorded_at,
        window_end_at=observation.source_recorded_at,
        severity=_quality_severity(flags),
        rationale=_quality_rationale(flags),
        evidence=[{"observation_id": observation.observation_id, "role": "trigger"}],
        data_quality_status="unusable" if "invalid_unit" in flags else "degraded",
        data_quality_flags=flags,
    )
    session.add(finding)
    link_finding_to_incident(session, finding, now)
    return finding


def detect_telemetry_anomaly(
    session: Session, observation: Observation, now: datetime
) -> Finding | None:
    """Evaluate a small, transparent deviation rule over public telemetry only."""
    if observation.kind != "telemetry" or observation.metric is None or observation.value is None:
        return None
    if not _eligible_for_telemetry_deviation(observation):
        return None

    prior_observations = list(
        session.scalars(
            select(Observation)
            .where(
                Observation.asset_id == observation.asset_id,
                Observation.metric == observation.metric,
                Observation.observation_id != observation.observation_id,
            )
            .order_by(Observation.source_recorded_at.desc())
        )
    )
    eligible_prior = [
        item
        for item in prior_observations
        if item.value is not None and _eligible_for_telemetry_deviation(item)
    ][:5]
    prior_values = [item.value for item in eligible_prior if item.value is not None]
    if len(prior_values) < 3:
        return None

    baseline = fmean(value for value in prior_values if value is not None)
    if baseline == 0:
        return None
    relative_deviation = abs(observation.value - baseline) / abs(baseline)
    if relative_deviation < 0.25:
        return None

    direction = "above" if observation.value > baseline else "below"
    severity = "critical" if relative_deviation >= 0.5 else "warning"
    evidence_flags = sorted(
        {flag for item in [observation, *eligible_prior] for flag in item.quality_flags}
    )
    degraded = bool(evidence_flags)
    quality_caveat = (
        " Timing/order quality caveat: this finding uses late-arriving or out-of-order "
        "public evidence and should be interpreted as degraded."
        if degraded
        else ""
    )
    finding = Finding(
        finding_id=new_id("fnd"),
        finding_type="anomaly",
        status="active",
        asset_id=observation.asset_id,
        detector_name="public-telemetry-deviation",
        detector_version="1.0.0",
        window_start_at=min(as_utc(observation.source_recorded_at), now),
        window_end_at=max(as_utc(observation.source_recorded_at), now),
        severity=severity,
        rationale=(
            f"{observation.metric} measured {observation.value:g}, {relative_deviation:.0%} "
            f"{direction} the mean of the previous {len(prior_values)} observed readings "
            f"({baseline:g}).{quality_caveat}"
        ),
        evidence=[
            {"observation_id": observation.observation_id, "role": "trigger"},
            *[
                {"observation_id": item.observation_id, "role": "baseline"}
                for item in eligible_prior
            ],
        ],
        data_quality_status="degraded" if degraded else "good",
        data_quality_flags=evidence_flags,
    )
    session.add(finding)
    link_finding_to_incident(session, finding, now)
    return finding


def _eligible_for_telemetry_deviation(observation: Observation) -> bool:
    """Allow only clean or timing/order-degraded public telemetry as detector evidence."""
    return set(observation.quality_flags).issubset(TIMING_QUALITY_FLAGS)


def detect_multi_source_freshness(
    session: Session, trigger: Observation, now: datetime
) -> Finding | None:
    """Classify a multi-source freshness outage from observed timestamps, never scenario state."""
    source_freshness = session.execute(
        select(Observation.source_id, func.max(Observation.source_recorded_at)).group_by(
            Observation.source_id
        )
    ).all()
    stale_sources = [
        source_id
        for source_id, recorded_at in source_freshness
        if now - as_utc(recorded_at) > timedelta(minutes=5)
    ]
    fresh_sources = [
        source_id
        for source_id, recorded_at in source_freshness
        if now - as_utc(recorded_at) <= timedelta(minutes=5)
    ]
    if len(stale_sources) < 2 or not fresh_sources:
        return None

    existing = session.scalar(
        select(Finding).where(
            Finding.asset_id == trigger.asset_id,
            Finding.detector_name == "multi-source-freshness",
            Finding.status == "active",
        )
    )
    if existing is not None:
        return None
    finding = Finding(
        finding_id=new_id("fnd"),
        finding_type="data_quality",
        status="active",
        asset_id=trigger.asset_id,
        detector_name="multi-source-freshness",
        detector_version="1.0.0",
        window_start_at=now - timedelta(minutes=5),
        window_end_at=now,
        severity="warning",
        rationale=(
            f"{len(stale_sources)} observed sources are stale for more than five minutes "
            f"while {len(fresh_sources)} source remains current. This classifies a data "
            "freshness/connectivity issue, not a plant condition."
        ),
        evidence=[
            {"source_id": source_id, "role": "stale_source"} for source_id in sorted(stale_sources)
        ],
        data_quality_status="degraded",
        data_quality_flags=["stale_source"],
    )
    session.add(finding)
    link_finding_to_incident(session, finding, now)
    return finding


def link_finding_to_incident(session: Session, finding: Finding, now: datetime) -> Incident:
    title_prefix = (
        "Data quality issue" if finding.finding_type == "data_quality" else "Operational anomaly"
    )
    title = f"{title_prefix} on {finding.asset_id}"
    incident = session.scalar(
        select(Incident)
        .where(
            Incident.asset_id == finding.asset_id,
            Incident.title == title,
            Incident.status.in_(ACTIVE_INCIDENT_STATES),
        )
        .order_by(Incident.opened_at.desc())
        .limit(1)
    )
    if incident is None:
        incident = Incident(
            incident_id=new_id("inc"),
            asset_id=finding.asset_id,
            status="open",
            title=title,
            severity=finding.severity,
            opened_at=now,
            updated_at=now,
        )
        session.add(incident)
        session.add(
            IncidentTimelineEntry(
                timeline_entry_id=new_id("evt"),
                incident=incident,
                occurred_at=now,
                actor="system:ingestion",
                prior_status=None,
                new_status="open",
                reason="Created from an explainable platform finding.",
                evidence=[{"finding_id": finding.finding_id, "role": "trigger"}],
            )
        )
    elif _severity_rank(finding.severity) > _severity_rank(incident.severity):
        incident.severity = finding.severity
        incident.updated_at = now
    session.add(IncidentFinding(incident=incident, finding=finding, linked_at=now))
    return incident


def _severity_rank(severity: str) -> int:
    return {"info": 0, "warning": 1, "critical": 2}.get(severity, 0)


def observation_response(observation: Observation) -> ObservationResponse:
    return ObservationResponse(
        observation_id=observation.observation_id,
        idempotency_key=observation.idempotency_key,
        observed_at=observation.observed_at,
        ingested_at=observation.ingested_at,
        source_recorded_at=observation.source_recorded_at,
        asset_ref=AssetRef(site_id=observation.asset.site_id, asset_id=observation.asset_id),
        kind=observation.kind,
        metric=observation.metric,
        value=observation.value,
        unit=observation.unit,
        record_type=observation.record_type,
        attributes=observation.attributes,
        quality_status=observation.quality_status,
        quality_flags=observation.quality_flags,
    )


def finding_response(finding: Finding) -> FindingResponse:
    return FindingResponse(
        finding_id=finding.finding_id,
        finding_type=finding.finding_type,
        status=finding.status,
        asset_ref=AssetRef(site_id=finding.asset.site_id, asset_id=finding.asset_id),
        detector={"name": finding.detector_name, "version": finding.detector_version},
        evaluated_window={"start_at": finding.window_start_at, "end_at": finding.window_end_at},
        severity=finding.severity,
        rationale=finding.rationale,
        evidence=finding.evidence,
        data_quality_summary={
            "status": finding.data_quality_status,
            "flags": finding.data_quality_flags,
        },
        created_at=finding.created_at,
    )


def incident_response(incident: Incident) -> IncidentResponse:
    return IncidentResponse(
        incident_id=incident.incident_id,
        status=incident.status,
        title=incident.title,
        severity=incident.severity,
        asset_refs=[AssetRef(site_id=incident.asset.site_id, asset_id=incident.asset_id)],
        finding_ids=[link.finding_id for link in incident.finding_links],
        opened_at=incident.opened_at,
        updated_at=incident.updated_at,
    )


def incident_detail_response(incident: Incident) -> IncidentDetailResponse:
    response = incident_response(incident)
    return IncidentDetailResponse(
        **response.model_dump(),
        timeline=[
            TimelineEntryResponse(
                timeline_entry_id=entry.timeline_entry_id,
                occurred_at=entry.occurred_at,
                actor=entry.actor,
                prior_status=entry.prior_status,
                new_status=entry.new_status,
                reason=entry.reason,
                evidence=entry.evidence,
            )
            for entry in sorted(incident.timeline_entries, key=lambda item: item.occurred_at)
        ],
    )


def asset_response(asset: Asset) -> AssetResponse:
    return AssetResponse(site_id=asset.site_id, asset_id=asset.asset_id)


def encode_cursor(values: dict[str, str]) -> str:
    raw = json.dumps(values, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        parsed = json.loads(base64.urlsafe_b64decode(padded))
        if not isinstance(parsed, dict) or not all(
            isinstance(value, str) for value in parsed.values()
        ):
            raise ValueError
        return parsed
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        raise HTTPException(status_code=422, detail="invalid cursor") from None


def transition_incident(
    session: Session,
    incident: Incident,
    transition: IncidentTransitionRequest,
    idempotency_key: str,
    now: datetime,
) -> Incident:
    prior_entry = session.scalar(
        select(IncidentTimelineEntry).where(
            IncidentTimelineEntry.incident_id == incident.incident_id,
            IncidentTimelineEntry.idempotency_key == idempotency_key,
        )
    )
    if prior_entry is not None:
        return incident
    if transition.to_status not in TRANSITIONS[incident.status]:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition incident from {incident.status} to {transition.to_status}",
        )
    if transition.to_status in {"dismissed", "mitigated", "resolved"} and not transition.reason:
        raise HTTPException(status_code=422, detail="reason is required for this transition")
    prior_status = incident.status
    incident.status = transition.to_status
    incident.updated_at = now
    session.add(
        IncidentTimelineEntry(
            timeline_entry_id=new_id("evt"),
            incident=incident,
            occurred_at=now,
            actor=transition.actor,
            idempotency_key=idempotency_key,
            prior_status=prior_status,
            new_status=transition.to_status,
            reason=transition.reason,
            evidence=[],
        )
    )
    return incident
