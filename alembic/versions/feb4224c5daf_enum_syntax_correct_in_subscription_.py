"""Enum syntax correct in subscription table

Revision ID: feb4224c5daf
Revises: 1ea94b3ffe12
Create Date: 2026-06-03 10:45:35.087036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'feb4224c5daf'
down_revision: Union[str, Sequence[str], None] = '1ea94b3ffe12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "subscriptions",
        "status",
        type_=sa.Enum(name="subscriptionstatus"),
        existing_type=sa.String(),
        postgresql_using="status::text::subscriptionstatus"
    )
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    op.alter_column(
        "subscriptions",
        "status",
        type_=sa.String(),
        existing_type=sa.Enum(name="subscriptionstatus"),
        postgresql_using="status::text"
    )
    pass
    # ### end Alembic commands ###
