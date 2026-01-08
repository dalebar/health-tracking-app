# Claude Desktop MCP Setup

## Step 1: Locate Config File

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/
```
Then edit `claude_desktop_config.json`

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

## Step 2: Get Your Project Path

```bash
# From project root
pwd
```

Copy this path - you'll need it for the config.

## Step 3: Edit Config File

If the file doesn't exist, create it. Add this content:

```json
{
  "mcpServers": {
    "health-tracking": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "PASTE_YOUR_PROJECT_PATH_HERE"
    }
  }
}
```

**Replace `PASTE_YOUR_PROJECT_PATH_HERE` with your actual path!**

**Example:**
```json
"cwd": "/Users/yourname/projects/health-tracking-app"
```

## Step 4: Verify JSON Syntax

Use a JSON validator to ensure no syntax errors:
https://jsonlint.com/

## Step 5: Restart Claude Desktop

**macOS:**
1. Cmd+Q to quit Claude Desktop completely
2. Reopen from Applications

**Windows:**
1. Right-click system tray icon → Quit
2. Reopen from Start Menu

## Step 6: Verify Connection

In a new conversation in Claude Desktop, look for:
- Small hammer/tools icon near the text input
- Or "Tools" indicator in the sidebar

## Step 7: Test with Query

Try asking:
- "What's my current weight?"
- "Show my workout stats for the last week"
- "Am I in a calorie deficit today?"

Claude should respond with your actual data!

## Troubleshooting

### Server Not Connecting

**Check project path:**
Make sure the `cwd` in your config points to the project root (where `src/` folder is).

**Check Python path:**
Try running manually:
```bash
cd /your/project/path
python -m src.mcp.server
```

**Check database connection:**
The MCP server connects directly to your database. Verify `.env` has correct `DATABASE_URL`.

### Tools Not Appearing

1. Completely quit Claude Desktop (Cmd+Q / Quit from tray)
2. Wait 5 seconds
3. Reopen
4. Start new conversation

### Permission Errors

Make sure your Python environment has all dependencies:
```bash
pip install fastmcp
```

### "No data" Responses

1. Verify imports completed successfully
2. Check the date range you're asking about has data
3. Try a known query like "What's my latest weight?"
