"""Initial CareerPilot persistence schema."""

from alembic import op

from careerpilot.core import Base

revision = "0001"
down_revision = None


def upgrade() -> None:
    # ponytail: metadata is the single schema source until a second migration exists.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
