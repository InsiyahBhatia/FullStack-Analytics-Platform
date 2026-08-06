# FinSight Performance Benchmarks

Benchmark files are generated after model training:

```text
models/artifacts/churn_benchmarks.csv
models/artifacts/default_benchmarks.csv
models/artifacts/fraud_benchmarks.csv
```

## Target Metrics

| Model | Target ROC-AUC | Primary Business Goal |
|---|---:|---|
| Churn | 0.85+ | Identify customers likely to leave. |
| Loan default | 0.85+ | Reduce risky loan approvals and price credit risk. |
| Fraud | 0.90+ | Detect suspicious transactions with high recall. |

## Actual Results (v2 pipeline)

| Task | Winning Algorithm | ROC-AUC (test) | ROC-AUC (CV) | Train/Test gap | Verdict |
|---|---|---:|---:|---:|---|
| Churn | Logistic Regression | 0.839 | 0.844 | +0.007 | No overfitting |
| Loan default | CatBoost | 0.701 | 0.699 | +0.008 | No overfitting |
| Fraud | XGBoost (regularized) | 0.857 | 0.904 | +0.057 | No — gap is temporal drift |

How overfitting was reduced, per model:

- **Churn** — selected via a 5-fold stratified CV tournament with winner hyperparameter tuning; train (0.846) ≈ CV (0.844) ≈ test (0.839), a sub-1-point gap.
- **Loan default** — same 5-fold CV tournament plus calibrated SMOTE(0.25)/undersample(0.50) resampling; train (0.708) ≈ CV (0.699) ≈ test (0.701).
- **Fraud** — causal chronological split so velocity features never see the future (`velocity_cutoff_dt`), regularized XGBoost (`min_child_weight`, `gamma`, `reg_lambda`, `n_estimators` capped at 300), and all 590k rows: train 0.914 ≈ CV 0.904 shows no in-period overfit, and the residual test gap is temporal drift (test = most recent 20% of the stream).

## Interview Explanation

Accuracy is not enough for financial risk problems because fraud and default classes can be rare. Precision, recall, F1, and ROC-AUC are included so the model can be evaluated across both ranking quality and decision quality.

For fraud detection, recall is especially important because missed fraud can create direct financial loss. Precision is still monitored to avoid overwhelming operations teams with false positives.
