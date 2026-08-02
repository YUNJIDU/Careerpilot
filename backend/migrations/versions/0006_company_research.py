"""Add versioned company research."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("company_research_versions"):
        return
    op.create_table(
        "company_research_versions",
        sa.Column("research_id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.application_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("application_id", "version"),
    )


def downgrade() -> None:
    op.drop_table("company_research_versions")
