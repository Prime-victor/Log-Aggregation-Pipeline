"""
AI/ML Microservice — Anomaly Detection.
Exposes HTTP API consumed by Django Celery workers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from api.routes import router
from anomaly_detection.detector import AnomalyDetector

logger = structlog.get_logger()

# Shared detector instance — loaded once at startup
detector: AnomalyDetector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load/train model at startup. Runs once when the service starts."""
    global detector
    logger.info("ai_service.startup", msg="Loading anomaly detection model...")

    detector = AnomalyDetector()
    await detector.initialize()  # Load from disk or train fresh

    logger.info("ai_service.startup", msg="Model ready.")
    app.state.detector = detector

    yield

    logger.info("ai_service.shutdown", msg="Shutting down AI service.")


app = FastAPI(
    title="Log Intelligence — AI/ML Service",
    description="Isolation Forest anomaly detection for log streams",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to internal network in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy", "model_ready": app.state.detector.is_trained}