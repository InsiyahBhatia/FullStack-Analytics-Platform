# TODO

## Models
- [ ] Retrain all three models with the datasets in place (`python -m models.train_all --log-mlflow`); shipped artifacts predate the validation/calibration changes
- [ ] Improve the loan default model (test ROC-AUC ~0.70): add more Lending Club features (sub-grade, term, interest rate, credit history length, inquiries)
- [ ] Reduce fraud false alerts (precision ~12%); investigate the CV vs test AUC gap (0.90 vs 0.86)
- [ ] Add SHAP-based per-prediction drivers to the API (`top_drivers` is currently just the feature list)
- [ ] Add drift monitoring (PSI) on input features and score distribution
- [ ] Add tests for calibration under SMOTE on real-size data

## Dashboards
- [ ] Review the 8 Power BI pages against the business questions answered in `streamlit/business.py`; close gaps (segment churn, revenue at risk, pricing vs expected loss, fraud timing)
- [ ] Add Power BI measures for expected credit loss and revenue-at-risk
- [ ] Point Streamlit `WAREHOUSE_URL` at the real warehouse and validate the business pages against live data
- [ ] Replace the assumed capture rate / loss-given-default in the Streamlit pages with model-derived values
- [ ] Add authentication to the Streamlit app

## Platform
- [ ] Fix API test setup (API key format for `API_KEYS_DEV`) so `pytest tests` runs out of the box
- [ ] Add CI to run tests and a Streamlit smoke test
