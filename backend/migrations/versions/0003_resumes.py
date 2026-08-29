"""Add minimal versioned resumes and one current resume per application."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
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
            sa.Column(
                "application_id",
                sa.String(36),
                sa.ForeignKey("applications.application_id"),
                primary_key=True,
            ),
            sa.Column(
                "version_id",
                sa.String(36),
                sa.ForeignKey("resume_versions.version_id"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_table("application_resumes")
    op.drop_table("resume_versions")
