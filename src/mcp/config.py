"""
MCP Server configuration.
"""

import os

# API Configuration
API_BASE_URL = os.getenv("HEALTH_API_URL", "http://localhost:8000")
API_TIMEOUT = 30  # seconds

# MCP Server Configuration
MCP_SERVER_NAME = "Health Tracking"
MCP_SERVER_VERSION = "0.1.0"

# Tool Configuration
DEFAULT_DAYS_LOOKBACK = 7
DEFAULT_WORKOUT_LIMIT = 50
MAX_WORKOUT_LIMIT = 500

# Goal Configuration
GOAL_WEIGHT_KG = 100.0
GOAL_DATE = "2026-04-30"
STARTING_WEIGHT_KG = 114.5
STARTING_DATE = "2026-01-03"
