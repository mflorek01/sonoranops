from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    site_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_observations_idempotency_key"),)

    observation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    received_via: Mapped[str] = mapped_column(String(32))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id"), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    metric: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    record_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    quality_status: Mapped[str] = mapped_column(String(32), default="accepted")
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)

    asset: Mapped[Asset] = relationship()


class Finding(Base):
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    finding_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id"), index=True)
    detector_name: Mapped[str] = mapped_column(String(128))
    detector_version: Mapped[str] = mapped_column(String(32))
    window_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)
    data_quality_status: Mapped[str] = mapped_column(String(16), default="good")
    data_quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship()


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    asset: Mapped[Asset] = relationship()
    finding_links: Mapped[list[IncidentFinding]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    timeline_entries: Mapped[list[IncidentTimelineEntry]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentFinding(Base):
    __tablename__ = "incident_findings"
    __table_args__ = (UniqueConstraint("incident_id", "finding_id", name="uq_incident_findings"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id"), index=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.finding_id"), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    incident: Mapped[Incident] = relationship(back_populates="finding_links")
    finding: Mapped[Finding] = relationship()


class IncidentTimelineEntry(Base):
    __tablename__ = "incident_timeline_entries"
    __table_args__ = (
        UniqueConstraint("incident_id", "idempotency_key", name="uq_incident_timeline_idempotency"),
    )

    timeline_entry_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(128))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prior_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)

    incident: Mapped[Incident] = relationship(back_populates="timeline_entries")
