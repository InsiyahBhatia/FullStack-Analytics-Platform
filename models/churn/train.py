"""Train the customer churn model."""

from pathlib import Path

from models.train_all import train_churn


if __name__ == "__main__":
    result = train_churn(Path("data"), max_rows=150000)
    print(result["best"])
