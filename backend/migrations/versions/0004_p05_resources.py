"""Add approved attachments and versioned resumes."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("attachments"):
        op.create_table(
            "attachments",
            sa.Column("attachment_id", sa.String(36), primary_key=True),
            sa.Column(
                "email_id", sa.String(64), sa.ForeignKey("email_records.email_id"), nullable=False
            ),
            sa.Column("account_id", sa.String(100), nullable=False),
            sa.Column("source_id", sa.String(300), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(200), nullable=False),
            sa.Column("size", sa.Integer(), nullable=True),
            sa.Column("allowed", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("rejection_reason", sa.String(200), nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("account_id", "source_id"),
        )
    if not inspector.has_table("resume_versions"):
        op.create_table(
            "resume_versions",
            sa.Column("version_id", sa.String(36), primary_key=True),
            sa.Column("resume_id", sa.String(36), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(200), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("resume_id", "version"),
            sa.UniqueConstraint("resume_id", "content_hash"),
        )
    if not inspector.has_table("application_resumes"):
        op.create_table(
            "application_resumes",
            sa.Column("link_id", sa.String(36), primary_key=True),
            sa.Column(
                "application_id",
                sa.String(36),
                sa.ForeignKey("applications.application_id"),
                nullable=False,
            ),
            sa.Column(
                "version_id",
                sa.String(36),
                sa.ForeignKey("resume_versions.version_id"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("application_id", "version_id"),
        )


def downgrade() -> None:
    op.drop_table("application_resumes")
    op.drop_table("resume_versions")
    op.drop_table("attachments")
