import random
import uuid
from datetime import datetime, timezone

MERCHANTS = [
    ("Amazon", "retail"), ("Walmart", "retail"), ("Target", "retail"),
    ("Starbucks", "food"), ("McDonalds", "food"), ("Subway", "food"),
    ("Uber", "transport"), ("Lyft", "transport"), ("Shell", "fuel"),
    ("Exxon", "fuel"), ("CVS", "health"), ("Walgreens", "health"),
    ("Netflix", "entertainment"), ("Spotify", "entertainment"),
    ("Apple Store", "tech"), ("Best Buy", "tech"),
    ("Home Depot", "home"), ("Lowe's", "home"),
    ("ATM Withdrawal", "cash"), ("Wire Transfer", "transfer"),
    ("Zelle Payment", "transfer"), ("Venmo", "transfer"),
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin",
    "Seattle", "Denver", "Boston", "Nashville", "Portland",
]

ACCOUNT_IDS = [f"ACC-{i:05d}" for i in range(1, 201)]


def _normal_amount():
    """Typical transaction: $5-$300."""
    return round(random.lognormvariate(3.5, 1.0), 2)


def _suspicious_amount():
    """Unusually large: $500-$5000."""
    return round(random.uniform(500, 5000), 2)


def generate_transaction(force_fraud=False):
    now = datetime.now(timezone.utc)
    hour = now.hour

    is_fraud = force_fraud or (random.random() < 0.03)

    if is_fraud:
        amount = _suspicious_amount()
        merchant, category = random.choice([
            ("Wire Transfer", "transfer"), ("ATM Withdrawal", "cash"),
            ("Jewelry Store", "luxury"), ("Electronics Outlet", "tech"),
            ("Unknown Merchant", "other"),
        ])
        city = random.choice(CITIES)
    else:
        amount = _normal_amount()
        merchant, category = random.choice(MERCHANTS)
        city = random.choice(CITIES)

    if not is_fraud and amount > 800 and random.random() < 0.4:
        is_fraud = True

    if not is_fraud and 1 <= hour <= 5 and random.random() < 0.15:
        is_fraud = True

    return {
        "transaction_id": str(uuid.uuid4()),
        "account_id": random.choice(ACCOUNT_IDS),
        "amount": max(0.01, amount),
        "merchant": merchant,
        "category": category,
        "city": city,
        "is_fraud": int(is_fraud),
        "timestamp": now.isoformat(),
    }
