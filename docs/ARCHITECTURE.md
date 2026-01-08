# Architecture Documentation

## Data Flow

```
Data Sources
├── Apple Health Export (XML)
└── MyFitnessPal Export (CSV)
         ↓
    Folder Watcher (watchdog)
         ↓
    Import Orchestrator
         ↓
    Parsers (XML iterparse / CSV reader)
         ↓
    SQLAlchemy ORM Models
         ↓
    PostgreSQL Database (Neon)
         ↓
    ┌────────────────────────────┐
    │      FastAPI REST API      │
    └────────────────────────────┘
         ↓              ↓
    Claude MCP     Dashboards
```

## Parser Design

### Memory Efficiency

Uses `ET.iterparse()` to process large XML files (~1-2GB) without loading the entire file into memory. Elements are cleared after processing to prevent memory buildup.

### Aggregation Strategies

| Data Type | Strategy | Notes |
|-----------|----------|-------|
| Steps/Energy/Exercise | Sum by date | Multiple records per day aggregated |
| Heart Rate (resting/walking) | Average by date | Daily average calculated |
| HRV | Maximum by date | Peak HRV retained |
| Sleep | 2-hour gap detection | Groups records into sessions |
| Workouts | Individual sessions | Deduplicated by start_time |
| Nutrition | Per-meal + daily summary | MFP CSV parsed directly |

### Type Safety

All parsers return TypedDict objects:
- `MetricResult` - Daily aggregated metrics
- `WeightRecord` - Timestamp-based measurements
- `VO2MaxRecord` - Fitness measurements
- `SleepSessionRecord` - Complete sleep sessions with stage breakdown
- `WorkoutRecord` - Individual workout sessions with metrics
- `NutritionRecord` - Individual meals/foods

## Database Design

### Schema Overview

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │ 1:N
       ├──────────────────────────────────────────────────┐
       │         │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  body_   │ │ activity │ │ heart_   │ │  sleep   │ │ workouts │
│ metrics  │ │ metrics  │ │   rate   │ │ sessions │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
       │
       ├──────────────────────────────────────────────────┐
       │         │         │                              │
       ▼         ▼         ▼                              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐            ┌──────────┐
│  cardio  │ │nutrition │ │  daily   │            │nutrition │
│ fitness  │ │  logs    │ │nutrition │            │  goals   │
└──────────┘ └──────────┘ │ summary  │            └──────────┘
                          └──────────┘
```

### Tables (10 total)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User profiles | name, email, height, target_weight |
| `body_metrics` | Weight, BMI, body fat | metric_type, value, recorded_at |
| `activity_metrics` | Steps, energy, exercise | metric_type, value, date |
| `heart_rate_metrics` | Resting HR, walking HR, HRV | metric_type, value, date |
| `cardio_fitness` | VO2 max measurements | vo2_max, recorded_at |
| `sleep_sessions` | Sleep with stage breakdown | start_time, deep/rem/core_minutes |
| `workouts` | Workout sessions | workout_type, duration, energy, HR |
| `nutrition_logs` | Individual meals/foods | meal_type, food_name, calories, macros |
| `daily_nutrition_summary` | Daily calorie/macro totals | date, total_calories, protein/carbs/fat |
| `nutrition_goals` | Target calories by day | day_of_week, target_calories |

### Normalization

- Third Normal Form (3NF)
- Separate tables by metric category
- Foreign key relationships with cascade deletes

### Constraints

- **Unique**: Prevent duplicate imports (e.g., `user_id + date + metric_type`)
- **Check**: Validate data (e.g., `end_time > start_time` for sleep)
- **Foreign Key**: Maintain referential integrity with ON DELETE CASCADE

### Indexes

Optimized for common query patterns:
- `(user_id, metric_type, date)` for activity/HR metrics
- `(user_id, recorded_at)` for body metrics
- `(user_id, start_time)` for sleep sessions
- `(user_id, workout_type, start_time)` for workouts
- `(user_id, date)` for nutrition summaries

## Import System

### Auto-Import Architecture

```
~/Documents/health/
        │
        │  (file dropped)
        ▼
┌─────────────────────┐
│   Folder Watcher    │  (watchdog + launchd)
│  watch_health_      │
│  exports.py         │
└─────────┬───────────┘
          │
          │  detects: export.zip OR File-Export-*.zip
          ▼
┌─────────────────────┐
│     Orchestrator    │
│  orchestrate_       │
│  import.py          │
└─────────┬───────────┘
          │
          ├── Apple Health: unified XML parsing (single pass)
          │   └── Weight, Steps, Activity, HR, VO2, Sleep, Workouts
          │
          └── MyFitnessPal: CSV parsing
              └── Nutrition logs + daily summaries
          │
          ▼
┌─────────────────────┐
│  macOS Notification │
│  notification_      │
│  helper.py          │
└─────────────────────┘
```

### Import Idempotency

All imports are safe to re-run:
1. Unique constraints prevent duplicate records
2. Each import checks for existing records before inserting
3. Conflicts handled with `ON CONFLICT DO NOTHING` or `DO UPDATE`

### Batch Processing

- Bulk duplicate checking (batch queries vs N+1)
- Bulk inserts with `insert().values([...])`
- Commit every 50-100 records to balance transactions vs memory

### Error Handling

- Skip malformed XML/CSV records
- Continue processing on individual record failures
- Clear XML elements after processing to free memory
- Log errors to `logs/import_history.log`

## API Design

### REST Endpoints

```
/weight
├── GET /latest          → Most recent weight
├── GET /history         → Weight measurements
└── GET /trend           → Trend analysis

/activity
├── GET /daily/{date}    → Complete breakdown
├── GET /summary         → Period summary
└── GET /tdee            → Daily energy expenditure

/workouts
├── GET /                → List workouts
├── GET /{id}            → Single workout
├── GET /stats           → Aggregated stats
└── GET /boxing          → Boxing-specific

/sleep
├── GET /recent          → Recent sessions
└── GET /stats           → Sleep statistics

/nutrition
├── GET /daily/{date}    → Daily summary
├── GET /meals/{date}    → Individual meals
├── GET /summary         → Period summary
├── GET /goals           → All goals
├── GET /goals/today     → Today's goal
├── GET /trends          → Calorie trends
└── GET /deficit         → Deficit analysis
```

### MCP Integration

The MCP server wraps API endpoints for Claude Desktop:
- 21 tools available (weight, activity, workouts, sleep, nutrition)
- Direct database queries for performance
- Natural language interface via Claude

## Project Structure

```
health-tracking-app/
├── src/
│   ├── api/                 # FastAPI application
│   │   ├── routes/          # Endpoint handlers by domain
│   │   └── schemas/         # Pydantic request/response models
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── session.py       # Database connection management
│   ├── importers/           # All import scripts
│   │   ├── orchestrate_import.py
│   │   ├── import_*.py      # Individual metric importers
│   │   └── myfitnesspal_importer.py
│   ├── mcp/                 # Claude Desktop integration
│   │   └── server.py        # FastMCP server with tools
│   ├── parsers/
│   │   └── apple_health_parser.py
│   ├── utils/
│   │   └── import_helpers.py
│   └── watcher/             # Folder monitoring
│       ├── watch_health_exports.py
│       └── notification_helper.py
├── migrations/              # Alembic database migrations
├── tests/                   # pytest test suite
├── scripts/                 # CLI entry points
│   └── run_import.py        # Manual import CLI
└── logs/                    # Runtime logs
```
