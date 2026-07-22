import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_STREAM = "finsight:transactions"
REDIS_GROUP = "finsight_consumers"
REDIS_CONSUMER = os.environ.get("HOSTNAME", "consumer-1")

DB_USER = os.environ.get("DB_USER", "finsight_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "finsight_dev_2026")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5433")
DB_NAME = os.environ.get("DB_NAME", "finsight")
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
