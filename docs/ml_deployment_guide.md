# FinSight ML Deployment Guide

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

Train models:

```bash
python -m models.train_all --task all --max-rows 150000
```

Start API:

```bash
uvicorn api.main:app --reload
```

Start Streamlit:

```bash
streamlit run streamlit/app.py
```

## Dockerized Demo Stack

Use the ML compose file:

```bash
docker compose -f docker/docker-compose.ml.yml up --build
```

Services:

| Service | URL |
|---|---|
| FastAPI | `http://localhost:8000/docs` |
| MLflow | `http://localhost:5000` |
| Streamlit | `http://localhost:8501` |
| PostgreSQL | `localhost:5433` |

## Production Notes

- Move secrets to a vault or managed secret store.
- Use managed PostgreSQL for the warehouse and MLflow backend store.
- Store MLflow artifacts in S3, ADLS, or another durable object store.
- Add authentication back to prediction endpoints before internet exposure.
- Add request logging, drift monitoring, and model approval gates.
- Run batch scoring jobs daily and write results to `fact_prediction_monitoring`.
