# Health Tracking App

A health data pipeline that imports Apple Health metrics into PostgreSQL for analysis and visualization.

## Features

- **Comprehensive Data Import**: Weight, steps, activity, heart rate (resting, walking, HRV), VO2 max, sleep sessions, workouts
- **Type-Safe Parsing**: Full TypedDict usage with memory-efficient XML parsing
- **Database Migrations**: Alembic-managed schema with proper constraints
- **Test Coverage**: Integration and unit tests with real data validation
- **Professional Tooling**: Pre-commit hooks, linting, type checking, security scanning

### Current Metrics Supported

**Activity Metrics:**
- Daily steps
- Active energy (exercise calories)
- Resting energy (basal metabolic rate)
- Exercise minutes

**Heart Metrics:**
- Resting heart rate
- Walking/running heart rate
- Heart rate variability (HRV)

**Body Metrics:**
- Weight
- VO2 Max

**Sleep:**
- Sleep sessions (using 2-hour gap detection)

**Workouts:**
- Workout sessions with type, duration, and energy
- Heart rate data (average, min, max)
- Distance tracking for cardio activities
- Indoor/outdoor classification
- Supported types: Boxing, Running, Walking, Cycling, and more

## Data Volume

| Metric | Records | Aggregation |
|--------|---------|-------------|
| Weight | 18 | Individual measurements |
| Steps | 1,255 days | Daily totals |
| Active Energy | 1.1M+ records | Daily totals |
| Resting Energy | 1.1M+ records | Daily totals |
| Exercise Minutes | 60K+ records | Daily totals |
| Resting Heart Rate | 990 | Daily averages |
| Walking Heart Rate | 926 | Daily averages |
| HRV | 8,244 records | Daily maximum |
| VO2 Max | 221 | Individual measurements |
| Sleep Sessions | 1,233 | Multi-stage sessions |
| Workouts | 658 | Individual workout sessions |

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

**7 Tables:**
- `users` - User profiles
- `body_metrics` - Weight, BMI, body fat %
- `activity_metrics` - Steps, energy (active & resting), exercise (daily aggregates)
- `heart_rate_metrics` - Resting HR, walking HR, HRV (daily aggregates)
- `cardio_fitness` - VO2 max measurements
- `sleep_sessions` - Complete sleep sessions with stage breakdowns
- `workouts` - Individual workout sessions with metrics and heart rate data

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
python scripts/import_workouts.py
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

## MCP Integration (Phase 4)

The Health Tracking app includes an MCP (Model Context Protocol) server that enables Claude to query your health data through natural language in the Claude Desktop app.

### Quick Start

1. **Start the API:**
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Configure Claude Desktop:**

   Edit config file:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   Add:
   ```json
   {
     "mcpServers": {
       "health-tracking": {
         "command": "python",
         "args": ["-m", "src.mcp.server"],
         "cwd": "/path/to/health-tracking-app"
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Ask Claude questions:**
   - "What's my current weight?"
   - "Show me my boxing stats for January"
   - "Am I on track to hit my goal?"

See `src/mcp/README.md` for complete documentation.

## Auto-Import System (Phase 5A)

The Health Tracking app includes an automated import system that watches for Apple Health exports and automatically processes them when detected.

### Quick Start

**Option 1: Automatic Watcher (Recommended)**

1. **Install the watcher service:**
   ```bash
   ./scripts/install_watcher.sh
   ```

2. **Export from Apple Health:**
   - Open Health app on iPhone/iPad
   - Tap your profile → Export All Health Data
   - Save and AirDrop/share `export.zip` to Mac

3. **Drop the file:**
   - Move `export.zip` to `/Users/daleb/Documents/health/`
   - Auto-import will start within 30 seconds
   - You'll receive a macOS notification when complete

**Option 2: Manual Import**

```bash
python scripts/run_import.py ~/Documents/health/export.zip
```

### Features

- ✅ **Automatic Detection** - Watches folder for new export.zip files
- ✅ **Smart Import** - Runs all 9 import scripts in sequence
- ✅ **Duplicate Prevention** - Skips records that already exist
- ✅ **macOS Notifications** - Success/failure alerts
- ✅ **Comprehensive Logging** - Full history in `logs/import_history.log`
- ✅ **Auto-Restart** - Watcher restarts if it crashes
- ✅ **Background Service** - Runs on login via LaunchAgent

### Management Commands

```bash
# Stop the watcher
launchctl unload ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist

# Start the watcher
launchctl load ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist

# Check status
launchctl list | grep health-import-watcher

# View logs
tail -f logs/import_history.log

# Uninstall
./scripts/uninstall_watcher.sh
```

### Architecture

- **Watcher** (`scripts/watch_health_exports.py`) - Monitors folder for files
- **Orchestrator** (`scripts/orchestrate_import.py`) - Coordinates all imports
- **Import Scripts** (9 total) - Parse and import specific metrics:
  - Weight history
  - Steps and activity metrics
  - Resting energy (BMR)
  - Heart rate metrics (resting, walking, HRV)
  - VO2 max (cardio fitness)
  - Sleep sessions
  - Workouts
- **Notifications** (`scripts/notification_helper.py`) - macOS alerts

### Troubleshooting

**Watcher not starting?**
- Check logs: `tail -f logs/watcher_stdout.log`
- Verify Python path in plist file
- Ensure watchdog is installed: `uv pip list | grep watchdog`

**Import failing?**
- Verify database connection in `.env`
- Check that FastAPI server is NOT required (imports work standalone)
- Review detailed logs in `logs/import_history.log`

**No notification appearing?**
- Grant Terminal/Python notification permissions in System Settings
- Test manually: `python scripts/notification_helper.py`

## Future Enhancements

- Automated data sync (iOS Shortcuts + Mac app)
- MyFitnessPal nutrition integration
- Predictive analytics and correlations
- Additional health metrics (blood pressure, glucose, etc.)

## License

MIT License - see LICENSE file

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Migrations
- [defusedxml](https://github.com/tiran/defusedxml) - Secure XML parsing
- [Neon](https://neon.tech/) - Serverless PostgreSQL
