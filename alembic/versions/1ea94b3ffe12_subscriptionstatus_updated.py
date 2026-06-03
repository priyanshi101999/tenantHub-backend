"""SubscriptionStatus updated

Revision ID: 1ea94b3ffe12
Revises: 6e7a23cea672
Create Date: 2026-06-03 07:15:54.152981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ea94b3ffe12'
down_revision: Union[str, Sequence[str], None] = '6e7a23cea672'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'INCOMPLETE'")
    op.execute("ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'PAST_DUE'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
