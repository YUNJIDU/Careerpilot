"""Add versioned job descriptions."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("jd_versions"):
        return
    op.create_table(
        "jd_versions",
        sa.Column("jd_version_id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.application_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("create_key", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("source_title", sa.String(500), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("structure", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("application_id", "version"),
        sa.UniqueConstraint("application_id", "create_key"),
    )


def downgrade() -> None:
    op.drop_table("jd_versions")
