# Architecture Documentation

## Data Flow

```
Apple Health Export (XML)
    ↓
Apple Health Parser (memory-efficient iterparse)
    ↓
SQLAlchemy ORM Models
    ↓
PostgreSQL Database (Neon)
    ↓
[Future] FastAPI REST API
    ↓
[Future] Streamlit Dashboard / Claude MCP
```

## Parser Design

### Memory Efficiency

Uses `ET.iterparse()` to process 1.65GB XML file without loading entire file into memory.

### Aggregation Strategies

- **Steps/Energy/Exercise**: Sum by date
- **Heart Rate**: Average by date (resting, walking), Maximum by date (HRV)
- **Sleep**: 2-hour gap detection groups records into sessions
- **Workouts**: Individual sessions (no aggregation), duplicates handled by start_time uniqueness

### Type Safety

All parsers return TypedDict objects:
- `MetricResult` - Daily aggregated metrics
- `WeightRecord` - Timestamp-based measurements
- `VO2MaxRecord` - Fitness measurements
- `SleepSessionRecord` - Complete sleep sessions
- `WorkoutRecord` - Individual workout sessions with metrics

## Database Design

### Normalization

- 3NF (Third Normal Form)
- Separate tables by metric category
- Foreign key relationships with cascade deletes

### Constraints

- **Unique**: Prevent duplicate imports
- **Check**: Validate data (e.g., sleep end_time > start_time)
- **Foreign Key**: Maintain referential integrity

### Indexes

Created on frequently queried columns:
- `(user_id, metric_type, date)` for activity/HR metrics
- `(user_id, recorded_at)` for body metrics
- `(user_id, start_time)` for sleep sessions
- `(user_id, workout_type, start_time)` for workouts

### Database Tables

#### workouts
Stores individual workout sessions with comprehensive performance metrics.

**Key Fields:**
- `workout_type`: Type of activity (Boxing, Running, Walking, Cycling, etc.)
- `start_time`, `end_time`: Workout timing with timezone
- `duration_minutes`: Total workout duration
- `active_energy_kcal`, `basal_energy_kcal`, `total_energy_kcal`: Energy expenditure breakdown
- `distance_km`: Distance covered (for cardio activities)
- `avg_heart_rate_bpm`, `min_heart_rate_bpm`, `max_heart_rate_bpm`: Heart rate metrics during workout
- `indoor_workout`: Boolean flag for indoor/outdoor classification
- `source`: Data source (e.g., "Apple Watch", "Strava")

**Constraints:**
- Unique constraint on `user_id` + `start_time` (prevents duplicate workouts)
- Check constraint ensuring `end_time > start_time`
- Index on `(user_id, workout_type, start_time)` for efficient queries

**Notes:**
- Duplicate workouts (same start_time) are deduplicated during import, keeping the record with most complete data
- Heart rate zones are calculated on-demand from aggregate HR metrics, not stored

## Import Strategy

### Idempotency

All import scripts check for existing records before inserting.
Safe to re-run without creating duplicates.

### Batch Commits

Commit every 100 records to balance transaction overhead with memory usage.

### Error Handling

- Skip malformed XML records
- Continue processing on individual record failures
- Clear XML elements after processing to free memory
