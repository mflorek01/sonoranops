from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PRIVATE_FIELD_NAMES = {
    "expected_answer",
    "fault_label",
    "ground_truth",
    "hidden_truth",
    "scenario_id",
    "scenario_seed",
    "scenario_schedule",
}


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset")
    return value.astimezone(UTC)


def _contains_private_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in PRIVATE_FIELD_NAMES or _contains_private_field(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_private_field(item) for item in value)
    return False


class Source(ContractModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: Literal["telemetry", "file", "external_api"]
    received_via: Literal["api", "file_adapter", "external_adapter"]


class AssetRef(ContractModel):
    site_id: str = Field(min_length=1, max_length=128)
    asset_id: str = Field(min_length=1, max_length=128)


class ObservationInput(ContractModel):
    idempotency_key: str = Field(min_length=1, max_length=255)
    observed_at: datetime
    asset_ref: AssetRef
    kind: Literal[
        "telemetry",
        "production_record",
        "quality_result",
        "maintenance_record",
        "dispatch_record",
        "environmental_observation",
    ]
    metric: str | None = Field(default=None, max_length=128)
    value: float | None = None
    unit: str | None = Field(default=None, max_length=32)
    record_type: str | None = Field(default=None, max_length=128)
    source_recorded_at: datetime
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at", "source_recorded_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def telemetry_has_measurement(self) -> ObservationInput:
        if self.kind == "telemetry" and not all((self.metric, self.unit, self.value is not None)):
            raise ValueError("telemetry observations require metric, value, and unit")
        if self.kind != "telemetry" and self.record_type is None and self.metric is None:
            raise ValueError("non-telemetry observations require record_type or metric")
        if _contains_private_field(self.attributes):
            raise ValueError(
                "attributes must not contain scenario-private or evaluation-only fields"
            )
        return self


class ObservationBatchRequest(ContractModel):
    contract_version: Literal["1.0"]
    source: Source
    observations: list[ObservationInput] = Field(min_length=1, max_length=500)


class AssetResponse(ContractModel):
    site_id: str
    asset_id: str


class ObservationResponse(ContractModel):
    observation_id: str
    idempotency_key: str
    observed_at: datetime
    ingested_at: datetime
    source_recorded_at: datetime
    asset_ref: AssetRef
    kind: str
    metric: str | None
    value: float | None
    unit: str | None
    record_type: str | None
    attributes: dict[str, Any]
    quality_status: str
    quality_flags: list[str]


class ObservationBatchResponse(ContractModel):
    accepted_count: int
    duplicate_count: int
    flagged_count: int
    rejected_count: int = 0
    observations: list[ObservationResponse]


class AssistantToolRequest(ContractModel):
    """Structured request for deterministic, read-only synthetic-demo evidence tools."""

    site_id: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any]


class AssistantCitationResponse(ContractModel):
    object_id: str
    object_type: str
    timestamp: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    asset_id: str | None = None
    metric: str | None = None
    source_id: str | None = None
    note: str | None = None


class AssistantToolResponse(ContractModel):
    mode: Literal["deterministic_evidence_tool"]
    tool_name: str
    site_id: str
    records: list[dict[str, Any]]
    citations: list[AssistantCitationResponse]
    uncertainty_notes: list[str]
    truncated: bool


class FindingResponse(ContractModel):
    finding_id: str
    finding_type: str
    status: str
    asset_ref: AssetRef
    detector: dict[str, str]
    evaluated_window: dict[str, datetime]
    severity: str
    rationale: str
    evidence: list[dict[str, str]]
    data_quality_summary: dict[str, Any]
    created_at: datetime | None = None


class IncidentResponse(ContractModel):
    incident_id: str
    status: str
    title: str
    severity: str
    asset_refs: list[AssetRef]
    finding_ids: list[str]
    opened_at: datetime
    updated_at: datetime


class TimelineEntryResponse(ContractModel):
    timeline_entry_id: str
    occurred_at: datetime
    actor: str
    prior_status: str | None
    new_status: str
    reason: str | None
    evidence: list[dict[str, str]]


class IncidentDetailResponse(IncidentResponse):
    linked_findings: list[FindingResponse]
    linked_observations: list[ObservationResponse]
    timeline: list[TimelineEntryResponse]


class ReplayBoundaryResponse(ContractModel):
    """States exactly which stored timestamps and records underpin the briefing."""

    mode: Literal["stored_observation_replay"]
    observation_time_field: Literal["observed_at"]
    production_series_definition: Literal["production_record.attributes.throughput_tph"]
    window_start_at: datetime | None
    window_end_at: datetime | None
    calculation_note: str


class ProductionPointResponse(ContractModel):
    observation_id: str
    observed_at: datetime
    value: float
    unit: str | None
    quality_status: str
    quality_flags: list[str]


class ProductionBaselineResponse(ContractModel):
    method: Literal["median_of_clean_production_records"]
    value: float | None
    sample_count: int


class ProductionSummaryResponse(ContractModel):
    series: list[ProductionPointResponse]
    current: ProductionPointResponse | None
    baseline: ProductionBaselineResponse
    delta_vs_baseline: float | None


class DataQualityFlagCountResponse(ContractModel):
    flag: str
    observation_count: int


class AssetBriefingResponse(ContractModel):
    asset_id: str
    observation_count: int
    flagged_observation_count: int
    active_incident_count: int
    latest_observed_at: datetime | None


class OperationsBriefingResponse(ContractModel):
    """A transparent, database-derived read model for the public recruiter demo."""

    site_id: str
    replay_boundary: ReplayBoundaryResponse
    observation_count: int
    flagged_observation_count: int
    oldest_observed_at: datetime | None
    latest_observed_at: datetime | None
    production: ProductionSummaryResponse
    data_quality_flag_counts: list[DataQualityFlagCountResponse]
    assets: list[AssetBriefingResponse]


class IncidentTransitionRequest(ContractModel):
    to_status: Literal["acknowledged", "investigating", "mitigated", "resolved", "dismissed"]
    reason: str | None = Field(default=None, max_length=2000)
    actor: str = Field(min_length=1, max_length=128)


class ListResponse(ContractModel):
    items: list[Any]
    next_cursor: str | None = None


class ErrorDetail(ContractModel):
    path: str | None = None
    reason: str


class ErrorBody(ContractModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str


class ErrorResponse(ContractModel):
    error: ErrorBody
