"""add sleep_score column to sleep_sessions

Revision ID: 6b6ce18cf7a4
Revises: 273d31ea2672
Create Date: 2026-01-06 13:36:45.946338

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b6ce18cf7a4"
down_revision: Union[str, Sequence[str], None] = "273d31ea2672"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sleep_sessions", sa.Column("sleep_score", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sleep_sessions", "sleep_score")
