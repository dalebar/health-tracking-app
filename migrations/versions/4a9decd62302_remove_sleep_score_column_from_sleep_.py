"""remove sleep_score column from sleep_sessions

Revision ID: 4a9decd62302
Revises: 6b6ce18cf7a4
Create Date: 2026-01-06 14:19:59.815130

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a9decd62302"
down_revision: Union[str, Sequence[str], None] = "6b6ce18cf7a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("sleep_sessions", "sleep_score")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "sleep_sessions", sa.Column("sleep_score", sa.Integer(), nullable=True)
    )
