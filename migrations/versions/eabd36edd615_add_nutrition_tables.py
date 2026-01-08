"""add nutrition tables

Revision ID: eabd36edd615
Revises: 69485b6ad5b7
Create Date: 2026-01-08 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "eabd36edd615"
down_revision: Union[str, Sequence[str], None] = "69485b6ad5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create nutrition_logs, daily_nutrition_summary, and nutrition_goals tables."""

    # Table 1: nutrition_logs - Individual meal/food entries from CSV
    op.create_table(
        "nutrition_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal", sa.String(length=20), nullable=False),
        sa.Column("time", sa.Time(), nullable=True),
        # Core macros
        sa.Column("calories", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("protein_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("carbohydrates_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("fiber_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("sugar_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Detailed fats
        sa.Column("saturated_fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column(
            "polyunsaturated_fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True
        ),
        sa.Column(
            "monounsaturated_fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True
        ),
        sa.Column("trans_fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Micros
        sa.Column("cholesterol_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("sodium_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("potassium_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("vitamin_a_pct", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("vitamin_c_pct", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("calcium_pct", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("iron_pct", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Metadata
        sa.Column("note", sa.TEXT(), nullable=True),
        sa.Column(
            "source", sa.String(length=50), server_default="myfitnesspal", nullable=True
        ),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Composite unique constraint for deduplication
        sa.UniqueConstraint(
            "user_id",
            "date",
            "meal",
            "time",
            "calories",
            "protein_g",
            name="uq_nutrition_log",
        ),
    )
    op.create_index(
        "idx_nutrition_logs_date",
        "nutrition_logs",
        ["date"],
        unique=False,
    )
    op.create_index(
        "idx_nutrition_logs_user_date",
        "nutrition_logs",
        ["user_id", "date"],
        unique=False,
    )

    # Table 2: daily_nutrition_summary - Aggregated daily totals
    op.create_table(
        "daily_nutrition_summary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("date", sa.Date(), nullable=False),
        # Totals
        sa.Column("total_calories", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("total_protein_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column(
            "total_carbohydrates_g", sa.DECIMAL(precision=8, scale=2), nullable=True
        ),
        sa.Column("total_fat_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("total_fiber_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("total_sugar_g", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("total_sodium_mg", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Meal breakdown
        sa.Column(
            "breakfast_calories", sa.DECIMAL(precision=8, scale=2), nullable=True
        ),
        sa.Column("lunch_calories", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("dinner_calories", sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column("snacks_calories", sa.DECIMAL(precision=8, scale=2), nullable=True),
        # Counts
        sa.Column("meal_count", sa.Integer(), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("user_id", "date", name="uq_daily_nutrition"),
    )
    op.create_index(
        "idx_daily_nutrition_date",
        "daily_nutrition_summary",
        ["date"],
        unique=False,
    )

    # Table 3: nutrition_goals - User's calorie/macro targets by day of week
    op.create_table(
        "nutrition_goals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("day_of_week", sa.Integer(), nullable=False),  # 0=Monday, 6=Sunday
        sa.Column("calorie_target", sa.Integer(), nullable=False),
        sa.Column("protein_target_g", sa.Integer(), nullable=False),
        # Macro percentages (should sum to 100)
        sa.Column("carb_pct", sa.Integer(), server_default="40", nullable=True),
        sa.Column("protein_pct", sa.Integer(), server_default="30", nullable=True),
        sa.Column("fat_pct", sa.Integer(), server_default="30", nullable=True),
        sa.Column(
            "effective_from",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "day_of_week", "effective_from", name="uq_nutrition_goal"
        ),
    )

    # Seed default nutrition goals for user 1
    op.execute(
        """
        INSERT INTO nutrition_goals (user_id, day_of_week, calorie_target, protein_target_g, carb_pct, protein_pct, fat_pct)
        VALUES
            (1, 0, 2550, 190, 40, 30, 30),  -- Monday
            (1, 1, 2850, 190, 40, 30, 30),  -- Tuesday (boxing)
            (1, 2, 2750, 190, 40, 30, 30),  -- Wednesday
            (1, 3, 2300, 180, 40, 30, 30),  -- Thursday (rest)
            (1, 4, 3200, 200, 40, 30, 30),  -- Friday (double session)
            (1, 5, 2850, 190, 40, 30, 30),  -- Saturday (boxing)
            (1, 6, 2550, 190, 40, 30, 30)   -- Sunday
        ON CONFLICT DO NOTHING
    """
    )


def downgrade() -> None:
    """Remove nutrition tables."""
    op.drop_table("nutrition_goals")
    op.drop_index("idx_daily_nutrition_date", table_name="daily_nutrition_summary")
    op.drop_table("daily_nutrition_summary")
    op.drop_index("idx_nutrition_logs_user_date", table_name="nutrition_logs")
    op.drop_index("idx_nutrition_logs_date", table_name="nutrition_logs")
    op.drop_table("nutrition_logs")
