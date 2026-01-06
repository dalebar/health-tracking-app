# Health Tracking App

A production-grade health data pipeline that imports Apple Health metrics into PostgreSQL for analysis and visualization.

## Features

- **Comprehensive Data Import**: Weight, steps, activity, heart rate (resting, walking, HRV), VO2 max, sleep sessions
- **Type-Safe Parsing**: Full TypedDict usage with memory-efficient XML parsing
- **Database Migrations**: Alembic-managed schema with proper constraints
- **Test Coverage**: Integration and unit tests with real data validation
- **Professional Tooling**: Pre-commit hooks, linting, type checking, security scanning

## Metrics Tracked

| Metric | Records | Aggregation |
|--------|---------|-------------|
| Weight | 18 | Individual measurements |
| Steps | 1,255 days | Daily totals |
| Active Energy | 1.1M+ records | Daily totals |
| Exercise Minutes | 60K+ records | Daily totals |
| Resting Heart Rate | 990 | Daily averages |
| Walking Heart Rate | 926 | Daily averages |
| HRV | 8,244 records | Daily maximum |
| VO2 Max | 221 | Individual measurements |
| Sleep Sessions | 1,233 | Multi-stage sessions |

## Architecture

```
health-tracking-app/
├── src/
│   ├── api/              # FastAPI endpoints (future)
│   ├── db/
│   │   ├── models.py     # SQLAlchemy ORM models
│   │   └── session.py    # Database connection management
│   ├── parsers/
│   │   └── apple_health_parser.py  # XML parsing logic
│   └── utils/
│       └── import_helpers.py       # Reusable import utilities
├── scripts/              # Data import scripts
├── tests/
│   ├── integration/      # Integration tests (database + parser)
│   └── unit/             # Unit tests
├── migrations/           # Alembic database migrations
└── .env                  # Environment configuration (gitignored)
```

### Database Schema

**6 Tables:**
- `users` - User profiles
- `body_metrics` - Weight, BMI, body fat %
- `activity_metrics` - Steps, energy, exercise (daily aggregates)
- `heart_rate_metrics` - Resting HR, walking HR, HRV (daily aggregates)
- `cardio_fitness` - VO2 max measurements
- `sleep_sessions` - Complete sleep sessions with stage breakdowns

**Key Design Decisions:**
- Flexible `metric_type` columns support multiple metrics without schema changes
- Unique constraints prevent duplicate imports
- Foreign key cascades ensure data integrity
- Decimal(10,3) precision maintains Apple Health accuracy

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL database (Neon recommended)
- Apple Health export file (Settings → Health → Profile → Export All Health Data)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd health-tracking-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Configuration

Create `.env` file:

```bash
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
ENVIRONMENT=development
```

### Database Setup

```bash
# Run migrations
alembic upgrade head

# Insert initial user data
python scripts/insert_initial_data.py
```

### Import Health Data

```bash
# Import all metrics (run in order)
python scripts/import_weight_history.py
python scripts/import_steps_history.py
python scripts/import_activity_metrics.py
python scripts/import_heart_rate_metrics.py
python scripts/import_vo2_max.py
python scripts/import_sleep_data.py
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit
```

## Development

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check . --fix

# Type check
mypy src/

# Security scan
bandit -c pyproject.toml -r src/
```

### Pre-commit Hooks

Automatically run on `git commit`:
- Ruff formatting and linting
- MyPy type checking
- Bandit security scanning
- Trailing whitespace removal
- YAML validation

## Future Enhancements

- FastAPI REST endpoints
- Streamlit visualization dashboard
- MCP server for Claude integration
- Automated data sync (iOS Shortcuts + Mac app)
- MyFitnessPal nutrition integration
- Predictive analytics and correlations

## License

MIT License - see LICENSE file

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Migrations
- [defusedxml](https://github.com/tiran/defusedxml) - Secure XML parsing
- [Neon](https://neon.tech/) - Serverless PostgreSQL
