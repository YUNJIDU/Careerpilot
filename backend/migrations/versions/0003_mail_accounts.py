"""Add persistent mail accounts."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("mail_accounts"):
        return
    op.create_table(
        "mail_accounts",
        sa.Column("account_id", sa.String(100), primary_key=True),
        sa.Column("adapter", sa.String(30), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("adapter", "email"),
    )


def downgrade() -> None:
    op.drop_table("mail_accounts")
