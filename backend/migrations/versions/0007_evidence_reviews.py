"""Add resume-JD evidence maps and human reviews."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("evidence_map_versions"):
        op.create_table(
            "evidence_map_versions",
            sa.Column("map_id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.application_id"), nullable=False),
            sa.Column("jd_version_id", sa.String(36), sa.ForeignKey("jd_versions.jd_version_id"), nullable=False),
            sa.Column("resume_version_id", sa.String(36), sa.ForeignKey("resume_versions.version_id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("content", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("jd_version_id", "resume_version_id", "version"),
        )
    if not inspector.has_table("review_records"):
        op.create_table(
            "review_records",
            sa.Column("review_id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.application_id"), nullable=False),
            sa.Column("artifact_type", sa.String(30), nullable=False),
            sa.Column("artifact_id", sa.String(36), nullable=False),
            sa.Column("item_id", sa.String(80), nullable=False),
            sa.Column("decision", sa.String(30), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("review_records")
    op.drop_table("evidence_map_versions")
