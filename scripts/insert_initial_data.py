#!/usr/bin/env python3

from datetime import datetime, date
from decimal import Decimal

from src.db.models import User, BodyMetric
from src.db.session import get_db_context


def main():
    """Insert initial data and verify database operations."""

    print("=" * 60)
    print("Health Tracking App - Database Quick Win Test")
    print("=" * 60)
    print()

    with get_db_context() as db:
        # Step 1: Check if user already exists
        print("Step 1: Checking for existing user...")
        existing_user = db.query(User).filter(User.email == "dale@live.com").first()

        if existing_user:
            print(f"✅ User already exists: {existing_user}")
            user = existing_user
        else:
            # Create new user
            print("Creating new user record...")
            user = User(
                email="dale@example.com",
                name="Dale",
                height_cm=Decimal("185.00"),
                date_of_birth=date(
                    1986, 11, 5
                ),  # Update with your actual DOB if you want
            )
            db.add(user)
            db.commit()
            db.refresh(user)  # Reload to get the auto-generated ID
            print(f"✅ User created: {user}")

        print()

        # Step 2: Insert current weight measurement
        print("Step 2: Inserting weight measurement...")

        # Check if today's weight already exists
        today = datetime.now().date()
        existing_weight = (
            db.query(BodyMetric)
            .filter(
                BodyMetric.user_id == user.id,
                BodyMetric.metric_type == "weight",
                BodyMetric.recorded_at >= datetime.combine(today, datetime.min.time()),
                BodyMetric.recorded_at < datetime.combine(today, datetime.max.time()),
            )
            .first()
        )

        if existing_weight:
            print(f"✅ Today's weight already recorded: {existing_weight}")
            weight_metric = existing_weight
        else:
            weight_metric = BodyMetric(
                user_id=user.id,
                metric_type="weight",
                value=Decimal("114.0"),
                unit="kg",
                recorded_at=datetime.now(),
                source="manual_entry",
                notes="Initial data entry - starting weight for transformation journey",
            )
            db.add(weight_metric)
            db.commit()
            db.refresh(weight_metric)
            print(f"✅ Weight recorded: {weight_metric}")

        print()

        # Step 3: Query all weight measurements for this user
        print("Step 3: Querying all weight measurements...")
        all_weights = (
            db.query(BodyMetric)
            .filter(BodyMetric.user_id == user.id, BodyMetric.metric_type == "weight")
            .order_by(BodyMetric.recorded_at.desc())
            .all()
        )

        print(f"Found {len(all_weights)} weight measurement(s):")
        for weight in all_weights:
            print(
                f"  📊 {weight.recorded_at.strftime('%Y-%m-%d %H:%M')}: "
                f"{weight.value}{weight.unit} (source: {weight.source})"
            )

        print()

        # Step 4: Display user summary
        print("=" * 60)
        print("USER SUMMARY")
        print("=" * 60)
        print(f"Name:           {user.name}")
        print(f"Email:          {user.email}")
        print(f"Height:         {user.height_cm} cm")
        print(f"Current Weight: {weight_metric.value} {weight_metric.unit}")

        # Calculate BMI
        if user.height_cm and weight_metric.value:
            height_m = float(user.height_cm) / 100
            bmi = float(weight_metric.value) / (height_m**2)
            print(f"BMI:            {bmi:.1f}")

        print("Target Weight:  100 kg")
        print(f"Weight to Lose: {float(weight_metric.value) - 100:.1f} kg")
        print("=" * 60)
        print()

        print("✅ Database connectivity verified!")
        print("✅ SQLAlchemy models working!")
        print("✅ Data persisted to Neon!")
        print()
        print("Next step: Parse Apple Health XML export")


if __name__ == "__main__":
    main()
