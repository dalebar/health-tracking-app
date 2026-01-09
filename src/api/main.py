"""
FastAPI application for Health Tracking API.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import verify_api_key
from src.api.routes import activity, body, nutrition, sleep, workouts

app = FastAPI(
    title="Health Tracking API",
    description="REST API for accessing personal health metrics and workout data",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - configure origins from env for production
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with auth dependency
# All /api/v1/* routes require API key when API_KEY env var is set
app.include_router(
    body.router,
    prefix="/api/v1/body",
    tags=["Body Metrics"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    activity.router,
    prefix="/api/v1/activity",
    tags=["Activity"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    workouts.router,
    prefix="/api/v1/workouts",
    tags=["Workouts"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    sleep.router,
    prefix="/api/v1/sleep",
    tags=["Sleep"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    nutrition.router,
    prefix="/api/v1/nutrition",
    tags=["Nutrition"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/")
def root():
    """Root endpoint with API information (public)."""
    return {
        "name": "Health Tracking API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint (public, used by Render)."""
    return {"status": "healthy"}
