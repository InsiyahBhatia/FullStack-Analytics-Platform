# MLflow

This directory documents MLflow usage for FinSight.

Run the tracking server through Docker:

```bash
docker compose -f docker/docker-compose.ml.yml up mlflow
```

Log training runs:

```bash
python -m models.train_all --task all --log-mlflow
```

Tracked assets:

- Parameters
- Metrics
- Model artifact
- Metadata JSON
- Registered model name: `finsight_<task>`
