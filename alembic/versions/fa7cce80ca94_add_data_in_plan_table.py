"""add data in plan table

Revision ID: fa7cce80ca94
Revises: c7c5b4fed824
Create Date: 2026-06-09 12:22:30.195767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa7cce80ca94'
down_revision: Union[str, Sequence[str], None] = 'c7c5b4fed824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO plans (
            id,
            name,
            price,
            created_at,
            updated_at,
            is_active,
            max_tasks,
            max_users,
            stripe_price_id
        )
        VALUES
            (3, 'FREE', 0, '2026-05-31 16:13:10.892341', '2026-05-31 16:13:10.892341', true, 20, 5, 'price_zero'),
            (4, 'PRO', 9, '2026-05-31 16:13:10.892341', '2026-05-31 16:13:10.892341', true, 500, 25, 'price_1TdohUF2Otih1ahbKUlTFyfA'),
            (5, 'ENTERPRISE', 29, '2026-05-31 16:13:10.892341', '2026-05-31 16:13:10.892341', true, 999999, 999999, 'price_1TdomXF2Otih1ahbUYJIq0nt')
        ON CONFLICT (name) DO UPDATE SET
            price = EXCLUDED.price,
            updated_at = EXCLUDED.updated_at,
            is_active = EXCLUDED.is_active,
            max_tasks = EXCLUDED.max_tasks,
            max_users = EXCLUDED.max_users,
            stripe_price_id = EXCLUDED.stripe_price_id
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DELETE FROM plans
        WHERE name IN ('FREE', 'PRO', 'ENTERPRISE')
        """
    )
