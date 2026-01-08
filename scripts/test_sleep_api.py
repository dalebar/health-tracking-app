#!/usr/bin/env python3
"""
Test script for Sleep API endpoints.

Run with: python scripts/test_sleep_api.py

Requires the API server to be running on localhost:8000
"""

import requests
import sys

BASE_URL = "http://localhost:8000"


def test_endpoint(name: str, url: str, params: dict | None = None) -> bool:
    """Test an API endpoint and print results."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    print("-" * 60)

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            # Pretty print a summary
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        print(f"  {key}: [{len(value)} items]")
                    elif isinstance(value, dict):
                        print(f"  {key}: {{...}}")
                    else:
                        print(f"  {key}: {value}")
            print("\nResult: PASS")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print("\nResult: FAIL")
            return False

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server")
        print("Make sure the server is running: uvicorn src.api.main:app")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main() -> int:
    """Run all sleep API tests."""
    print("=" * 60)
    print("SLEEP API TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Latest sleep
    results.append(
        test_endpoint(
            "Get Latest Sleep",
            f"{BASE_URL}/api/v1/sleep/latest",
        )
    )

    # Test 2: Sleep sessions (last 7 days)
    results.append(
        test_endpoint(
            "Get Sleep Sessions (7 days)",
            f"{BASE_URL}/api/v1/sleep/sessions",
            {"days": 7, "limit": 10},
        )
    )

    # Test 3: Sleep sessions with date range
    results.append(
        test_endpoint(
            "Get Sleep Sessions (30 days)",
            f"{BASE_URL}/api/v1/sleep/sessions",
            {"days": 30, "limit": 30},
        )
    )

    # Test 4: Sleep summary (7 days)
    results.append(
        test_endpoint(
            "Get Sleep Summary (7 days)",
            f"{BASE_URL}/api/v1/sleep/summary",
            {"days": 7},
        )
    )

    # Test 5: Sleep summary (30 days)
    results.append(
        test_endpoint(
            "Get Sleep Summary (30 days)",
            f"{BASE_URL}/api/v1/sleep/summary",
            {"days": 30},
        )
    )

    # Test 6: Get specific session by ID (get a valid ID from latest)
    # First get latest to find a valid ID
    try:
        latest = requests.get(f"{BASE_URL}/api/v1/sleep/latest", timeout=10).json()
        session_id = latest.get("id", 1)
    except Exception:
        session_id = 1

    results.append(
        test_endpoint(
            f"Get Sleep Session by ID ({session_id})",
            f"{BASE_URL}/api/v1/sleep/{session_id}",
        )
    )

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
