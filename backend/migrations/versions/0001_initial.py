"""Initial CareerPilot persistence schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("application_id", sa.String(36), primary_key=True),
        sa.Column("create_key", sa.String(200), nullable=False, unique=True),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("role", sa.String(200), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("user_fields", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "application_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(36),
            sa.ForeignKey("applications.application_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "field_provenance",
        sa.Column("provenance_id", sa.String(36), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(36),
            sa.ForeignKey("applications.application_id"),
            nullable=False,
        ),
        sa.Column("field", sa.String(100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "email_records",
        sa.Column("email_id", sa.String(64), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(36),
            sa.ForeignKey("applications.application_id"),
            nullable=True,
        ),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("message_id", sa.String(500), nullable=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("sender", sa.String(500), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sync_batches",
        sa.Column("batch_id", sa.String(36), primary_key=True),
        sa.Column("batch_type", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("baseline", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "background_jobs",
        sa.Column("job_id", sa.String(36), primary_key=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "job_checkpoints",
        sa.Column("checkpoint_id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("background_jobs.job_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("step", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("job_checkpoints")
    op.drop_table("background_jobs")
    op.drop_table("sync_batches")
    op.drop_table("email_records")
    op.drop_table("field_provenance")
    op.drop_table("application_events")
    op.drop_table("applications")
