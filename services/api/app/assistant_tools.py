# ruff: noqa: E501, E701, E702
"""Provider-neutral, read-only retrieval tools for a future grounded assistant.

These tools deliberately return platform-visible records plus citations and uncertainty.
They do not execute raw SQL, write state, access simulator/evaluation data, or decide actions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Asset, Finding, Incident, IncidentFinding, Observation

MAX_RESULTS = 50
MAX_OBSERVATION_WINDOW = timedelta(days=7)
MAX_RECENT_LOOKBACK = timedelta(days=31)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UNSAFE_TEXT = re.compile(
    r"(?:;|--|/\*|\*/|\b(?:select|insert|update|delete|drop|alter|attach)\b|"
    r"ignore\s+(?:all|previous)|system\s+prompt|hidden[_ ]truth|scenario[_ ](?:seed|schedule))",
    re.IGNORECASE,
)


class ToolInputError(ValueError):
    """Raised when a tool request is outside its narrow, read-only contract."""


@dataclass(frozen=True)
class Citation:
    object_id: str
    object_type: str
    timestamp: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    asset_id: str | None = None
    metric: str | None = None
    source_id: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ToolResult:
    records: list[dict[str, Any]]
    citations: list[Citation]
    uncertainty_notes: list[str]
    truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "citations": [asdict(item) for item in self.citations]}


def list_recent_incidents(
    session: Session, *, limit: int = 20, site_id: str | None = None
) -> ToolResult:
    limit = _bounded_limit(limit)
    _optional_identifier(site_id, "site_id")
    cutoff = datetime.now(UTC) - MAX_RECENT_LOOKBACK
    statement = (
        select(Incident)
        .options(selectinload(Incident.asset), selectinload(Incident.finding_links))
        .where(Incident.updated_at >= cutoff)
        .order_by(Incident.updated_at.desc(), Incident.incident_id)
    )
    if site_id:
        statement = statement.join(Incident.asset).where(Asset.site_id == site_id)
    statement = statement.limit(limit + 1)
    incidents = list(session.scalars(statement))
    truncated = len(incidents) > limit
    incidents = incidents[:limit]
    return ToolResult(
        records=[
            {
                "incident_id": item.incident_id,
                "status": item.status,
                "title": item.title,
                "severity": item.severity,
                "asset_id": item.asset_id,
                "finding_ids": [link.finding_id for link in item.finding_links],
                "opened_at": _iso(item.opened_at),
                "updated_at": _iso(item.updated_at),
            }
            for item in incidents
        ],
        citations=[_incident_citation(item) for item in incidents],
        uncertainty_notes=_limit_note(truncated),
        truncated=truncated,
    )


def get_incident_evidence(
    session: Session, *, incident_id: str, site_id: str | None = None
) -> ToolResult:
    _identifier(incident_id, "incident_id")
    _optional_identifier(site_id, "site_id")
    statement = (
        select(Incident)
        .options(
            selectinload(Incident.asset),
            selectinload(Incident.finding_links)
            .selectinload(IncidentFinding.finding)
            .selectinload(Finding.asset),
            selectinload(Incident.timeline_entries),
        )
        .where(Incident.incident_id == incident_id)
    )
    if site_id:
        statement = statement.join(Incident.asset).where(Asset.site_id == site_id)
    incident = session.scalar(statement)
    if incident is None:
        return ToolResult(
            [], [], [f"No platform-visible incident exists for {incident_id}."], False
        )
    citations = [_incident_citation(incident)]
    notes: list[str] = []
    findings: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    for link in incident.finding_links:
        finding = link.finding
        if site_id and finding.asset.site_id != site_id:
            continue
        findings.append(
            {
                "finding_id": finding.finding_id,
                "finding_type": finding.finding_type,
                "severity": finding.severity,
                "rationale": finding.rationale,
                "data_quality_flags": finding.data_quality_flags,
            }
        )
        citations.append(
            Citation(
                finding.finding_id,
                "finding",
                start_at=_iso(finding.window_start_at),
                end_at=_iso(finding.window_end_at),
                asset_id=finding.asset_id,
                note="Finding window and platform rationale.",
            )
        )
        evidence_ids.update(
            item.get("observation_id", "")
            for item in finding.evidence
            if item.get("observation_id")
        )
    observations = (
        {
            item.observation_id: item
            for item in session.scalars(
                select(Observation)
                .join(Observation.asset)
                .where(
                    Observation.observation_id.in_(evidence_ids),
                    *([Asset.site_id == site_id] if site_id else []),
                )
            )
        }
        if evidence_ids
        else {}
    )
    for observation_id in sorted(evidence_ids):
        observation = observations.get(observation_id)
        if observation is None:
            citations.append(
                Citation(
                    observation_id, "observation", note="Referenced by finding but unavailable."
                )
            )
            notes.append(
                f"Evidence observation {observation_id} is not available in the read model."
            )
        else:
            citations.append(_observation_citation(observation))
    timeline = []
    for entry in sorted(incident.timeline_entries, key=lambda item: item.occurred_at):
        timeline.append(
            {
                "timeline_entry_id": entry.timeline_entry_id,
                "occurred_at": _iso(entry.occurred_at),
                "actor": entry.actor,
                "prior_status": entry.prior_status,
                "new_status": entry.new_status,
                "reason": entry.reason,
            }
        )
        citations.append(
            Citation(
                entry.timeline_entry_id,
                "incident_timeline_entry",
                timestamp=_iso(entry.occurred_at),
                asset_id=incident.asset_id,
                note="Append-only lifecycle event.",
            )
        )
    return ToolResult(
        [
            {
                "incident_id": incident.incident_id,
                "asset_id": incident.asset_id,
                "status": incident.status,
                "title": incident.title,
                "findings": findings,
                "timeline": timeline,
            }
        ],
        citations,
        notes or ["Evidence is limited to platform-visible findings and linked observations."],
    )


def query_observations(
    session: Session,
    *,
    asset_id: str,
    metric: str | None = None,
    start_at: str | datetime | None = None,
    end_at: str | datetime | None = None,
    limit: int = 50,
    site_id: str | None = None,
) -> ToolResult:
    _identifier(asset_id, "asset_id")
    _optional_identifier(site_id, "site_id")
    if metric is not None:
        _identifier(metric, "metric")
    limit = _bounded_limit(limit)
    end = _time(end_at, "end_at") if end_at else datetime.now(UTC)
    start = _time(start_at, "start_at") if start_at else end - timedelta(hours=24)
    _window(start, end)
    statement = (
        select(Observation)
        .join(Observation.asset)
        .where(
            Observation.asset_id == asset_id,
            Observation.observed_at >= start,
            Observation.observed_at < end,
        )
        .order_by(Observation.observed_at, Observation.observation_id)
    )
    if site_id:
        statement = statement.where(Asset.site_id == site_id)
    if metric:
        statement = statement.where(Observation.metric == metric)
    rows = list(session.scalars(statement.limit(limit + 1)))
    truncated = len(rows) > limit
    rows = rows[:limit]
    notes = _quality_notes(rows) + _limit_note(truncated)
    if not rows:
        notes.append("No platform-visible observations matched this bounded query.")
    return ToolResult(
        [_observation_record(item) for item in rows],
        [_observation_citation(item) for item in rows],
        notes,
        truncated,
    )


def list_recent_findings(
    session: Session, *, limit: int = 20, asset_id: str | None = None, site_id: str | None = None
) -> ToolResult:
    limit = _bounded_limit(limit)
    if asset_id is not None:
        _identifier(asset_id, "asset_id")
    _optional_identifier(site_id, "site_id")
    cutoff = datetime.now(UTC) - MAX_RECENT_LOOKBACK
    statement = select(Finding).order_by(Finding.created_at.desc(), Finding.finding_id)
    statement = statement.where(Finding.created_at >= cutoff)
    if site_id:
        statement = statement.join(Finding.asset).where(Asset.site_id == site_id)
    if asset_id:
        statement = statement.where(Finding.asset_id == asset_id)
    rows = list(session.scalars(statement.limit(limit + 1)))
    truncated = len(rows) > limit
    rows = rows[:limit]
    records = [
        {
            "finding_id": item.finding_id,
            "finding_type": item.finding_type,
            "severity": item.severity,
            "asset_id": item.asset_id,
            "rationale": item.rationale,
            "data_quality_status": item.data_quality_status,
            "data_quality_flags": item.data_quality_flags,
            "start_at": _iso(item.window_start_at),
            "end_at": _iso(item.window_end_at),
        }
        for item in rows
    ]
    citations = [
        Citation(
            item.finding_id,
            "finding",
            start_at=_iso(item.window_start_at),
            end_at=_iso(item.window_end_at),
            asset_id=item.asset_id,
            note="Platform detector output.",
        )
        for item in rows
    ]
    notes = _limit_note(truncated)
    if any(item.data_quality_flags for item in rows):
        notes.append(
            "Some listed findings describe data quality rather than an equipment condition."
        )
    return ToolResult(records, citations, notes, truncated)


def compare_observation_periods(
    session: Session,
    *,
    asset_id: str,
    metric: str,
    baseline_start_at: str | datetime,
    baseline_end_at: str | datetime,
    comparison_start_at: str | datetime,
    comparison_end_at: str | datetime,
    site_id: str | None = None,
) -> ToolResult:
    _identifier(asset_id, "asset_id")
    _identifier(metric, "metric")
    _optional_identifier(site_id, "site_id")
    baseline = (
        _time(baseline_start_at, "baseline_start_at"),
        _time(baseline_end_at, "baseline_end_at"),
    )
    comparison = (
        _time(comparison_start_at, "comparison_start_at"),
        _time(comparison_end_at, "comparison_end_at"),
    )
    _window(*baseline)
    _window(*comparison)
    left = _period(session, asset_id, metric, *baseline, site_id=site_id)
    right = _period(session, asset_id, metric, *comparison, site_id=site_id)
    values_left = [item.value for item in left if item.value is not None]
    values_right = [item.value for item in right if item.value is not None]
    result = {
        "asset_id": asset_id,
        "metric": metric,
        "baseline": _period_summary(values_left, baseline),
        "comparison": _period_summary(values_right, comparison),
    }
    if values_left and values_right:
        result["mean_change"] = round(fmean(values_right) - fmean(values_left), 6)
    notes = _quality_notes(left + right)
    if not values_left or not values_right:
        notes.append(
            "At least one period has no numeric platform-visible observations; no comparison is inferred."
        )
    citations = [_observation_citation(item) for item in left + right]
    return ToolResult(
        [result], citations, notes, len(left) == MAX_RESULTS or len(right) == MAX_RESULTS
    )


TOOL_REGISTRY: dict[str, Callable[..., ToolResult]] = {
    "list_recent_incidents": list_recent_incidents,
    "get_incident_evidence": get_incident_evidence,
    "query_observations": query_observations,
    "list_recent_findings": list_recent_findings,
    "compare_observation_periods": compare_observation_periods,
}


def invoke_tool(session: Session, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
    """Single constrained dispatch point for a future provider adapter."""
    _identifier(tool_name, "tool_name")
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        raise ToolInputError("tool is not registered for read-only assistant use")
    if not isinstance(arguments, dict):
        raise ToolInputError("tool arguments must be an object")
    _reject_unsafe(arguments)
    try:
        return tool(session, **arguments)
    except TypeError as error:
        raise ToolInputError("tool arguments do not match the allowed tool contract") from error


def _period(
    session: Session,
    asset_id: str,
    metric: str,
    start: datetime,
    end: datetime,
    *,
    site_id: str | None = None,
) -> list[Observation]:
    statement = select(Observation).join(Observation.asset).where(
        Observation.asset_id == asset_id,
        Observation.metric == metric,
        Observation.observed_at >= start,
        Observation.observed_at < end,
    )
    if site_id:
        statement = statement.where(Asset.site_id == site_id)
    return list(
        session.scalars(
            statement.order_by(Observation.observed_at, Observation.observation_id).limit(MAX_RESULTS)
        )
    )


def _period_summary(values: list[float], bounds: tuple[datetime, datetime]) -> dict[str, Any]:
    return {
        "start_at": _iso(bounds[0]),
        "end_at": _iso(bounds[1]),
        "count": len(values),
        "mean": round(fmean(values), 6) if values else None,
    }


def _observation_record(item: Observation) -> dict[str, Any]:
    return {
        "observation_id": item.observation_id,
        "observed_at": _iso(item.observed_at),
        "asset_id": item.asset_id,
        "metric": item.metric,
        "value": item.value,
        "unit": item.unit,
        "source_id": item.source_id,
        "quality_status": item.quality_status,
        "quality_flags": item.quality_flags,
    }


def _observation_citation(item: Observation) -> Citation:
    return Citation(
        item.observation_id,
        "observation",
        timestamp=_iso(item.observed_at),
        asset_id=item.asset_id,
        metric=item.metric,
        source_id=item.source_id,
        note="Platform-visible observation.",
    )


def _incident_citation(item: Incident) -> Citation:
    return Citation(
        item.incident_id,
        "incident",
        start_at=_iso(item.opened_at),
        end_at=_iso(item.updated_at),
        asset_id=item.asset_id,
        note="Platform incident record.",
    )


def _quality_notes(rows: list[Observation]) -> list[str]:
    flags = sorted({flag for item in rows for flag in item.quality_flags})
    return [f"Data-quality flags present: {', '.join(flags)}."] if flags else []


def _bounded_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_RESULTS:
        raise ToolInputError(f"limit must be an integer from 1 to {MAX_RESULTS}")
    return value


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or _UNSAFE_TEXT.search(value):
        raise ToolInputError(f"{name} is not a permitted identifier")
    return value


def _optional_identifier(value: str | None, name: str) -> str | None:
    return _identifier(value, name) if value is not None else None


def _time(value: str | datetime, name: str) -> datetime:
    if isinstance(value, str):
        _reject_unsafe(value)
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ToolInputError(f"{name} must be an ISO-8601 UTC timestamp") from error
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ToolInputError(f"{name} must include a UTC offset")
    return value.astimezone(UTC)


def _window(start: datetime, end: datetime) -> None:
    if end <= start:
        raise ToolInputError("time range must have an end after its start")
    if end - start > MAX_OBSERVATION_WINDOW:
        raise ToolInputError("time range exceeds the seven-day read-only tool bound")
    if datetime.now(UTC) - start > MAX_RECENT_LOOKBACK:
        raise ToolInputError("time range is older than the 31-day assistant retrieval bound")


def _reject_unsafe(value: Any) -> None:
    if isinstance(value, str) and _UNSAFE_TEXT.search(value):
        raise ToolInputError("tool input contains a prohibited instruction or query fragment")
    if isinstance(value, dict):
        for key, nested in value.items():
            _reject_unsafe(key)
            _reject_unsafe(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_unsafe(nested)


def _limit_note(truncated: bool) -> list[str]:
    return (
        [f"Results were truncated at the hard limit of {MAX_RESULTS} records."] if truncated else []
    )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
