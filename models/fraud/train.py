"""Train the fraud detection model."""

from pathlib import Path

from models.train_all import train_fraud


if __name__ == "__main__":
    result = train_fraud(Path("data"), max_rows=150000)
    print(result["best"])
