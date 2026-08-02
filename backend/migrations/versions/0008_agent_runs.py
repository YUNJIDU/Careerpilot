"""Add bounded agent runs, tool calls, and human approvals."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("agent_runs"):
        op.create_table(
            "agent_runs",
            sa.Column(
                "run_id",
                sa.String(36),
                sa.ForeignKey("background_jobs.job_id"),
                primary_key=True,
            ),
            sa.Column(
                "application_id",
                sa.String(36),
                sa.ForeignKey("applications.application_id"),
                nullable=False,
            ),
            sa.Column("request_text", sa.Text(), nullable=False),
            sa.Column("model_name", sa.String(200), nullable=False),
            sa.Column("prompt_version", sa.String(30), nullable=False),
            sa.Column("processor_version", sa.String(30), nullable=False),
            sa.Column("max_steps", sa.Integer(), nullable=False),
            sa.Column("steps_used", sa.Integer(), nullable=False),
            sa.Column("max_model_calls", sa.Integer(), nullable=False),
            sa.Column("model_calls_used", sa.Integer(), nullable=False),
            sa.Column("max_tool_calls", sa.Integer(), nullable=False),
            sa.Column("tool_calls_used", sa.Integer(), nullable=False),
            sa.Column("max_write_approvals", sa.Integer(), nullable=False),
            sa.Column("write_approvals_used", sa.Integer(), nullable=False),
            sa.Column("max_elapsed_seconds", sa.Integer(), nullable=False),
            sa.Column("elapsed_ms", sa.Integer(), nullable=False),
            sa.Column("final_output", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("agent_tool_calls"):
        op.create_table(
            "agent_tool_calls",
            sa.Column("tool_call_id", sa.String(36), primary_key=True),
            sa.Column(
                "run_id",
                sa.String(36),
                sa.ForeignKey("agent_runs.run_id"),
                nullable=False,
            ),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("tool_name", sa.String(100), nullable=False),
            sa.Column("tool_version", sa.String(30), nullable=False),
            sa.Column("risk_level", sa.String(30), nullable=False),
            sa.Column("arguments", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("result_refs", sa.JSON(), nullable=False),
            sa.Column("result_summary_safe", sa.Text(), nullable=True),
            sa.Column("error_code", sa.String(100), nullable=True),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("run_id", "sequence"),
        )
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("agent_approvals"):
        op.create_table(
            "agent_approvals",
            sa.Column("approval_id", sa.String(36), primary_key=True),
            sa.Column(
                "tool_call_id",
                sa.String(36),
                sa.ForeignKey("agent_tool_calls.tool_call_id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("request_summary", sa.Text(), nullable=False),
            sa.Column("application_version", sa.Integer(), nullable=False),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("agent_approvals")
    op.drop_table("agent_tool_calls")
    op.drop_table("agent_runs")
