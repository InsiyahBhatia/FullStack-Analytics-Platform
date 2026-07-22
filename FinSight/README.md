# Power BI & Analytics (DAX)

The FinSight Power BI project (`.pbip`) contains the entire presentation layer of the platform. It features an 8-page interactive dashboard backed by a robust TMDL semantic model pulling directly from our PostgreSQL Data Warehouse.

## Dashboard Overview

The dashboard is structured into 8 highly focused pages:
1. **Executive Overview**: High-level KPIs across all business domains.
2. **Lending Analytics**: Loan origination and default risk profiles.
3. **Fraud Analytics**: Real-time and historical transaction security metrics.
4. **Customer Churn**: Retention tracking and lifetime value analysis.
5. **Customer Detail**: Individual client drill-through capabilities.
6. **ETL Monitoring**: Data pipeline health and Airflow success rates.
7. **ML Monitoring**: Model drift, latency, and fallback tracking.
8. **Real-Time Monitoring**: Live streaming transaction analysis.

![Executive Overview](../screenshots/pbi_01_executive_overview.jpg)

## Comprehensive DAX Measures

The Semantic Model utilizes over 50 DAX measures. Below are the most critical DAX queries powering the dashboards:

### 1. Key Performance Indicators (KPIs)
```dax
TotalCustomers = COUNTROWS(fact_churn)
TotalLoans = COUNT(fact_loan[loan_id_orig])
TotalTransactions = COUNTROWS(fact_transaction)
TotalStreamTransactions = COUNTROWS(fact_streaming_transaction)
```

### 2. Risk & Rates
```dax
ChurnRate = DIVIDE([ChurnCount], [TotalCustomers], 0)
DefaultRate = DIVIDE([DefaultCount], [TotalLoans], 0)
FraudRate = DIVIDE(SUM(fact_transaction[is_fraud]), COUNT(fact_transaction[transaction_id]), 0)
StreamFraudRate = DIVIDE([StreamFraudCases], [TotalStreamTransactions], 0)
```

### 3. Advanced Financial Metrics
```dax
CustomerLifetimeValue = 
VAR AvgMonthlyRevenue = AVERAGE(fact_churn[monthly_charges])
VAR ChurnProb = [LatestChurnRate] 
RETURN IF(ISBLANK(ChurnProb) || ChurnProb = 0, 0, AvgMonthlyRevenue / ChurnProb)

RevenueAtRisk = 
SUMX(
    FILTER(fact_churn, fact_churn[churn] = FALSE()),
    [CustomerLifetimeValue] * [LatestChurnRate]
)

RiskExposure = 
SUMX(fact_loan, fact_loan[loan_amount] * [LatestDefaultRate])

FraudLossPct = DIVIDE([TotalFraudAmount], [TransactionVolume], 0)
FraudSeverity = DIVIDE([TotalFraudAmount], [FraudCases], 0)
```

### 4. Real-Time & Streaming
```dax
CurrentTxn5Min = CALCULATE([TotalStreamTransactions], fact_streaming_transaction[timestamp] >= NOW() - 5/1440)
CurrentFraud5Min = CALCULATE([StreamFraudCases], fact_streaming_transaction[timestamp] >= NOW() - 5/1440)
CurrentAvgAmt5Min = CALCULATE([StreamAvgAmount], fact_streaming_transaction[timestamp] >= NOW() - 5/1440)
```

### 5. ML Ops & Monitoring
```dax
TotalPredictions = COUNT(fact_prediction_monitoring[prediction_id])
FallbackRate = DIVIDE(
    CALCULATE(COUNTROWS(fact_prediction_monitoring), fact_prediction_monitoring[fallback] = TRUE()),
    [TotalPredictions], 0
)
PredictionSuccessRate = 1 - [FallbackRate]
AvgConfidence = AVERAGE(fact_prediction_monitoring[prediction_score])
AvgLatencyMs = AVERAGE(fact_prediction_monitoring[inference_ms])
```

### 6. UI & Theming (Dynamic Formatting)
```dax
Dynamic Theme Color = 
VAR RankVal = SWITCH(TRUE(), 
    ISINSCOPE('fact_loan'[loan_status]), RANKX(ALLSELECTED('fact_loan'[loan_status]), CALCULATE(MAX('fact_loan'[loan_status])), , ASC, DENSE), 
    ISINSCOPE('fact_loan'[grade]), RANKX(ALLSELECTED('fact_loan'[grade]), CALCULATE(MAX('fact_loan'[grade])), , ASC, DENSE),
    1) 
VAR ModIndex = MOD(INT(RankVal) - 1, 24) + 1 
VAR HexCode = LOOKUPVALUE(Dim_ColorPalette[HexCode], Dim_ColorPalette[Index], ModIndex) 
RETURN COALESCE(HexCode, "#000000")
```

## Configuration & Usage

*   **Format**: The project uses the modern Power BI Project (`.pbip`) format, enabling version control of the Semantic Model via TMDL.
*   **Connection**: It connects to PostgreSQL via the standard ODBC/PostgreSQL connector. Ensure you have the Npgsql provider installed on your Windows machine if opening locally.
*   **Opening**: Double-click `FinSight.pbip` in this directory to launch Power BI Desktop.
