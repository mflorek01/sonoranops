"""Initial platform operational data model.

Revision ID: 20260808_0001
Revises:
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260808_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("asset_id", sa.String(length=128), primary_key=True),
        sa.Column("site_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assets_site_id", "assets", ["site_id"])

    op.create_table(
        "observations",
        sa.Column("observation_id", sa.String(length=36), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("received_via", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=128), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=128), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("record_type", sa.String(length=128), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_observations_idempotency_key"),
    )
    for column in ("source_id", "asset_id", "kind", "metric", "observed_at", "source_recorded_at", "ingested_at"):
        op.create_index(f"ix_observations_{column}", "observations", [column])

    op.create_table(
        "findings",
        sa.Column("finding_id", sa.String(length=36), primary_key=True),
        sa.Column("finding_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=128), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("detector_name", sa.String(length=128), nullable=False),
        sa.Column("detector_version", sa.String(length=32), nullable=False),
        sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("data_quality_status", sa.String(length=16), nullable=False),
        sa.Column("data_quality_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("finding_type", "status", "asset_id"):
        op.create_index(f"ix_findings_{column}", "findings", [column])

    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=128), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("asset_id", "status"):
        op.create_index(f"ix_incidents_{column}", "incidents", [column])

    op.create_table(
        "incident_findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("incident_id", sa.String(length=36), sa.ForeignKey("incidents.incident_id"), nullable=False),
        sa.Column("finding_id", sa.String(length=36), sa.ForeignKey("findings.finding_id"), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("incident_id", "finding_id", name="uq_incident_findings"),
    )
    op.create_index("ix_incident_findings_incident_id", "incident_findings", ["incident_id"])
    op.create_index("ix_incident_findings_finding_id", "incident_findings", ["finding_id"])

    op.create_table(
        "incident_timeline_entries",
        sa.Column("timeline_entry_id", sa.String(length=36), primary_key=True),
        sa.Column("incident_id", sa.String(length=36), sa.ForeignKey("incidents.incident_id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("prior_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("incident_id", "idempotency_key", name="uq_incident_timeline_idempotency"),
    )
    op.create_index("ix_incident_timeline_entries_incident_id", "incident_timeline_entries", ["incident_id"])


def downgrade() -> None:
    op.drop_table("incident_timeline_entries")
    op.drop_table("incident_findings")
    op.drop_table("incidents")
    op.drop_table("findings")
    op.drop_table("observations")
    op.drop_table("assets")
