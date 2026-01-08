# Health Tracking App

A personal health data pipeline that imports Apple Health and MyFitnessPal data into PostgreSQL, with a REST API, automated imports, and Claude Desktop integration via MCP.

## What This Does

Export your health data from your iPhone, drop the file into a folder, and it automatically imports everything into a database. You can then:

- Query your data through a REST API
- Ask Claude questions about your health trends (via MCP)
- Build dashboards and visualizations
- Run your own analysis with SQL

The system handles all the heavy lifting: parsing Apple's XML format, aggregating raw measurements into daily summaries, deduplicating records, and keeping everything in sync.

## Requirements

- **Mac or Linux** (tested on macOS Tahoe)
- **Python 3.13+**
- **PostgreSQL** (local or cloud - I use [Neon](https://neon.tech/))
- **iPhone with Apple Health** (for health metrics export)
- **Apple Watch Series 7+** (optional, for workout/heart rate data)
- **MyFitnessPal** (optional, for nutrition tracking)

## Supported Metrics

| Source | Data |
|--------|------|
| **Apple Health** | Weight, steps, active/resting energy, exercise minutes |
| **Apple Health** | Heart rate (resting, walking, HRV), VO2 max |
| **Apple Health** | Sleep sessions with stage breakdown |
| **Apple Health** | Workouts (type, duration, calories, distance, heart rate zones) |
| **MyFitnessPal** | Meals, calories, macros (protein/carbs/fat), daily summaries |

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/health-tracking-app.git
cd health-tracking-app

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
pre-commit install
```

### 2. Set Up the Database

Create a `.env` file:

```bash
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
ENVIRONMENT=development
```

Run migrations and seed initial data:

```bash
alembic upgrade head
python -m src.importers.insert_initial_data
```

### 3. Export Your Health Data

**Apple Health:**
1. Open the Health app on your iPhone
2. Tap your profile picture (top right)
3. Scroll down and tap "Export All Health Data"
4. Save and AirDrop `export.zip` to your Mac

**MyFitnessPal:**
1. Log into MyFitnessPal on the web
2. Go to Settings → Export Data
3. Download the ZIP file (named like `File-Export-2026-01-01-to-2026-01-08.zip`)

### 4. Import Your Data

**Option A: Automatic (Recommended)**

Install the folder watcher as a background service:

```bash
./scripts/install_watcher.sh
```

Now just drop files into `~/Documents/health/`:
- `export.zip` for Apple Health
- `File-Export-*.zip` for MyFitnessPal

The watcher detects new files, runs the import, and sends a macOS notification when done.

**Option B: Manual**

```bash
# Apple Health
python scripts/run_import.py ~/Downloads/export.zip

# MyFitnessPal
python -m src.importers.myfitnesspal_importer ~/Downloads/File-Export-*.zip
```

## Using the API

Start the server:

```bash
uvicorn src.api.main:app --reload --port 8000
```

Example endpoints:

```bash
# Weight trend over last 30 days
curl http://localhost:8000/weight/trend?days=30

# Today's workouts
curl http://localhost:8000/workouts?days=1

# Calorie deficit for the week
curl http://localhost:8000/nutrition/deficit?days=7

# Full API docs
open http://localhost:8000/docs
```

## Claude Desktop Integration (MCP)

The app includes an MCP server so you can ask Claude about your health data directly in Claude Desktop.

**Setup:**

1. Edit your Claude Desktop config:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add:
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

3. Restart Claude Desktop

**Example questions:**
- "What's my weight trend this month?"
- "How many boxing sessions did I do in December?"
- "Am I in a calorie deficit today?"
- "Compare my workouts this week vs last week"

## Project Structure

```
health-tracking-app/
├── src/
│   ├── api/                 # FastAPI routes and schemas
│   │   ├── routes/          # Endpoint handlers
│   │   └── schemas/         # Pydantic models
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── session.py       # Database connection
│   ├── importers/           # Data import scripts
│   │   ├── orchestrate_import.py    # Coordinates all imports
│   │   ├── import_weight_history.py
│   │   ├── import_steps_history.py
│   │   ├── import_activity_metrics.py
│   │   ├── import_heart_rate_metrics.py
│   │   ├── import_vo2_max.py
│   │   ├── import_sleep_data.py
│   │   ├── import_workouts.py
│   │   └── myfitnesspal_importer.py
│   ├── mcp/                 # Claude Desktop integration
│   ├── parsers/             # XML/CSV parsing logic
│   ├── utils/               # Shared utilities
│   └── watcher/             # Folder monitoring service
├── migrations/              # Alembic database migrations
├── tests/                   # pytest test suite
├── scripts/                 # CLI tools
└── logs/                    # Import history and watcher logs
```

## Database Schema

**10 tables:**

| Table | Purpose |
|-------|---------|
| `users` | User profiles |
| `body_metrics` | Weight measurements |
| `activity_metrics` | Steps, energy, exercise (daily aggregates) |
| `heart_rate_metrics` | Resting HR, walking HR, HRV |
| `cardio_fitness` | VO2 max |
| `sleep_sessions` | Sleep with stage breakdown |
| `workouts` | Workout sessions with metrics |
| `nutrition_logs` | Individual meals/foods |
| `daily_nutrition_summary` | Daily calorie/macro totals |
| `nutrition_goals` | Target calories by day of week |

All tables use unique constraints to prevent duplicate imports - you can re-run imports safely.

## Managing the Watcher

```bash
# View status
launchctl list | grep health-import-watcher

# Stop
launchctl unload ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist

# Start
launchctl load ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist

# View logs
tail -f logs/import_history.log

# Uninstall completely
./scripts/uninstall_watcher.sh
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
ruff check . --fix

# Format
ruff format .
```

Pre-commit hooks run automatically on `git commit` to catch issues early.

## Troubleshooting

**Import not working?**
- Check `logs/import_history.log` for detailed errors
- Verify your `.env` has the correct `DATABASE_URL`
- Make sure migrations ran: `alembic upgrade head`

**Watcher not detecting files?**
- Check `logs/watcher_stdout.log`
- Verify the watch folder exists: `mkdir -p ~/Documents/health`
- Restart: `launchctl unload ... && launchctl load ...`

**No macOS notifications?**
- Grant notification permissions to Terminal/Python in System Settings
- Test manually: `python -m src.watcher.notification_helper`

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** - REST API
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM
- **[Alembic](https://alembic.sqlalchemy.org/)** - Database migrations
- **[MCP](https://modelcontextprotocol.io/)** - Claude Desktop integration
- **[defusedxml](https://github.com/tiran/defusedxml)** - Secure XML parsing
- **[Watchdog](https://pythonhosted.org/watchdog/)** - File system monitoring
- **[Neon](https://neon.tech/)** - Serverless PostgreSQL

## License

MIT
