#!/usr/bin/env python3
"""
Test MCP tools by calling the FastAPI endpoints directly.
Useful for verifying the API works before integrating with Claude Desktop.
"""

import requests
from datetime import date, timedelta
from typing import Any


API_BASE_URL = "http://localhost:8000"


def _get(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Make GET request to FastAPI backend."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def test_tools() -> None:
    """Test all API endpoints used by MCP tools."""
    print("=" * 70)
    print("MCP API ENDPOINTS TEST")
    print("=" * 70)
    print()

    # Test 1: Latest Weight
    print("1. Testing /api/v1/body/weight/latest...")
    result = _get("/api/v1/body/weight/latest")
    if "error" not in result:
        print(f"   ✅ Weight: {result.get('value')} {result.get('unit')}")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 2: Weight History
    print("2. Testing /api/v1/body/weight (7 days)...")
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    result = _get(
        "/api/v1/body/weight",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": 100,
        },
    )
    if "error" not in result:
        print(f"   ✅ Found {result.get('count', 0)} measurements")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 3: Weight Trend
    print("3. Testing /api/v1/body/weight/trend (30 days)...")
    result = _get("/api/v1/body/weight/trend", params={"days": 30})
    if "error" not in result:
        print(f"   ✅ Change: {result.get('change', 'N/A')} kg")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 4: Daily Activity
    print("4. Testing /api/v1/activity/daily/2026-01-03...")
    result = _get("/api/v1/activity/daily/2026-01-03")
    if "error" not in result:
        print(f"   ✅ TDEE: {result.get('total_energy_kcal', 'N/A')} kcal")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 5: Activity Summary
    print("5. Testing /api/v1/activity/summary (7 days)...")
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    result = _get(
        "/api/v1/activity/summary",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    if "error" not in result:
        print(f"   ✅ Avg steps: {result.get('avg_steps_per_day', 'N/A')}")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 6: Workouts (Boxing)
    print("6. Testing /api/v1/workouts (Boxing, 30 days)...")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    result = _get(
        "/api/v1/workouts",
        params={
            "workout_type": "Boxing",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": 50,
        },
    )
    if "error" not in result:
        print(f"   ✅ Found {result.get('count', 0)} boxing workouts")
    else:
        print(f"   ❌ {result['error']}")
    print()

    # Test 7: Workout Stats
    print("7. Testing /api/v1/workouts/stats/by-type (30 days)...")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    result = _get(
        "/api/v1/workouts/stats/by-type",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    if "error" not in result and isinstance(result, list):
        print(f"   ✅ Found stats for {len(result)} workout types")
    else:
        print("   ❌ Error or no data")
    print()

    print("=" * 70)
    print("✅ All API endpoints tested!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Configure Claude Desktop (see docs/CLAUDE_DESKTOP_SETUP.md)")
    print("  2. Restart Claude Desktop")
    print("  3. Ask Claude: 'What's my current weight?'")


if __name__ == "__main__":
    print("Make sure FastAPI is running at http://localhost:8000")
    print()

    # Quick health check
    try:
        health = _get("/health")
        if health.get("status") == "healthy":
            print("✅ FastAPI server is running")
            print()
        else:
            print("❌ FastAPI server returned unexpected health status")
            print()
            exit(1)
    except Exception:
        print("❌ FastAPI server is not running!")
        print()
        print("Start it with:")
        print("  uvicorn src.api.main:app --reload --port 8000")
        print()
        exit(1)

    try:
        test_tools()
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure:")
        print("  1. FastAPI server is running")
        print("  2. Database has data imported")
