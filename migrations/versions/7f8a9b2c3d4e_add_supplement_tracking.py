"""add supplement tracking tables

Revision ID: 7f8a9b2c3d4e
Revises: eabd36edd615
Create Date: 2026-01-10 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f8a9b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "eabd36edd615"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create supplements and supplement_logs tables."""

    # Table 1: supplements - Master list of supplements user takes
    op.create_table(
        "supplements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("dosage", sa.String(length=50), nullable=True),  # "5000 IU", "500mg"
        sa.Column(
            "dosage_unit", sa.String(length=20), nullable=True
        ),  # "IU", "mg", "g"
        sa.Column(
            "timing", sa.String(length=50), nullable=True
        ),  # "Morning", "With food", "Before bed"
        sa.Column(
            "frequency", sa.String(length=50), nullable=True, server_default="daily"
        ),  # "daily", "twice daily", "as needed"
        sa.Column(
            "category", sa.String(length=50), nullable=True
        ),  # "Vitamin", "Mineral", "Amino Acid", "Herb", "Other"
        # Nutritional content (for gap analysis)
        sa.Column("vitamin_a_iu", sa.Integer(), nullable=True),
        sa.Column("vitamin_c_mg", sa.Integer(), nullable=True),
        sa.Column("vitamin_d_iu", sa.Integer(), nullable=True),
        sa.Column("vitamin_e_iu", sa.Integer(), nullable=True),
        sa.Column("vitamin_k_mcg", sa.Integer(), nullable=True),
        sa.Column("vitamin_b12_mcg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("folate_mcg", sa.Integer(), nullable=True),
        sa.Column("calcium_mg", sa.Integer(), nullable=True),
        sa.Column("iron_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("magnesium_mg", sa.Integer(), nullable=True),
        sa.Column("zinc_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("omega3_mg", sa.Integer(), nullable=True),
        sa.Column("protein_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("creatine_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Status
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.TEXT(), nullable=True),
        sa.Column("purchase_url", sa.String(length=500), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_supplements_user_active",
        "supplements",
        ["user_id", "active"],
        unique=False,
    )

    # Table 2: supplement_logs - Daily tracking of supplement intake
    op.create_table(
        "supplement_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supplement_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("taken", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("taken_at", sa.Time(), nullable=True),  # Optional: time taken
        sa.Column(
            "dose_count", sa.Integer(), server_default="1", nullable=False
        ),  # Number of doses (e.g., 2 pills)
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
        # One log per supplement per day
        sa.UniqueConstraint(
            "user_id", "supplement_id", "date", name="uq_supplement_log"
        ),
    )
    op.create_index(
        "idx_supplement_logs_date",
        "supplement_logs",
        ["date"],
        unique=False,
    )
    op.create_index(
        "idx_supplement_logs_user_date",
        "supplement_logs",
        ["user_id", "date"],
        unique=False,
    )

    # Seed some common supplements for Dale's stack
    # (User can modify/add via API later)
    op.execute(
        """
        INSERT INTO supplements (user_id, name, dosage, dosage_unit, timing, category, vitamin_d_iu, active, notes)
        VALUES
            (1, 'Vitamin D3', '5000', 'IU', 'Morning with food', 'Vitamin', 5000, true, 'Essential for UK climate'),
            (1, 'Omega-3 Fish Oil', '2000', 'mg', 'With meals', 'Essential Fatty Acid', NULL, true, 'EPA/DHA for heart and brain'),
            (1, 'Magnesium Glycinate', '400', 'mg', 'Before bed', 'Mineral', NULL, true, 'Sleep and muscle recovery'),
            (1, 'Creatine Monohydrate', '5', 'g', 'Post-workout', 'Amino Acid', NULL, true, 'Strength and power'),
            (1, 'Vitamin B Complex', '1', 'tablet', 'Morning', 'Vitamin', NULL, true, 'Energy metabolism'),
            (1, 'Zinc', '25', 'mg', 'Evening', 'Mineral', NULL, true, 'Immune support')
        ON CONFLICT DO NOTHING
    """
    )


def downgrade() -> None:
    """Remove supplement tracking tables."""
    op.drop_index("idx_supplement_logs_user_date", table_name="supplement_logs")
    op.drop_index("idx_supplement_logs_date", table_name="supplement_logs")
    op.drop_table("supplement_logs")
    op.drop_index("idx_supplements_user_active", table_name="supplements")
    op.drop_table("supplements")
