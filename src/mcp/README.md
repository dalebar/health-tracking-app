# Health Tracking MCP Server

MCP (Model Context Protocol) server that enables Claude to query your health data through natural language.

## Prerequisites

1. **FastAPI server running:**
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **FastMCP installed:**
   ```bash
   uv pip install fastmcp
   ```

3. **Claude Desktop app installed:**
   - Download from: https://claude.ai/download

## Installation

### Step 1: Configure Claude Desktop

**macOS:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`

**Add this configuration:**
```json
{
  "mcpServers": {
    "health-tracking": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.server"
      ],
      "cwd": "/Users/daleb/Documents/projects/health-tracking-app",
      "env": {
        "HEALTH_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Important:** Replace `/Users/daleb/Documents/projects/health-tracking-app` with your actual project path.

### Step 2: Restart Claude Desktop

After saving the config, completely quit and restart Claude Desktop app.

### Step 3: Verify Connection

In Claude Desktop, you should see a small 🔌 icon or tools indicator showing the MCP server is connected.

## Usage Examples

Once configured, you can ask Claude natural language questions:

### Weight Tracking
- "What's my current weight?"
- "Show me my weight progress over the last 30 days"
- "Am I on track to hit my goal?"
- "What's my weight loss rate?"

### Activity & Energy
- "What was my TDEE yesterday?"
- "Show me my activity summary for the last week"
- "How many calories did I burn on Friday?"

### Workouts
- "How many boxing sessions did I do this month?"
- "Show me my workout stats for January"
- "Compare my training intensity pre and post injury"
- "What was my average heart rate during boxing last week?"

### Analysis
- "Give me a weekly summary"
- "How's my progress toward 100kg?"
- "Compare my last 30 days to the previous 30 days"

## Available Tools

The MCP server provides these tools to Claude:

**Body Metrics:**
- `get_latest_weight()` - Most recent weight
- `get_weight_history()` - Weight measurements over time
- `get_weight_trend()` - Trend analysis with averages

**Activity:**
- `get_daily_activity()` - Complete breakdown for a date
- `get_activity_summary()` - Summary over date range
- `get_recent_tdee()` - Daily energy expenditure

**Workouts:**
- `get_workouts()` - Workout history with filters
- `get_workout_by_id()` - Specific workout details
- `get_workout_stats()` - Aggregated statistics by type
- `get_boxing_workouts()` - Boxing-specific analysis

**Analysis:**
- `get_weekly_summary()` - Complete week overview
- `get_progress_to_goal()` - Goal tracking
- `compare_training_periods()` - Period comparison

## Troubleshooting

### "MCP server not connected"
1. Verify FastAPI is running at http://localhost:8000
2. Check Claude Desktop config file syntax (valid JSON)
3. Restart Claude Desktop completely
4. Check project path in config is correct

### "Tool execution failed"
1. Ensure FastAPI server is running
2. Check API logs for errors
3. Verify database is accessible

### "No data returned"
1. Check date ranges (data might not exist for that period)
2. Verify imports completed successfully
3. Query API directly to confirm data exists

## Development

### Running MCP Server Standalone

For testing without Claude Desktop:
```bash
python -m src.mcp.server
```

### Adding New Tools

1. Add tool function to `server.py` with `@mcp.tool()` decorator
2. Include clear docstring (Claude uses this)
3. Add type hints for parameters
4. Test with FastAPI endpoint first
5. Restart Claude Desktop to pick up changes

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Notes

- MCP server runs locally (no cloud)
- Only accessible from Claude Desktop on your machine
- Uses same API as Streamlit dashboard
- No authentication needed (local-only access)
