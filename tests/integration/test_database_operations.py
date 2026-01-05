"""
Integration tests for database operations.

These tests verify:
- CRUD operations work correctly
- Constraints are enforced (unique, foreign key)
- Cascade deletes work as expected
- Data integrity is maintained
"""

from datetime import datetime, date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.models import User, BodyMetric, ActivityMetric
from src.db.session import get_db_context


@pytest.fixture
def test_user():
    """
    Create a test user for integration tests.

    Yields a user object, then cleans up after test completes.
    """
    with get_db_context() as db:
        # Clean up any existing test user
        db.query(User).filter(User.email == "test@example.com").delete()
        db.commit()

        user = User(
            email="test@example.com",
            name="Test User",
            height_cm=Decimal("185.00"),
            date_of_birth=date(1990, 1, 1),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id  # Store ID before yielding

        yield user

        # Cleanup after test
        with get_db_context() as cleanup_db:
            cleanup_db.query(User).filter(User.id == user_id).delete()
            cleanup_db.commit()


class TestDatabaseOperations:
    """Test database CRUD operations and constraints."""

    def test_insert_and_retrieve_weight(self, test_user):
        """Test inserting and querying weight data."""
        with get_db_context() as db:
            # Insert weight
            weight = BodyMetric(
                user_id=test_user.id,
                metric_type="weight",
                value=Decimal("100.5"),
                unit="kg",
                recorded_at=datetime(2025, 12, 30, 8, 0, 0),
                source="test",
            )
            db.add(weight)
            db.commit()

            # Query back
            result = (
                db.query(BodyMetric)
                .filter(
                    BodyMetric.user_id == test_user.id,
                    BodyMetric.metric_type == "weight",
                )
                .first()
            )

            assert result is not None
            assert result.value == Decimal("100.5")
            assert result.unit == "kg"
            assert result.source == "test"
            assert result.metric_type == "weight"

    def test_insert_activity_metric(self, test_user):
        """Test inserting activity metrics with date field."""
        with get_db_context() as db:
            metric_date = date(2025, 12, 30)

            metric = ActivityMetric(
                user_id=test_user.id,
                metric_type="steps",
                value=Decimal("10000"),
                unit="count",
                date=metric_date,
                recorded_at=datetime.combine(metric_date, datetime.min.time()),
                source="test",
            )
            db.add(metric)
            db.commit()

            # Query back
            result = (
                db.query(ActivityMetric)
                .filter(
                    ActivityMetric.user_id == test_user.id,
                    ActivityMetric.metric_type == "steps",
                )
                .first()
            )

            assert result is not None
            assert result.value == Decimal("10000")
            assert result.date == metric_date

    def test_unique_constraint_prevents_duplicate_body_metrics(self, test_user):
        """Test that unique constraint prevents duplicate weight entries."""
        with get_db_context() as db:
            recorded_time = datetime(2025, 12, 30, 8, 0, 0)

            # Insert first weight
            weight1 = BodyMetric(
                user_id=test_user.id,
                metric_type="weight",
                value=Decimal("100.0"),
                unit="kg",
                recorded_at=recorded_time,
                source="test",
            )
            db.add(weight1)
            db.commit()

        # Try to insert duplicate (same user, type, recorded_at)
        with get_db_context() as db:
            weight2 = BodyMetric(
                user_id=test_user.id,
                metric_type="weight",
                value=Decimal("101.0"),
                unit="kg",
                recorded_at=recorded_time,
                source="test",
            )
            db.add(weight2)

            # Should raise integrity error
            with pytest.raises(IntegrityError):
                db.commit()

            # Rollback the failed transaction
            db.rollback()

    def test_unique_constraint_prevents_duplicate_activity_metrics(self, test_user):
        """Test that unique constraint prevents duplicate activity entries."""
        with get_db_context() as db:
            metric_date = date(2025, 12, 30)

            # Insert first activity metric
            metric1 = ActivityMetric(
                user_id=test_user.id,
                metric_type="steps",
                value=Decimal("10000"),
                unit="count",
                date=metric_date,
                recorded_at=datetime.combine(metric_date, datetime.min.time()),
                source="test",
            )
            db.add(metric1)
            db.commit()

        # Try to insert duplicate (same user, type, date)
        with get_db_context() as db:
            metric2 = ActivityMetric(
                user_id=test_user.id,
                metric_type="steps",
                value=Decimal("5000"),
                unit="count",
                date=metric_date,
                recorded_at=datetime.combine(metric_date, datetime.min.time()),
                source="test",
            )
            db.add(metric2)

            # Should raise integrity error
            with pytest.raises(IntegrityError):
                db.commit()

            # Rollback the failed transaction
            db.rollback()

    def test_cascade_delete_removes_body_metrics(self, test_user):
        """Test that deleting user cascades to body metrics."""
        user_id = test_user.id

        # Add body metric
        with get_db_context() as db:
            db.add(
                BodyMetric(
                    user_id=user_id,
                    metric_type="weight",
                    value=Decimal("100.0"),
                    unit="kg",
                    recorded_at=datetime(2025, 12, 30, 8, 0, 0),
                    source="test",
                )
            )
            db.commit()

        # Delete user
        with get_db_context() as db:
            db.query(User).filter(User.id == user_id).delete()
            db.commit()

        # Metrics should be gone too
        with get_db_context() as db:
            metrics = db.query(BodyMetric).filter(BodyMetric.user_id == user_id).all()
            assert len(metrics) == 0

    def test_cascade_delete_removes_activity_metrics(self, test_user):
        """Test that deleting user cascades to activity metrics."""
        user_id = test_user.id

        # Add activity metrics
        with get_db_context() as db:
            db.add(
                ActivityMetric(
                    user_id=user_id,
                    metric_type="steps",
                    value=Decimal("10000"),
                    unit="count",
                    date=date(2025, 12, 30),
                    recorded_at=datetime(2025, 12, 30, 0, 0, 0),
                    source="test",
                )
            )
            db.commit()

        # Delete user
        with get_db_context() as db:
            db.query(User).filter(User.id == user_id).delete()
            db.commit()

        # Metrics should be gone too
        with get_db_context() as db:
            metrics = (
                db.query(ActivityMetric).filter(ActivityMetric.user_id == user_id).all()
            )
            assert len(metrics) == 0

    def test_multiple_metrics_same_day_different_types(self, test_user):
        """Test storing different metric types for same day."""
        with get_db_context() as db:
            metric_date = date(2025, 12, 30)

            # Add steps
            db.add(
                ActivityMetric(
                    user_id=test_user.id,
                    metric_type="steps",
                    value=Decimal("10000"),
                    unit="count",
                    date=metric_date,
                    recorded_at=datetime.combine(metric_date, datetime.min.time()),
                    source="test",
                )
            )

            # Add energy
            db.add(
                ActivityMetric(
                    user_id=test_user.id,
                    metric_type="active_energy",
                    value=Decimal("500"),
                    unit="kcal",
                    date=metric_date,
                    recorded_at=datetime.combine(metric_date, datetime.min.time()),
                    source="test",
                )
            )

            db.commit()

            # Query all metrics for that day
            metrics = (
                db.query(ActivityMetric)
                .filter(
                    ActivityMetric.user_id == test_user.id,
                    ActivityMetric.date == metric_date,
                )
                .all()
            )

            assert len(metrics) == 2
            metric_types = {m.metric_type for m in metrics}
            assert metric_types == {"steps", "active_energy"}

    def test_query_metrics_by_date_range(self, test_user):
        """Test querying metrics within a date range."""
        with get_db_context() as db:
            # Add metrics for multiple days
            for day in [28, 29, 30]:
                db.add(
                    ActivityMetric(
                        user_id=test_user.id,
                        metric_type="steps",
                        value=Decimal(str(day * 1000)),
                        unit="count",
                        date=date(2025, 12, day),
                        recorded_at=datetime(2025, 12, day, 0, 0, 0),
                        source="test",
                    )
                )
            db.commit()

            # Query range (29-30)
            results = (
                db.query(ActivityMetric)
                .filter(
                    ActivityMetric.user_id == test_user.id,
                    ActivityMetric.date >= date(2025, 12, 29),
                    ActivityMetric.date <= date(2025, 12, 30),
                )
                .order_by(ActivityMetric.date)
                .all()
            )

            assert len(results) == 2
            assert results[0].value == Decimal("29000")
            assert results[1].value == Decimal("30000")

    def test_decimal_precision_in_database(self, test_user):
        """Test that decimal precision is maintained in database."""
        with get_db_context() as db:
            # Store value with 3 decimal places
            weight = BodyMetric(
                user_id=test_user.id,
                metric_type="weight",
                value=Decimal("114.567"),
                unit="kg",
                recorded_at=datetime(2025, 12, 30, 8, 0, 0),
                source="test",
            )
            db.add(weight)
            db.commit()

        # Query back and verify precision
        with get_db_context() as db:
            result = (
                db.query(BodyMetric)
                .filter(
                    BodyMetric.user_id == test_user.id,
                    BodyMetric.metric_type == "weight",
                )
                .first()
            )

            assert result is not None
            assert result.value == Decimal("114.567")
            # Verify it's stored as Decimal, not float
            assert isinstance(result.value, Decimal)
