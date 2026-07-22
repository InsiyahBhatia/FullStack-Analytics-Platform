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

## Interview Explanation

Accuracy is not enough for financial risk problems because fraud and default classes can be rare. Precision, recall, F1, and ROC-AUC are included so the model can be evaluated across both ranking quality and decision quality.

For fraud detection, recall is especially important because missed fraud can create direct financial loss. Precision is still monitored to avoid overwhelming operations teams with false positives.
