"""Verify all packages and infrastructure are ready."""

import os
import sqlalchemy
import redis

print("=== Package Versions ===")
import pandas; print(f"  pandas: {pandas.__version__}")
import numpy; print(f"  numpy: {numpy.__version__}")
import sklearn; print(f"  scikit-learn: {sklearn.__version__}")
import xgboost; print(f"  XGBoost: {xgboost.__version__}")
import lightgbm; print(f"  LightGBM: {lightgbm.__version__}")
import fastapi; print(f"  FastAPI: {fastapi.__version__}")
import pyspark; print(f"  PySpark: {pyspark.__version__}")
import streamlit; print(f"  Streamlit: {streamlit.__version__}")
import plotly; print(f"  Plotly: {plotly.__version__}")
import redis; print(f"  redis-py: {redis.__version__}")

print("\n=== Infrastructure ===")

# PostgreSQL
try:
    engine = sqlalchemy.create_engine(
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5433')}/{os.environ.get('DB_NAME', 'finsight')}"
    )
    with engine.connect() as conn:
        tables = conn.execute(
            sqlalchemy.text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
        ).scalar()
        views = conn.execute(
            sqlalchemy.text("SELECT count(*) FROM information_schema.views WHERE table_schema='public'")
        ).scalar()
    print(f"  PostgreSQL: connected ({tables} tables, {views} views)")
except Exception as e:
    print(f"  PostgreSQL: FAILED — {e}")

# Redis
try:
    r = redis.Redis(host="localhost", port=6379, decode_responses=True, socket_connect_timeout=3)
    r.ping()
    print(f"  Redis: connected")
except Exception as e:
    print(f"  Redis: FAILED — {e}")

print("\nDone - Setup complete")
