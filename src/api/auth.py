"""API key authentication for deployed API."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """
    Verify the API key from request header.

    If API_KEY env var is not set, allows all requests (local dev mode).
    If API_KEY is set, requires matching key in X-API-Key header.

    Returns:
        The API key or "dev-mode" if no auth required.

    Raises:
        HTTPException: 401 if key is missing or invalid.
    """
    expected_key = os.getenv("API_KEY")

    # No API_KEY set = local dev mode, allow all
    if not expected_key:
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
