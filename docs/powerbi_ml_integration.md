# Power BI ML Integration Plan

Add these metrics to the existing FinSight Power BI dashboard:

- Predicted Churn Rate
- Predicted Default Rate
- Predicted Fraud Rate
- Top Prediction Drivers
- Average Prediction Confidence
- Model Version
- Prediction Volume

## Recommended Tables

Use `fact_prediction_monitoring` or extend the existing `fact_prediction` table.

Suggested fields:

- `task`
- `model_name`
- `model_version`
- `prediction_label`
- `prediction_score`
- `top_drivers`
- `inference_ms`
- `created_at`

## DAX Measures

```DAX
Predicted Churn Rate = DIVIDE(CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "churn", fact_prediction_monitoring[prediction_label] = "Will Churn"), CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "churn"), 0)
```

```DAX
Predicted Default Rate = DIVIDE(CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "default", fact_prediction_monitoring[prediction_label] = "Likely Default"), CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "default"), 0)
```

```DAX
Predicted Fraud Rate = DIVIDE(CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "fraud", fact_prediction_monitoring[prediction_label] = "Fraud"), CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[task] = "fraud"), 0)
```

```DAX
Average Prediction Confidence = AVERAGE(fact_prediction_monitoring[prediction_score])
```

## Dashboard Placement

Executive Overview:
- Add predicted risk cards next to actual fraud/churn/default rates.

Fraud Analytics:
- Add predicted fraud rate trend and top fraud drivers.

Lending Analytics:
- Add predicted default by grade and purpose.

Customer Churn:
- Add predicted churn rate by contract type and payment method.

ETL Monitoring:
- Add model scoring volume and average inference latency.
