"""Calibration wrapper and richer evaluation metrics for FinSight models."""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_curve,
    precision_recall_curve,
)
from sklearn.calibration import calibration_curve


class CalibratedPipeline:
    """Fitted pipeline + probability calibrator.

    SMOTE / class weighting distorts predicted probabilities, so the raw scores are
    not real default/fraud/churn rates. The calibrator is fit on a held-out
    validation slice and maps raw scores to calibrated probabilities. Exposes
    ``named_steps`` so feature-importance and SHAP code keep working.
    """

    def __init__(self, base, calibrator, method: str):
        self.base = base
        self.calibrator = calibrator
        self.method = method

    @property
    def named_steps(self):
        return self.base.named_steps

    def _raw(self, x) -> np.ndarray:
        return self.base.predict_proba(x)[:, 1]

    def _apply(self, raw: np.ndarray) -> np.ndarray:
        if self.method == "isotonic":
            return np.clip(self.calibrator.predict(raw), 0.0, 1.0)
        logit = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / (1 - np.clip(raw, 1e-6, 1 - 1e-6)))
        return self.calibrator.predict_proba(logit.reshape(-1, 1))[:, 1]

    def predict_proba(self, x) -> np.ndarray:
        p = self._apply(self._raw(x))
        return np.column_stack([1 - p, p])


def fit_calibrator(raw_scores, y_true) -> tuple[object, str]:
    """Fit isotonic or sigmoid calibration, whichever has the lower Brier score.

    Isotonic needs enough data to avoid overfitting, so it is only considered with
    >= 500 validation rows and >= 30 positives; the choice is made by 2-fold
    cross-fitting on the validation slice.
    """
    raw = np.asarray(raw_scores, dtype=float)
    y = np.asarray(y_true, dtype=int)
    logit = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / (1 - np.clip(raw, 1e-6, 1 - 1e-6))).reshape(-1, 1)
    sigmoid = LogisticRegression(C=1e6, max_iter=1000).fit(logit, y)

    if len(y) >= 500 and y.sum() >= 30:
        idx = np.random.RandomState(42).permutation(len(y))
        half = len(y) // 2
        a, b = idx[:half], idx[half:]
        scores = {"isotonic": 0.0, "sigmoid": 0.0}
        for tr, te in ((a, b), (b, a)):
            if y[tr].sum() == 0 or y[te].sum() == 0:
                break
            iso = IsotonicRegression(out_of_bounds="clip").fit(raw[tr], y[tr])
            sig = LogisticRegression(C=1e6, max_iter=1000).fit(logit[tr], y[tr])
            scores["isotonic"] += brier_score_loss(y[te], np.clip(iso.predict(raw[te]), 0, 1))
            scores["sigmoid"] += brier_score_loss(y[te], sig.predict_proba(logit[te])[:, 1])
        else:
            if scores["isotonic"] < scores["sigmoid"]:
                return IsotonicRegression(out_of_bounds="clip").fit(raw, y), "isotonic"
    return sigmoid, "sigmoid"


def ks_statistic(y_true, y_score) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return float(np.max(tpr - fpr))


def lift_at(y_true, y_score, fraction: float = 0.1) -> float:
    """Precision in the top ``fraction`` of scores divided by the base rate."""
    y = np.asarray(y_true)
    n = max(1, int(len(y) * fraction))
    top = np.argsort(-np.asarray(y_score))[:n]
    base = y.mean()
    return float(y[top].mean() / base) if base > 0 else 0.0


def extended_metrics(y_true, y_score, threshold: float) -> dict:
    """Threshold-free and confusion-matrix metrics beyond ROC-AUC."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=float)
    pred = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {
        "pr_auc": round(float(average_precision_score(y, s)), 4),
        "ks": round(ks_statistic(y, s), 4),
        "lift_top10": round(lift_at(y, s, 0.1), 3),
        "base_rate": round(float(y.mean()), 4),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "specificity": round(float(tn / max(tn + fp, 1)), 4),
    }
    if 0.0 <= s.min() and s.max() <= 1.0:
        out["brier"] = round(float(brier_score_loss(y, s)), 4)
        out["log_loss"] = round(float(log_loss(y, np.clip(s, 1e-6, 1 - 1e-6), labels=[0, 1])), 4)
    return out


def curve_payload(y_true, y_score, bins: int = 10, max_points: int = 100) -> dict:
    """Downsampled ROC / PR / calibration curves for dashboards (JSON-safe)."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=float)

    def thin(*arrays):
        n = len(arrays[0])
        if n <= max_points:
            return [np.round(a, 4).tolist() for a in arrays]
        keep = np.linspace(0, n - 1, max_points).astype(int)
        return [np.round(np.asarray(a)[keep], 4).tolist() for a in arrays]

    fpr, tpr, _ = roc_curve(y, s)
    prec, rec, _ = precision_recall_curve(y, s)
    payload = {"roc": dict(zip(("fpr", "tpr"), thin(fpr, tpr))),
               "pr": dict(zip(("precision", "recall"), thin(prec, rec)))}
    if 0.0 <= s.min() and s.max() <= 1.0:
        try:
            frac_pos, mean_pred = calibration_curve(y, s, n_bins=bins, strategy="quantile")
            payload["calibration"] = {"mean_predicted": np.round(mean_pred, 4).tolist(),
                                      "fraction_positive": np.round(frac_pos, 4).tolist()}
        except ValueError:
            pass
    return payload
