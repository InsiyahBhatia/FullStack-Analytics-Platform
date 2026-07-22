"""Train the loan default model."""

from pathlib import Path

from models.train_all import train_default


if __name__ == "__main__":
    result = train_default(Path("data"), max_rows=150000)
    print(result["best"])
