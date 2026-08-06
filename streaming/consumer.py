"""
FinSight Streaming Consumer

Reads transactions from Redis Stream and writes to PostgreSQL.
Uses consumer groups for horizontal scaling.

Usage:
    python -m streaming.consumer
"""

import json
import logging
import time

import redis
from sqlalchemy import create_engine, text

from streaming.config import (
    DB_URL, REDIS_CONSUMER, REDIS_GROUP, REDIS_HOST, REDIS_PORT, REDIS_STREAM,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [consumer] %(levelname)s: %(message)s",
)
logger = logging.getLogger("finsight.consumer")

BATCH_SIZE = 10
FLUSH_INTERVAL = 5
RETRY_DELAY = 5
MAX_RETRIES = 10


def ensure_table(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fact_streaming_transaction (
                transaction_id   TEXT PRIMARY KEY,
                account_id       TEXT NOT NULL,
                amount           NUMERIC(12,2) NOT NULL,
                merchant         TEXT NOT NULL,
                category         TEXT NOT NULL,
                city             TEXT,
                is_fraud         BOOLEAN DEFAULT FALSE,
                transaction_ts   TIMESTAMPTZ NOT NULL,
                ingested_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_streaming_ts
            ON fact_streaming_transaction (transaction_ts)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_streaming_fraud
            ON fact_streaming_transaction (is_fraud)
        """))
    logger.info("Table fact_streaming_transaction ready")


def ensure_consumer_group(r):
    try:
        r.xgroup_create(REDIS_STREAM, REDIS_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group: {REDIS_GROUP}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass
        else:
            raise


def get_redis_connection():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=5)


def main():
    r = get_redis_connection()
    engine = create_engine(DB_URL, pool_pre_ping=True)

    ensure_table(engine)
    ensure_consumer_group(r)

    logger.info(f"Consumer '{REDIS_CONSUMER}' ready")
    logger.info(f"Reading from stream: {REDIS_STREAM}")
    logger.info("Writing to: PostgreSQL")
    logger.info("Press Ctrl+C to stop")

    total = 0
    fraud_count = 0
    retries = 0
    try:
        while True:
            try:
                entries = r.xreadgroup(
                    REDIS_GROUP,
                    REDIS_CONSUMER,
                    {REDIS_STREAM: ">"},
                    count=BATCH_SIZE,
                    block=FLUSH_INTERVAL * 1000,
                )

                if not entries:
                    continue

                for stream_name, messages in entries:
                    rows = []
                    ids = []
                    for msg_id, fields in messages:
                        try:
                            tx = json.loads(fields["data"])
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Skipping malformed message {msg_id}: {e}")
                            r.xack(REDIS_STREAM, REDIS_GROUP, msg_id)
                            continue

                        rows.append({
                            "transaction_id": tx["transaction_id"],
                            "account_id": tx["account_id"],
                            "amount": tx["amount"],
                            "merchant": tx["merchant"],
                            "category": tx["category"],
                            "city": tx["city"],
                            "is_fraud": bool(tx["is_fraud"]),
                            "transaction_ts": tx["timestamp"],
                        })
                        ids.append(msg_id)

                    if rows:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO fact_streaming_transaction
                                        (transaction_id, account_id, amount, merchant,
                                         category, city, is_fraud, transaction_ts)
                                    VALUES
                                        (:transaction_id, :account_id, :amount, :merchant,
                                         :category, :city, :is_fraud, :transaction_ts)
                                    ON CONFLICT (transaction_id) DO NOTHING
                                """),
                                rows,
                            )

                    r.xack(REDIS_STREAM, REDIS_GROUP, *ids)
                    retries = 0

                    batch_fraud = sum(1 for row in rows if row["is_fraud"])
                    total += len(rows)
                    fraud_count += batch_fraud

                    if total % 50 == 0:
                        logger.info(
                            f"[{total} ingested | {fraud_count} fraud detected]"
                        )

            except redis.exceptions.ConnectionError as e:
                retries += 1
                delay = min(RETRY_DELAY * retries, 60)
                logger.warning(f"Redis connection lost ({e}), retrying in {delay}s...")
                time.sleep(delay)
                try:
                    r = get_redis_connection()
                    ensure_consumer_group(r)
                    logger.info("Reconnected to Redis")
                except Exception:
                    pass

            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error: {e}")
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                time.sleep(RETRY_DELAY)

    except KeyboardInterrupt:
        logger.info(f"Stopped. Total: {total} ingested, {fraud_count} fraud")


if __name__ == "__main__":
    main()
