"""Add immutable Summary versions."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("summary_versions"):
        return
    op.create_table(
        "summary_versions",
        sa.Column("summary_id", sa.String(36), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(36),
            sa.ForeignKey("applications.application_id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("application_id", "version"),
    )


def downgrade() -> None:
    op.drop_table("summary_versions")
