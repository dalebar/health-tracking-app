"""simplify supplements remove logs and columns

Revision ID: 8a1b2c3d4e5f
Revises: 7f8a9b2c3d4e
Create Date: 2026-01-10 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "7f8a9b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop supplement_logs table and remove unused columns from supplements."""

    # Drop supplement_logs table
    op.drop_index("idx_supplement_logs_user_date", table_name="supplement_logs")
    op.drop_index("idx_supplement_logs_date", table_name="supplement_logs")
    op.drop_table("supplement_logs")

    # Drop unused columns from supplements table
    op.drop_column("supplements", "brand")
    op.drop_column("supplements", "frequency")
    op.drop_column("supplements", "category")
    op.drop_column("supplements", "vitamin_a_iu")
    op.drop_column("supplements", "vitamin_c_mg")
    op.drop_column("supplements", "vitamin_d_iu")
    op.drop_column("supplements", "vitamin_e_iu")
    op.drop_column("supplements", "vitamin_k_mcg")
    op.drop_column("supplements", "vitamin_b12_mcg")
    op.drop_column("supplements", "folate_mcg")
    op.drop_column("supplements", "calcium_mg")
    op.drop_column("supplements", "iron_mg")
    op.drop_column("supplements", "magnesium_mg")
    op.drop_column("supplements", "zinc_mg")
    op.drop_column("supplements", "omega3_mg")
    op.drop_column("supplements", "protein_g")
    op.drop_column("supplements", "creatine_g")
    op.drop_column("supplements", "notes")
    op.drop_column("supplements", "purchase_url")


def downgrade() -> None:
    """Restore supplement_logs table and columns."""

    # Restore columns to supplements table
    op.add_column(
        "supplements", sa.Column("brand", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "supplements",
        sa.Column(
            "frequency", sa.String(length=50), nullable=True, server_default="daily"
        ),
    )
    op.add_column(
        "supplements", sa.Column("category", sa.String(length=50), nullable=True)
    )
    op.add_column("supplements", sa.Column("vitamin_a_iu", sa.Integer(), nullable=True))
    op.add_column("supplements", sa.Column("vitamin_c_mg", sa.Integer(), nullable=True))
    op.add_column("supplements", sa.Column("vitamin_d_iu", sa.Integer(), nullable=True))
    op.add_column("supplements", sa.Column("vitamin_e_iu", sa.Integer(), nullable=True))
    op.add_column(
        "supplements", sa.Column("vitamin_k_mcg", sa.Integer(), nullable=True)
    )
    op.add_column(
        "supplements",
        sa.Column("vitamin_b12_mcg", sa.DECIMAL(precision=8, scale=2), nullable=True),
    )
    op.add_column("supplements", sa.Column("folate_mcg", sa.Integer(), nullable=True))
    op.add_column("supplements", sa.Column("calcium_mg", sa.Integer(), nullable=True))
    op.add_column(
        "supplements",
        sa.Column("iron_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
    )
    op.add_column("supplements", sa.Column("magnesium_mg", sa.Integer(), nullable=True))
    op.add_column(
        "supplements",
        sa.Column("zinc_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
    )
    op.add_column("supplements", sa.Column("omega3_mg", sa.Integer(), nullable=True))
    op.add_column(
        "supplements",
        sa.Column("protein_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
    )
    op.add_column(
        "supplements",
        sa.Column("creatine_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
    )
    op.add_column("supplements", sa.Column("notes", sa.TEXT(), nullable=True))
    op.add_column(
        "supplements", sa.Column("purchase_url", sa.String(length=500), nullable=True)
    )

    # Restore supplement_logs table
    op.create_table(
        "supplement_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supplement_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("taken", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("taken_at", sa.Time(), nullable=True),
        sa.Column("dose_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("notes", sa.TEXT(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supplement_id"], ["supplements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "supplement_id", "date", name="uq_supplement_log"
        ),
    )
    op.create_index(
        "idx_supplement_logs_date", "supplement_logs", ["date"], unique=False
    )
    op.create_index(
        "idx_supplement_logs_user_date",
        "supplement_logs",
        ["user_id", "date"],
        unique=False,
    )
