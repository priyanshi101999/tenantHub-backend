"""add overdue task status

Revision ID: a51d2e89b7c4
Revises: fa7cce80ca94
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a51d2e89b7c4"
down_revision: Union[str, Sequence[str], None] = "fa7cce80ca94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'OVERDUE'")


def downgrade() -> None:
    op.execute("UPDATE tasks SET status = 'TODO' WHERE status = 'OVERDUE'")
    old_status = sa.Enum("TODO", "IN_PROGRESS", "DONE", name="taskstatus_old")
    old_status.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "tasks",
        "status",
        type_=old_status,
        existing_type=sa.Enum(name="taskstatus"),
        postgresql_using="status::text::taskstatus_old",
    )
    op.execute("DROP TYPE taskstatus")
    op.execute("ALTER TYPE taskstatus_old RENAME TO taskstatus")
