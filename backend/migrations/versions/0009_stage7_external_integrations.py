"""Add Stage 7 OAuth connections, reminders, notifications, and prefill sessions."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("oauth_connections"):
        op.create_table(
            "oauth_connections",
            sa.Column(
                "account_id",
                sa.String(100),
                sa.ForeignKey("mail_accounts.account_id"),
                primary_key=True,
            ),
            sa.Column("provider", sa.String(20), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("reminders"):
        op.create_table(
            "reminders",
            sa.Column("reminder_id", sa.String(36), primary_key=True),
            sa.Column(
                "application_id",
                sa.String(36),
                sa.ForeignKey("applications.application_id"),
                nullable=False,
            ),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("notification_events"):
        op.create_table(
            "notification_events",
            sa.Column("notification_id", sa.String(36), primary_key=True),
            sa.Column(
                "reminder_id",
                sa.String(36),
                sa.ForeignKey("reminders.reminder_id"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(30), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        )
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("prefill_sessions"):
        op.create_table(
            "prefill_sessions",
            sa.Column("session_id", sa.String(36), primary_key=True),
            sa.Column(
                "application_id",
                sa.String(36),
                sa.ForeignKey("applications.application_id"),
                nullable=False,
            ),
            sa.Column("target_origin", sa.String(500), nullable=False),
            sa.Column("field_values", sa.JSON(), nullable=False),
            sa.Column("diff", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("captcha_required", sa.Boolean(), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("prefill_sessions")
    op.drop_table("notification_events")
    op.drop_table("reminders")
    op.drop_table("oauth_connections")
