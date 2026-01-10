"""
SQLAlchemy database models for health tracking application.

These models represent the database schema and provide an ORM (Object-Relational Mapping)
interface for interacting with the database using Python objects instead of raw SQL.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    Date,
    Time,
    TIMESTAMP,
    TEXT,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    Boolean,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from typing import Any, Optional
from datetime import date as date_type
from decimal import Decimal

# Base class for all models
# All tables will inherit from this
Base: Any = declarative_base()


class User(Base):
    """
    User model representing individuals in the system.

    Although this app is designed for a single user, using a users table
    makes the schema extensible for future multi-user support.
    """

    __tablename__ = "users"

    # Primary key - auto-incrementing integer
    id = Column(Integer, primary_key=True, autoincrement=True)

    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Physical attributes for health calculations
    height_cm: Optional[Decimal] = Column(DECIMAL(5, 2))  # type: ignore[assignment]
    date_of_birth = Column(Date)  # For age-based calculations (VO2 max, etc.)

    # Audit timestamps - automatically managed
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships to other tables (one-to-many)
    # These allow you to access related records easily:
    # user.body_metrics returns all body_metrics for this user
    body_metrics = relationship(
        "BodyMetric", back_populates="user", cascade="all, delete-orphan"
    )
    activity_metrics = relationship(
        "ActivityMetric", back_populates="user", cascade="all, delete-orphan"
    )
    heart_rate_metrics = relationship(
        "HeartRateMetric", back_populates="user", cascade="all, delete-orphan"
    )
    cardio_fitness = relationship(
        "CardioFitness", back_populates="user", cascade="all, delete-orphan"
    )
    sleep_sessions = relationship(
        "SleepSession", back_populates="user", cascade="all, delete-orphan"
    )
    workouts = relationship(
        "Workout", back_populates="user", cascade="all, delete-orphan"
    )
    nutrition_logs = relationship(
        "NutritionLog", back_populates="user", cascade="all, delete-orphan"
    )
    daily_nutrition_summaries = relationship(
        "DailyNutritionSummary", back_populates="user", cascade="all, delete-orphan"
    )
    nutrition_goals = relationship(
        "NutritionGoal", back_populates="user", cascade="all, delete-orphan"
    )
    supplements = relationship(
        "Supplement", back_populates="user", cascade="all, delete-orphan"
    )
    supplement_logs = relationship(
        "SupplementLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"


class BodyMetric(Base):
    """
    Body measurements like weight, body fat percentage, BMI.

    Uses a flexible metric_type field to support multiple measurement types
    without requiring schema changes.
    """

    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Metric identification
    metric_type = Column(String(50), nullable=False)  # 'weight', 'body_fat', 'bmi'
    value: Decimal = Column(DECIMAL(10, 3), nullable=False)  # type: ignore[assignment]
    unit = Column(String(20), nullable=False)  # 'kg', '%', etc.

    # Temporal information
    recorded_at = Column(TIMESTAMP, nullable=False)

    # Metadata
    source = Column(String(100))  # 'apple_health', 'manual', 'withings_scale'
    notes = Column(TEXT)  # Optional user notes

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="body_metrics")

    # Constraints
    __table_args__ = (
        # Prevent duplicate entries for same metric at same time
        UniqueConstraint(
            "user_id", "metric_type", "recorded_at", name="uq_body_metric"
        ),
        # Index for fast queries by user, type, and date
        Index(
            "idx_body_metrics_user_type_date", "user_id", "metric_type", "recorded_at"
        ),
    )

    def __repr__(self) -> str:
        return f"<BodyMetric(type='{self.metric_type}', value={self.value}{self.unit}, recorded_at={self.recorded_at})>"


class ActivityMetric(Base):
    """
    Activity measurements like steps, active energy burned, exercise minutes.

    These metrics are typically aggregated daily by Apple Health.
    """

    __tablename__ = "activity_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Metric identification
    metric_type = Column(
        String(50), nullable=False
    )  # 'steps', 'active_energy', 'exercise_minutes'
    value: Decimal = Column(DECIMAL(10, 3), nullable=False)  # type: ignore[assignment]
    unit = Column(String(20), nullable=False)  # 'count', 'kcal', 'minutes'

    # Temporal information
    recorded_at = Column(TIMESTAMP, nullable=False)
    date = Column(Date, nullable=False)  # Aggregation helper for daily sums

    # Metadata
    source = Column(String(100))

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="activity_metrics")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "metric_type", "date", name="uq_activity_metric"),
        Index("idx_activity_metrics_user_type_date", "user_id", "metric_type", "date"),
    )

    def __repr__(self) -> str:
        return f"<ActivityMetric(type='{self.metric_type}', value={self.value}{self.unit}, date={self.date})>"


class HeartRateMetric(Base):
    """
    Heart rate related measurements: resting HR, walking HR, HRV.

    These are typically calculated daily by Apple Health based on continuous monitoring.
    """

    __tablename__ = "heart_rate_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Metric identification
    metric_type = Column(
        String(50), nullable=False
    )  # 'resting_hr', 'walking_hr', 'hrv'
    value: Decimal = Column(DECIMAL(10, 3), nullable=False)  # type: ignore[assignment]
    unit = Column(String(20), nullable=False)  # 'bpm', 'ms'

    # Temporal information
    recorded_at = Column(TIMESTAMP, nullable=False)
    date = Column(Date, nullable=False)

    # Metadata
    source = Column(String(100))

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="heart_rate_metrics")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "metric_type", "date", name="uq_hr_metric"),
        Index("idx_hr_metrics_user_type_date", "user_id", "metric_type", "date"),
    )

    def __repr__(self) -> str:
        return f"<HeartRateMetric(type='{self.metric_type}', value={self.value}{self.unit}, date={self.date})>"


class CardioFitness(Base):
    """
    Cardio fitness (VO2 max) measurements.

    VO2 max is calculated periodically by Apple Watch and represents cardiovascular fitness level.
    """

    __tablename__ = "cardio_fitness"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Measurement
    vo2_max: Decimal = Column(DECIMAL(5, 2), nullable=False)  # type: ignore[assignment]

    # Temporal information
    recorded_at = Column(TIMESTAMP, nullable=False)

    # Metadata
    source = Column(String(100))

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="cardio_fitness")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "recorded_at", name="uq_cardio_fitness"),
        Index("idx_cardio_fitness_user_date", "user_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<CardioFitness(vo2_max={self.vo2_max}, recorded_at={self.recorded_at})>"
        )


class SleepSession(Base):
    """
    Sleep session data with duration and stage breakdowns.

    Sleep sessions can span across calendar dates (go to bed on Jan 3, wake on Jan 4).
    Apple Watch tracks sleep stages: awake, REM, core (light), and deep sleep.
    """

    __tablename__ = "sleep_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Sleep timing
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)

    # Duration breakdowns (in minutes)
    total_duration_minutes = Column(Integer, nullable=False)
    awake_minutes = Column(Integer)
    rem_minutes = Column(Integer)
    core_minutes = Column(Integer)  # Light sleep
    deep_minutes = Column(Integer)

    # Metadata
    source = Column(String(100))
    notes = Column(TEXT)

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="sleep_sessions")

    # Constraints
    __table_args__ = (
        # Ensure end_time is after start_time (data validation at database level)
        CheckConstraint("end_time > start_time", name="ck_valid_sleep_duration"),
        UniqueConstraint("user_id", "start_time", name="uq_sleep_session"),
        Index("idx_sleep_sessions_user_date", "user_id", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<SleepSession(start={self.start_time}, duration={self.total_duration_minutes}min)>"


class Workout(Base):
    """
    Workout sessions from Apple Health.

    Stores aggregated workout data including heart rate metrics, energy expenditure,
    and distance. Heart rate zones can be calculated on-demand from avg/min/max HR.
    """

    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Workout identification
    workout_type = Column(String(50), nullable=False)  # 'Boxing', 'Running', etc.
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    duration_minutes: Decimal = Column(DECIMAL(10, 2), nullable=False)  # type: ignore[assignment]

    # Energy metrics (in kcal)
    active_energy_kcal: Optional[Decimal] = Column(DECIMAL(10, 2))  # type: ignore[assignment]
    basal_energy_kcal: Optional[Decimal] = Column(DECIMAL(10, 2))  # type: ignore[assignment]
    total_energy_kcal: Optional[Decimal] = Column(DECIMAL(10, 2))  # type: ignore[assignment]

    # Distance (nullable - not all workouts have distance)
    distance_km: Optional[Decimal] = Column(DECIMAL(10, 3))  # type: ignore[assignment]

    # Heart rate aggregates (nullable - older workouts may not have HR)
    avg_heart_rate_bpm = Column(Integer)
    min_heart_rate_bpm = Column(Integer)
    max_heart_rate_bpm = Column(Integer)

    # Metadata
    source = Column(String(100))
    indoor_workout = Column(Boolean, default=False)

    # Audit timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="workouts")

    # Constraints
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_valid_workout_duration"),
        UniqueConstraint("user_id", "start_time", name="uq_workout"),
        Index("idx_workouts_user_type_date", "user_id", "workout_type", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<Workout(type='{self.workout_type}', start={self.start_time}, duration={self.duration_minutes}min)>"


class NutritionLog(Base):
    """
    Individual meal/food entries from MyFitnessPal CSV exports.

    Each row represents a single food item logged in MFP.
    Multiple entries per meal are common (e.g., breakfast has eggs, toast, coffee).
    """

    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1
    )

    # Temporal
    date = Column(Date, nullable=False)
    meal = Column(String(20), nullable=False)  # Breakfast, Lunch, Dinner, Snacks
    time = Column(Time, nullable=True)  # Can be empty in CSV

    # Core macros
    calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    protein_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    carbohydrates_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    fiber_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    sugar_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Detailed fats
    saturated_fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    polyunsaturated_fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    monounsaturated_fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    trans_fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Micros
    cholesterol_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    sodium_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    potassium_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    vitamin_a_pct: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    vitamin_c_pct: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    calcium_pct: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    iron_pct: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Metadata
    note = Column(TEXT)
    source = Column(String(50), default="myfitnesspal")
    source_file = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="nutrition_logs")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "date",
            "meal",
            "time",
            "calories",
            "protein_g",
            name="uq_nutrition_log",
        ),
        Index("idx_nutrition_logs_date", "date"),
        Index("idx_nutrition_logs_user_date", "user_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<NutritionLog(date={self.date}, meal='{self.meal}', calories={self.calories})>"


class DailyNutritionSummary(Base):
    """
    Aggregated daily nutrition totals computed from nutrition_logs.

    Provides quick access to daily totals without re-aggregating logs.
    Updated after each import.
    """

    __tablename__ = "daily_nutrition_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1
    )
    date = Column(Date, nullable=False)

    # Totals
    total_calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_protein_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_carbohydrates_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_fat_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_fiber_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_sugar_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    total_sodium_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Meal breakdown
    breakfast_calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    lunch_calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    dinner_calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    snacks_calories: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Counts
    meal_count = Column(Integer)
    entry_count = Column(Integer)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="daily_nutrition_summaries")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_nutrition"),
        Index("idx_daily_nutrition_date", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<DailyNutritionSummary(date={self.date}, calories={self.total_calories})>"
        )


class NutritionGoal(Base):
    """
    User's calorie and macro targets by day of week.

    Different days can have different targets based on training schedule.
    """

    __tablename__ = "nutrition_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1
    )
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday

    calorie_target = Column(Integer, nullable=False)
    protein_target_g = Column(Integer, nullable=False)

    # Macro percentages (should sum to 100)
    carb_pct = Column(Integer, default=40)
    protein_pct = Column(Integer, default=30)
    fat_pct = Column(Integer, default=30)

    effective_from = Column(Date, default=date_type.today)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="nutrition_goals")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id", "day_of_week", "effective_from", name="uq_nutrition_goal"
        ),
    )

    def __repr__(self) -> str:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        dow: int = int(self.day_of_week) if self.day_of_week is not None else -1  # type: ignore[arg-type]
        day_name = days[dow] if 0 <= dow <= 6 else "?"
        return f"<NutritionGoal({day_name}: {self.calorie_target}kcal, {self.protein_target_g}g protein)>"


class Supplement(Base):
    """
    Master list of supplements a user takes.

    Includes dosage information and nutritional content for gap analysis.
    """

    __tablename__ = "supplements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1
    )

    # Basic info
    name = Column(String(100), nullable=False)
    brand = Column(String(100))
    dosage = Column(String(50))  # "5000", "500"
    dosage_unit = Column(String(20))  # "IU", "mg", "g"
    timing = Column(String(50))  # "Morning", "With food", "Before bed"
    frequency = Column(String(50), default="daily")  # "daily", "twice daily"
    category = Column(String(50))  # "Vitamin", "Mineral", "Amino Acid"

    # Nutritional content (for gap analysis)
    vitamin_a_iu = Column(Integer)
    vitamin_c_mg = Column(Integer)
    vitamin_d_iu = Column(Integer)
    vitamin_e_iu = Column(Integer)
    vitamin_k_mcg = Column(Integer)
    vitamin_b12_mcg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    folate_mcg = Column(Integer)
    calcium_mg = Column(Integer)
    iron_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    magnesium_mg = Column(Integer)
    zinc_mg: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    omega3_mg = Column(Integer)
    protein_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]
    creatine_g: Optional[Decimal] = Column(DECIMAL(8, 2))  # type: ignore[assignment]

    # Status
    active = Column(Boolean, default=True, nullable=False)
    notes = Column(TEXT)
    purchase_url = Column(String(500))

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="supplements")
    logs = relationship(
        "SupplementLog", back_populates="supplement", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (Index("idx_supplements_user_active", "user_id", "active"),)

    def __repr__(self) -> str:
        return f"<Supplement(name='{self.name}', dosage='{self.dosage} {self.dosage_unit}')>"


class SupplementLog(Base):
    """
    Daily tracking of supplement intake.

    One record per supplement per day to track adherence.
    """

    __tablename__ = "supplement_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1
    )
    supplement_id = Column(
        Integer, ForeignKey("supplements.id", ondelete="CASCADE"), nullable=False
    )

    # Tracking
    date = Column(Date, nullable=False)
    taken = Column(Boolean, default=True, nullable=False)
    taken_at = Column(Time)  # Optional: specific time
    dose_count = Column(Integer, default=1, nullable=False)  # Number of doses
    notes = Column(TEXT)

    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="supplement_logs")
    supplement = relationship("Supplement", back_populates="logs")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "supplement_id", "date", name="uq_supplement_log"),
        Index("idx_supplement_logs_date", "date"),
        Index("idx_supplement_logs_user_date", "user_id", "date"),
    )

    def __repr__(self) -> str:
        status = "✓" if self.taken else "✗"
        return f"<SupplementLog(supplement_id={self.supplement_id}, date={self.date}, taken={status})>"
