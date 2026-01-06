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
    TIMESTAMP,
    TEXT,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from typing import Any, Optional
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
