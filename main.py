"""
Health Tracking App

Main entry point for the application.
"""


def main():
    """Display application information."""
    print("=" * 60)
    print("Health Tracking App - v0.1.0")
    print("=" * 60)
    print()
    print("Available commands:")
    print("  - Import data: See scripts/import_*.py")
    print("  - Run tests: pytest")
    print("  - Migrations: alembic upgrade head")
    print()
    print("For full documentation, see README.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
