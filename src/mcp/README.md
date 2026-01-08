# Health Tracking MCP Server

MCP (Model Context Protocol) server that enables Claude Desktop to query your health data through natural language.

## Prerequisites

1. **Database with imported data** (run imports first)

2. **FastMCP installed:**
   ```bash
   pip install fastmcp
   ```

3. **Claude Desktop app:**
   Download from https://claude.ai/download

## Installation

### Step 1: Configure Claude Desktop

**macOS:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`

Add this configuration:

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

**Important:** Replace `/path/to/health-tracking-app` with your actual project path. Find it with `pwd` from the project root.

### Step 2: Restart Claude Desktop

After saving the config, completely quit (Cmd+Q) and restart Claude Desktop.

### Step 3: Verify Connection

In Claude Desktop, you should see a tools indicator (hammer icon or similar) showing the MCP server is connected.

## Usage Examples

Once configured, ask Claude natural language questions:

### Weight Tracking
- "What's my current weight?"
- "Show me my weight trend for the last 30 days"
- "Am I on track to hit my goal?"

### Activity & Energy
- "What was my TDEE yesterday?"
- "Show me my activity summary for the last week"
- "How many steps did I take on Friday?"

### Workouts
- "How many boxing sessions did I do this month?"
- "Show me my workout stats for January"
- "What was my average heart rate during workouts last week?"
- "Compare my training this month vs last month"

### Sleep
- "How did I sleep last night?"
- "What's my average sleep duration this week?"

### Nutrition
- "What did I eat yesterday?"
- "Am I in a calorie deficit today?"
- "Show me my nutrition summary for the week"
- "What's my calorie goal for today?"
- "How much protein did I have this week?"

### Analysis
- "Give me a weekly summary"
- "How's my overall progress?"

## Available Tools (21 total)

### Weight (3 tools)
| Tool | Description |
|------|-------------|
| `get_latest_weight()` | Most recent weight measurement |
| `get_weight_history(days, limit)` | Weight measurements over time |
| `get_weight_trend(days)` | Trend analysis with averages and change rate |

### Activity (3 tools)
| Tool | Description |
|------|-------------|
| `get_daily_activity(date)` | Complete breakdown for a specific date |
| `get_activity_summary(days)` | Summary over date range |
| `get_recent_tdee(days)` | Daily energy expenditure breakdown |

### Workouts (4 tools)
| Tool | Description |
|------|-------------|
| `get_workouts(workout_type, days, limit)` | Workout history with filters |
| `get_workout_by_id(id)` | Specific workout details |
| `get_workout_stats(days)` | Aggregated statistics by type |
| `get_boxing_workouts(days, limit)` | Boxing-specific analysis |

### Sleep (2 tools)
| Tool | Description |
|------|-------------|
| `get_recent_sleep(days)` | Recent sleep sessions |
| `get_sleep_stats(days)` | Sleep statistics and averages |

### Nutrition (7 tools)
| Tool | Description |
|------|-------------|
| `get_daily_nutrition(date)` | Daily calorie/macro summary |
| `get_meals_for_date(date)` | Individual meals for a date |
| `get_nutrition_summary(days)` | Summary over date range |
| `get_nutrition_goals()` | All weekly calorie goals |
| `get_todays_nutrition_goal()` | Today's specific goal |
| `get_nutrition_trends(days)` | Calorie trends over time |
| `get_calorie_deficit(days)` | Deficit/surplus analysis |

### Analysis (2 tools)
| Tool | Description |
|------|-------------|
| `get_weekly_summary()` | Complete week overview |
| `get_progress_to_goal()` | Goal tracking progress |
| `compare_training_periods(period1, period2, gap)` | Period comparison |

## Troubleshooting

### "MCP server not connected"

1. Check Claude Desktop config file syntax (valid JSON)
2. Verify project path in `cwd` is correct
3. Restart Claude Desktop completely (Cmd+Q, not just close window)
4. Try running manually to check for errors:
   ```bash
   cd /path/to/health-tracking-app
   python -m src.mcp.server
   ```

### "Tool execution failed"

1. Check database connection in `.env`
2. Verify data exists for the queried date range
3. Check logs for specific error messages

### "No data returned"

1. Confirm imports completed successfully
2. Check date ranges (data might not exist for that period)
3. Query database directly to confirm data exists

## Development

### Running MCP Server Standalone

For testing without Claude Desktop:
```bash
python -m src.mcp.server
```

### Adding New Tools

1. Add function to `server.py` with `@mcp.tool()` decorator
2. Include clear docstring (Claude uses this for context)
3. Add type hints for all parameters
4. Restart Claude Desktop to pick up changes

Example:
```python
@mcp.tool()
def get_my_metric(days: int = 7) -> dict:
    """
    Get my custom metric for the specified number of days.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        dict: Metric data with values and dates
    """
    # Implementation here
    pass
```

### Debugging

Check MCP server logs in Claude Desktop's developer tools, or run standalone with verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Notes

- MCP server runs locally only
- No authentication required (local-only access)
- Data never leaves your machine
- Uses direct database queries (no external API calls)
