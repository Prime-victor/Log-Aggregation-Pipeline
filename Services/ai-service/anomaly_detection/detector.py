"""
Isolation Forest anomaly detector.

How Isolation Forest works:
  - Randomly partitions feature space using decision trees
  - Anomalous points are isolated in fewer splits (shorter path length)
  - Produces an anomaly score in [-1, 1]: -1 = anomalous, 1 = normal
  - We normalize this to [0, 1] where 1 = maximally anomalous

Features used (per 5-minute window, per service):
  - error_rate:       % of logs that are ERROR/CRITICAL
  - log_volume:       total log count
  - p99_latency:      99th percentile response time
  - error_velocity:   rate of change in error count
  - critical_ratio:   % of errors that are CRITICAL
"""

import os
import pickle
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from anomaly_detection.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/isolation_forest.pkl"))
SCALER_PATH = Path(os.getenv("SCALER_PATH", "/app/models/scaler.pkl"))

# Contamination = expected fraction of anomalies in training data.
# 0.05 = "we expect 5% of our historical windows to be anomalous"
# Tune this based on your baseline environment.
CONTAMINATION = float(os.getenv("CONTAMINATION", "0.05"))


class AnomalyDetector:

    def __init__(self):
        self.model:   Optional[IsolationForest] = None
        self.scaler:  Optional[StandardScaler]  = None
        self.extractor = FeatureExtractor()
        self.is_trained = False

    async def initialize(self):
        """Load existing model or train a new one from historical data."""
        if MODEL_PATH.exists() and SCALER_PATH.exists():
            self._load_model()
            logger.info("Loaded existing model from disk.")
        else:
            logger.info("No model found — training from historical data...")
            await self.train()

    async def train(self, lookback_hours: int = 168):  # 1 week of history
        """
        Train the Isolation Forest on historical log windows.
        In production: run this as a scheduled weekly job.
        """
        logger.info(f"Training model on {lookback_hours}h of historical data...")

        features = await self.extractor.extract_training_features(lookback_hours)

        if features is None or len(features) < 10:
            logger.warning("Insufficient training data — using default parameters")
            # Bootstrap with a minimal untrained model
            self.model  = IsolationForest(contamination=CONTAMINATION, random_state=42)
            self.scaler = StandardScaler()
            self.is_trained = False
            return

        X = np.array(features)

        # Scale features to zero mean, unit variance
        self.scaler = StandardScaler()
        X_scaled    = self.scaler.fit_transform(X)

        # Train model
        self.model = IsolationForest(
            n_estimators=200,            # More trees = more stable scores
            contamination=CONTAMINATION,
            max_samples="auto",
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1,                   # Use all CPU cores
            random_state=42,
        )
        self.model.fit(X_scaled)
        self.is_trained = True

        # Persist to disk
        self._save_model()
        logger.info(f"Model trained on {len(X)} windows. Saved to {MODEL_PATH}")

    async def detect(self, window_minutes: int = 5) -> list[dict]:
        """
        Detect anomalies in the current window across all services.
        Returns a list of anomaly dicts (empty if nothing detected).
        """
        now   = datetime.now(timezone.utc)
        start = now - timedelta(minutes=window_minutes)

        # Extract current feature vectors (one per service)
        service_features = await self.extractor.extract_current_features(start, now)

        if not service_features:
            return []

        anomalies = []

        for service_name, feature_vector in service_features.items():
            score, is_anomaly, confidence = self._score_features(feature_vector)

            if is_anomaly:
                anomaly_type = self._classify_anomaly(feature_vector)
                anomalies.append({
                    "service":     service_name,
                    "type":        anomaly_type,
                    "score":       score,
                    "confidence":  confidence,
                    "detected_at": now.isoformat(),
                    "window_start": start.isoformat(),
                    "window_end":   now.isoformat(),
                    "description": self._describe_anomaly(service_name, feature_vector, anomaly_type),
                    "features": {
                        "error_rate":     feature_vector[0],
                        "log_volume":     feature_vector[1],
                        "p99_latency_ms": feature_vector[2],
                        "error_velocity": feature_vector[3],
                        "critical_ratio": feature_vector[4],
                    }
                })

        return anomalies

    def _score_features(self, features: list[float]) -> tuple[float, bool, float]:
        """
        Score a single feature vector.
        Returns (anomaly_score, is_anomaly, confidence).
        """
        if not self.is_trained or self.model is None:
            return 0.0, False, 0.0

        X = np.array([features])
        X_scaled = self.scaler.transform(X)

        # Raw score: negative = anomalous, positive = normal
        raw_score = self.model.score_samples(X_scaled)[0]

        # Normalize to [0, 1] where 1 = most anomalous
        # Typical range for score_samples is roughly [-0.5, 0.5]
        normalized = float(np.clip(-raw_score + 0.5, 0, 1))

        prediction  = self.model.predict(X_scaled)[0]   # -1 = anomaly, 1 = normal
        is_anomaly  = prediction == -1
        confidence  = min(abs(raw_score) * 2, 1.0)       # Rough confidence heuristic

        return normalized, is_anomaly, confidence

    def _classify_anomaly(self, features: list[float]) -> str:
        """Classify the type of anomaly based on which features are most extreme."""
        error_rate, log_volume, p99_latency, error_velocity, critical_ratio = features

        # Simple heuristic — in production: use a decision tree classifier
        if error_rate > 20 or critical_ratio > 0.5:
            return "ERROR_BURST"
        elif p99_latency > 2000:
            return "LATENCY_SPIKE"
        elif log_volume > 10000:
            return "VOLUME_SPIKE"
        return "UNUSUAL_PATTERN"

    def _describe_anomaly(self, service: str, features: list, anomaly_type: str) -> str:
        error_rate, log_volume, p99_latency, _, _ = features
        descriptions = {
            "ERROR_BURST":     f"{service}: Error rate spiked to {error_rate:.1f}%",
            "LATENCY_SPIKE":   f"{service}: P99 latency reached {p99_latency:.0f}ms",
            "VOLUME_SPIKE":    f"{service}: Log volume surged to {int(log_volume)} entries",
            "UNUSUAL_PATTERN": f"{service}: Unusual log pattern detected by ML model",
        }
        return descriptions.get(anomaly_type, f"Anomaly detected in {service}")

    def _save_model(self):
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)

    def _load_model(self):
        with open(MODEL_PATH, "rb") as f:
            self.model = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            self.scaler = pickle.load(f)
        self.is_trained = True
