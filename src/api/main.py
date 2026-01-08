"""
FastAPI application for Health Tracking API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import body, activity, workouts, sleep

app = FastAPI(
    title="Health Tracking API",
    description="REST API for accessing personal health metrics and workout data",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(body.router, prefix="/api/v1/body", tags=["Body Metrics"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["Activity"])
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["Workouts"])
app.include_router(sleep.router, prefix="/api/v1/sleep", tags=["Sleep"])


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Health Tracking API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
