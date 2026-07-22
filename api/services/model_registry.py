"""
ModelRegistry — abstraction over MLflow for model loading + caching
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ModelWrapper:
    """Wraps a loaded model with metadata."""

    def __init__(self, model, meta: dict):
        self._model = model
        self.meta = meta

    def predict_proba(self, features):
        return self._model.predict_proba(features)

    def predict(self, features):
        return self._model.predict(features)


class ModelRegistry:
    """Caches models from MLflow in Redis for low-latency inference."""

    def __init__(self, tracking_uri: str, cache_client, ttl_seconds: int = 3600):
        self.tracking_uri = tracking_uri
        self.cache = cache_client
        self.ttl = ttl_seconds
        self._local_cache: dict[str, ModelWrapper] = {}

    async def get_model(self, task: str, alias: str = "latest") -> ModelWrapper:
        cache_key = f"model:{task}:{alias}"

        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        cached_meta = await self.cache.get(cache_key)
        if cached_meta:
            meta = json.loads(cached_meta)
            model = self._load_local(meta["artifact_path"])
            wrapper = ModelWrapper(model, meta)
            self._local_cache[cache_key] = wrapper
            return wrapper

        model, meta = self._load_from_mlflow(task, alias)
        wrapper = ModelWrapper(model, meta)

        await self.cache.setex(cache_key, self.ttl, json.dumps(meta))
        self._local_cache[cache_key] = wrapper

        return wrapper

    def _load_from_mlflow(self, task: str, alias: str):
        try:
            import mlflow
            mlflow.set_tracking_uri(self.tracking_uri)

            model_uri = f"models:/finsight_{task}/{alias}"
            model = mlflow.pyfunc.load_model(model_uri)

            client = mlflow.MlflowClient()
            mv = client.get_model_version_by_alias(f"finsight_{task}", alias)

            meta = {
                "name": f"finsight_{task}",
                "version": mv.version if mv else "unknown",
                "artifact_path": model_uri,
                "run_id": mv.run_id if mv else None,
            }
            logger.info(f"Loaded model {meta['name']}:{meta['version']}")
            return model, meta
        except ImportError:
            logger.warning("MLflow not installed; using dummy model")
            return self._dummy_model(), {
                "name": f"finsight_{task}",
                "version": "0.0.0-dev",
                "artifact_path": "dummy",
            }

    def _load_local(self, artifact_path: str):
        if artifact_path == "dummy":
            return self._dummy_model()
        import mlflow
        return mlflow.pyfunc.load_model(artifact_path)

    def _dummy_model(self):
        class DummyModel:
            def predict_proba(self, features):
                import numpy as np
                return np.array([[0.7, 0.3]])

            def predict(self, features):
                import numpy as np
                return np.array([0])

        return DummyModel()

    async def invalidate(self, task: str, alias: str = "latest"):
        cache_key = f"model:{task}:{alias}"
        await self.cache.delete(cache_key)
        self._local_cache.pop(cache_key, None)
        logger.info(f"Invalidated cache for {cache_key}")
