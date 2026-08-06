"""
FinSight Streaming Producer

Generates fake financial transactions and pushes them to a Redis Stream.
Runs continuously, producing 1-5 transactions per second.

Usage:
    python -m streaming.producer
"""

import json
import logging
import random
import time

import redis

from streaming.config import REDIS_HOST, REDIS_PORT, REDIS_STREAM
from streaming.generator import generate_transaction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [producer] %(levelname)s: %(message)s",
)
logger = logging.getLogger("finsight.producer")

RETRY_DELAY = 5
MAX_RETRIES = 10


def get_connection():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=5)


def main():
    r = get_connection()

    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"Producing to stream: {REDIS_STREAM}")
    logger.info("Press Ctrl+C to stop")

    count = 0
    retries = 0
    try:
        while True:
            try:
                tx = generate_transaction()
                r.xadd(REDIS_STREAM, {"data": json.dumps(tx)})
                count += 1
                retries = 0

                flag = " FRAUD" if tx["is_fraud"] else ""
                if count % 10 == 0:
                    logger.info(f"[{count}] {tx['merchant']:20s} ${tx['amount']:>9.2f}{flag}")

                time.sleep(random.uniform(0.2, 1.0))

            except redis.exceptions.ConnectionError as e:
                retries += 1
                delay = min(RETRY_DELAY * retries, 60)
                logger.warning(f"Redis connection lost ({e}), retrying in {delay}s...")
                time.sleep(delay)
                try:
                    r = get_connection()
                    logger.info("Reconnected to Redis")
                except Exception:
                    pass

            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error: {e}")
                time.sleep(RETRY_DELAY)

    except KeyboardInterrupt:
        logger.info(f"Stopped. Total transactions produced: {count}")


if __name__ == "__main__":
    main()
