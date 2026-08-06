"""Local artifact registry used by FastAPI, Streamlit, and tests."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)

ARTIFACT_ROOT = Path("models/artifacts")
_TRUSTED_HASHES: dict[str, str] = {}


def _verify_model_integrity(model_path: Path) -> None:
    """Verify model file hash against known-good values if a manifest exists."""
    manifest = model_path.parent / "integrity.json"
    if manifest.exists():
        expected = json.loads(manifest.read_text(encoding="utf-8"))
        actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
        task = model_path.parent.name
        if task in expected and expected[task] != actual:
            raise SecurityError(
                f"Model integrity check failed for '{task}': "
                f"expected {expected[task]}, got {actual}"
            )
        logger.info("Model integrity verified for '%s'", task)


class SecurityError(Exception):
    pass


@dataclass
class LocalModel:
    model: object
    metadata: dict

    def predict_proba(self, frame):
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(frame)
        if hasattr(self.model, "decision_function"):
            import numpy as np

            score = self.model.decision_function(frame)
            score = 1 - ((score - score.min()) / max(score.max() - score.min(), 1e-9))
            return np.column_stack([1 - score, score])
        if hasattr(self.model, "predict"):
            import numpy as np

            pred = self.model.predict(frame)
            return np.column_stack([1 - pred, pred])
        raise AttributeError("Loaded model does not support probability or score prediction")

    @property
    def meta(self) -> dict:
        return self.metadata


def artifact_dir(task: str) -> Path:
    return ARTIFACT_ROOT / task


def save_model(task: str, model, metadata: dict) -> Path:
    out = artifact_dir(task)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "model.joblib"
    joblib.dump(model, model_path)
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    # Write integrity hash so load_model can verify before deserializing
    actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    manifest_path = out / "integrity.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    existing[task] = actual_hash
    manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return out


def load_model(task: str) -> LocalModel:
    out = artifact_dir(task)
    model_path = out / "model.joblib"
    meta_path = out / "metadata.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model artifact for task '{task}': {model_path}")
    _verify_model_integrity(model_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return LocalModel(joblib.load(model_path), metadata)
