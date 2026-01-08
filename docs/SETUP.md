# Detailed Setup Guide

## Prerequisites

- Python 3.13+
- PostgreSQL database (local or [Neon](https://neon.tech))
- iPhone with Apple Health
- Apple Watch Series 7+ (optional, for workout/HR data)
- MyFitnessPal account (optional, for nutrition tracking)

## 1. Clone and Install

```bash
git clone https://github.com/yourusername/health-tracking-app.git
cd health-tracking-app

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
pre-commit install
```

## 2. Database Setup

### Option A: Neon (Recommended)

1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Copy connection string from dashboard

### Option B: Local PostgreSQL

```bash
createdb health_tracking
```

### Configure Environment

Create `.env` file in project root:

```bash
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
ENVIRONMENT=development
```

For local PostgreSQL, omit `?sslmode=require`.

### Run Migrations

```bash
alembic upgrade head
python -m src.importers.insert_initial_data
```

## 3. Export Your Health Data

### Apple Health

1. Open the **Health** app on your iPhone
2. Tap your profile picture (top right)
3. Scroll down and tap **Export All Health Data**
4. Wait 5-10 minutes for export to generate
5. AirDrop or share `export.zip` to your Mac
6. Place in `~/Documents/health/`

The export contains `export.xml` which can be 1-2GB depending on your data history.

### MyFitnessPal

1. Log into [MyFitnessPal](https://www.myfitnesspal.com) on the web
2. Go to **Settings** (gear icon) → **Export Data**
3. Select date range and click **Export**
4. Download the ZIP file (named like `File-Export-2026-01-01-to-2026-01-08.zip`)
5. Place in `~/Documents/health/`

## 4. Import Data

### Option A: Automatic Import (Recommended)

Install the folder watcher as a background service:

```bash
./scripts/install_watcher.sh
```

This creates a launchd service that:
- Monitors `~/Documents/health/` for new files
- Automatically imports `export.zip` (Apple Health)
- Automatically imports `File-Export-*.zip` (MyFitnessPal)
- Sends macOS notification when complete

Just drop files in the folder and imports happen automatically.

### Option B: Manual Import

**Apple Health:**
```bash
python scripts/run_import.py ~/Documents/health/export.zip
```

**MyFitnessPal:**
```bash
python -m src.importers.myfitnesspal_importer ~/Documents/health/File-Export-*.zip
```

## 5. Start the API (Optional)

```bash
uvicorn src.api.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs

## 6. Configure Claude Desktop (Optional)

See [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md) for MCP integration.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment | `development` |
| `API_HOST` | API bind address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `HEALTH_API_URL` | API URL for MCP server | `http://localhost:8000` |

## Troubleshooting

### Import Fails with "File Not Found"

Make sure the export file exists:
```bash
ls -la ~/Documents/health/
```

### Database Connection Errors

1. Verify `DATABASE_URL` in `.env`
2. Check Neon dashboard for connection string
3. Ensure `?sslmode=require` for cloud databases

### Migration Conflicts

Reset to clean state:
```bash
alembic downgrade base
alembic upgrade head
```

### Watcher Not Detecting Files

1. Check watcher is running:
   ```bash
   launchctl list | grep health-import-watcher
   ```

2. View watcher logs:
   ```bash
   tail -f logs/watcher_stdout.log
   ```

3. Restart watcher:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist
   launchctl load ~/Library/LaunchAgents/com.daleb.health-import-watcher.plist
   ```

### No macOS Notifications

Grant notification permissions to Terminal/Python in System Settings → Notifications.

Test manually:
```bash
python -m src.watcher.notification_helper
```

### MCP Server Not Connecting

1. Verify FastAPI is running at http://localhost:8000
2. Check Claude Desktop config file syntax (valid JSON)
3. Restart Claude Desktop completely (Cmd+Q)
4. Check project path in config is correct
