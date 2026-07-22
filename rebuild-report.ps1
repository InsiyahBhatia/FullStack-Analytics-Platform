$def = "D:\FinSight\FinSight\FinSight.Report\definition"
$schema = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json"
$enc = [System.Text.UTF8Encoding]::new($false)

function Write-Json($path, $obj) {
    $json = $obj | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($path, $json, $enc)
}

function New-Visual($page, $name, $type, $x, $y, $w, $h) {
    $dir = "$def\pages\$page\visuals\$name"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $o = @{
        "`$schema" = $schema
        name = $name
        position = @{ x = $x; y = $y; z = 0; height = $h; width = $w; tabOrder = 0 }
        visual = @{
            visualType = $type
            query = @{ queryState = @{} }
            drillFilterOtherVisuals = $true
        }
    }
    Write-Json "$dir\visual.json" $o
    Write-Host "  + $page/$name ($type)"
}

function Set-Card($page, $name, $entity, $property) {
    $f = "$def\pages\$page\visuals\$name\visual.json"
    $j = Get-Content $f -Raw | ConvertFrom-Json
    $j.visual.query = @{ queryState = @{ Values = @{ projections = @(@{ field = @{ Measure = @{ Expression = @{ SourceRef = @{ Entity = $entity } }; Property = $property } }; queryRef = "$entity.$property"; nativeQueryRef = $property }) } } }
    Write-Json $f $j
    Write-Host "    ~ $entity.$property"
}

function Set-Chart($page, $name, $entity, $catCol, $valEntity, $valProp) {
    $f = "$def\pages\$page\visuals\$name\visual.json"
    $j = Get-Content $f -Raw | ConvertFrom-Json
    $j.visual.query = @{ queryState = @{ Values = @{ projections = @(@{ field = @{ Measure = @{ Expression = @{ SourceRef = @{ Entity = $valEntity } }; Property = $valProp } }; queryRef = "$valEntity.$valProp"; nativeQueryRef = $valProp }) }; Category = @{ projections = @(@{ field = @{ Column = @{ Expression = @{ SourceRef = @{ Entity = $entity } }; Property = $catCol } }; queryRef = "$entity.$catCol"; nativeQueryRef = $catCol }) } } }
    Write-Json $f $j
    Write-Host "    ~ $catCol x $valProp"
}

# Clean old
Remove-Item "$def\pages\*\visuals\*" -Recurse -Force -ErrorAction SilentlyContinue

# ========== EXECUTIVE OVERVIEW ==========
Write-Host "=== Executive Overview ==="
New-Visual executive_overview total_customers card 0 0 140 100
New-Visual executive_overview total_loans card 160 0 140 100
New-Visual executive_overview total_revenue card 320 0 140 100
New-Visual executive_overview fraud_rate card 480 0 140 100
New-Visual executive_overview churn_rate_kpi card 640 0 140 100
New-Visual executive_overview etl_success_rate card 800 0 140 100
New-Visual executive_overview revenue_trend lineChart 0 120 300 280
New-Visual executive_overview loan_trend lineChart 320 120 300 280
New-Visual executive_overview churn_trend lineChart 640 120 300 280
New-Visual executive_overview fraud_trend lineChart 0 420 300 280
New-Visual executive_overview risk_distribution donutChart 320 420 300 280

Set-Card executive_overview total_customers fact_churn TotalCustomers
Set-Card executive_overview total_loans fact_loan TotalLoans
Set-Card executive_overview total_revenue fact_churn TotalRevenue
Set-Card executive_overview fraud_rate fact_transaction FraudRate
Set-Card executive_overview churn_rate_kpi fact_churn ChurnRate
Set-Card executive_overview etl_success_rate etl_metadata ETLSuccessRate
Set-Chart executive_overview revenue_trend fact_churn contract_type fact_churn TotalRevenue
Set-Chart executive_overview loan_trend fact_loan loan_status fact_loan LoanVolume
Set-Chart executive_overview churn_trend fact_churn tenure_group fact_churn ChurnRate
Set-Chart executive_overview fraud_trend fact_transaction device_type fact_transaction FraudRate
Set-Chart executive_overview risk_distribution fact_loan grade fact_loan TotalLoans

# ========== FRAUD ANALYTICS ==========
Write-Host "=== Fraud Analytics ==="
New-Visual fraud_analytics total_fraud_cases card 0 0 140 100
New-Visual fraud_analytics fraud_percentage card 160 0 140 100
New-Visual fraud_analytics avg_txn_amt card 320 0 140 100
New-Visual fraud_analytics fraud_by_device barChart 0 120 300 280
New-Visual fraud_analytics fraud_by_card barChart 320 120 300 280
New-Visual fraud_analytics fraud_trend lineChart 640 120 300 280
New-Visual fraud_analytics top_fraud_txns tableEx 0 420 640 280

Set-Card fraud_analytics total_fraud_cases fact_transaction FraudCases
Set-Card fraud_analytics fraud_percentage fact_transaction FraudRate
Set-Card fraud_analytics avg_txn_amt fact_transaction AvgTransactionAmount
Set-Chart fraud_analytics fraud_by_device fact_transaction device_type fact_transaction FraudCases
Set-Chart fraud_analytics fraud_by_card fact_transaction card_type fact_transaction FraudCases
Set-Chart fraud_analytics fraud_trend fact_transaction device_type fact_transaction FraudCases

# ========== LENDING ANALYTICS ==========
Write-Host "=== Lending Analytics ==="
New-Visual lending_analytics total_loans_kpi card 0 0 140 100
New-Visual lending_analytics avg_loan_amt card 160 0 140 100
New-Visual lending_analytics avg_interest card 320 0 140 100
New-Visual lending_analytics default_rate card 480 0 140 100
New-Visual lending_analytics loans_by_grade barChart 0 120 300 280
New-Visual lending_analytics loan_status_breakdown donutChart 320 120 300 280
New-Visual lending_analytics default_by_purpose barChart 640 120 300 280
New-Visual lending_analytics risk_distribution donutChart 0 420 300 280
New-Visual lending_analytics grade_purpose_matrix tableEx 320 420 300 280

Set-Card lending_analytics total_loans_kpi fact_loan TotalLoans
Set-Card lending_analytics avg_loan_amt fact_loan AvgLoanAmount
Set-Card lending_analytics avg_interest fact_loan AvgInterestRate
Set-Card lending_analytics default_rate fact_loan DefaultRate
Set-Chart lending_analytics loans_by_grade fact_loan grade fact_loan TotalLoans
Set-Chart lending_analytics loan_status_breakdown fact_loan loan_status fact_loan TotalLoans
Set-Chart lending_analytics default_by_purpose fact_loan purpose fact_loan DefaultRate
Set-Chart lending_analytics risk_distribution fact_loan home_ownership fact_loan LoanVolume

# ========== CUSTOMER CHURN ==========
Write-Host "=== Customer Churn ==="
New-Visual customer_churn total_customers_kpi card 0 0 140 100
New-Visual customer_churn churn_rate_main card 160 0 140 100
New-Visual customer_churn avg_monthly_charges card 320 0 140 100
New-Visual customer_churn avg_tenure card 480 0 140 100
New-Visual customer_churn churn_by_contract barChart 0 120 300 280
New-Visual customer_churn churn_by_internet barChart 320 120 300 280
New-Visual customer_churn churn_by_tenure_group barChart 0 420 300 280
New-Visual customer_churn payment_method_dist donutChart 320 420 300 280
New-Visual customer_churn churn_customer_table tableEx 640 120 300 580

Set-Card customer_churn total_customers_kpi fact_churn TotalCustomers
Set-Card customer_churn churn_rate_main fact_churn ChurnRate
Set-Card customer_churn avg_monthly_charges fact_churn AvgMonthlyCharges
Set-Card customer_churn avg_tenure fact_churn AvgTenure
Set-Chart customer_churn churn_by_contract fact_churn contract_type fact_churn ChurnedCustomers
Set-Chart customer_churn churn_by_internet fact_churn internet_service fact_churn ChurnedCustomers
Set-Chart customer_churn churn_by_tenure_group fact_churn tenure_group fact_churn ChurnRate
Set-Chart customer_churn payment_method_dist fact_churn payment_method fact_churn TotalCustomers

# ========== ETL MONITORING ==========
Write-Host "=== ETL Monitoring ==="
New-Visual etl_monitoring total_runs card 0 0 140 100
New-Visual etl_monitoring failed_runs card 160 0 140 100
New-Visual etl_monitoring etl_success_rate card 320 0 140 100
New-Visual etl_monitoring records_processed card 480 0 140 100
New-Visual etl_monitoring run_duration_chart barChart 0 120 300 280
New-Visual etl_monitoring records_trend lineChart 320 120 300 280
New-Visual etl_monitoring etl_status_table tableEx 0 420 640 280

Set-Card etl_monitoring total_runs etl_metadata TotalRuns
Set-Card etl_monitoring failed_runs etl_metadata FailedRuns
Set-Card etl_monitoring etl_success_rate etl_metadata ETLSuccessRate
Set-Card etl_monitoring records_processed etl_metadata TotalRecordsProcessed
Set-Chart etl_monitoring run_duration_chart etl_metadata task_id etl_metadata AvgRunDurationMinutes
Set-Chart etl_monitoring records_trend etl_metadata dag_id etl_metadata TotalRecordsProcessed

# ========== CUSTOMER DETAIL ==========
Write-Host "=== Customer Detail ==="
New-Visual customer_detail customer_profile_card card 0 0 200 100
New-Visual customer_detail customer_churn_status card 220 0 200 100
New-Visual customer_detail customer_loans tableEx 0 120 300 280
New-Visual customer_detail customer_transactions tableEx 320 120 300 280

Set-Card customer_detail customer_profile_card fact_churn TotalCustomers
Set-Card customer_detail customer_churn_status fact_churn ChurnRate

Write-Host "`nCreated 45 visuals. Run validation next."
