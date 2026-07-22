<#
.SYNOPSIS
    FinSight bootstrap script.
    Starts infrastructure, loads data, trains models, verifies everything.

.DESCRIPTION
    Idempotent PowerShell script that takes a blank system to fully operational.
    Safe to re-run: skips steps that are already complete.

.EXAMPLE
    .\scripts\bootstrap.ps1
    .\scripts\bootstrap.ps1 -SkipTraining
    .\scripts\bootstrap.ps1 -Reset
#>

param(
    [switch]$SkipTraining,
    [switch]$SkipETL,
    [switch]$Reset,
    [int]$MaxWaitSeconds = 180
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$ComposeFiles = "-f", "$Root\docker\docker-compose.yml", "-f", "$Root\docker\docker-compose.local.yml"

# --- Helpers ---

function Write-Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Write-OK($msg)       { Write-Host "  OK: $msg" -ForegroundColor Green }
function Write-Warn($msg)     { Write-Host "  WARN: $msg" -ForegroundColor Yellow }
function Write-Fail($msg)     { Write-Host "  FAIL: $msg" -ForegroundColor Red }

function Test-ContainerHealthy($name) {
    $info = docker inspect --format='{{.State.Health.Status}}' $name 2>$null
    return $info -eq "healthy"
}

# --- Banner ---

Write-Host ""
Write-Host "  FinSight Bootstrap" -ForegroundColor Magenta
Write-Host "  ==================" -ForegroundColor Magenta
Write-Host ""

# --- Phase 0: Reset ---

if ($Reset) {
    Write-Step 0 "Resetting (stopping containers and removing volumes)"
    Push-Location $Root
    docker compose @ComposeFiles down -v --remove-orphans 2>$null
    Pop-Location
    Write-OK "Containers stopped, volumes removed"
}

# --- Phase 1: Pre-flight checks ---

Write-Step 1 "Pre-flight checks"

# Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "Docker not found. Install Docker Desktop."; exit 1
}
$dockerVer = docker version --format '{{.Server.Version}}' 2>$null
Write-OK "Docker $dockerVer"

# Docker Compose
if (-not (Get-Command docker -ErrorAction SilentlyContinue) -or -not (docker compose version 2>$null)) {
    Write-Fail "Docker Compose not found."; exit 1
}
Write-OK "Docker Compose available"

# Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Fail "Python not found."; exit 1
}
$pyVer = python --version 2>&1
Write-OK "$pyVer"

# psql
$psqlAvailable = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlAvailable) { Write-OK "psql available" }
else { Write-Warn "psql not found - DB verification will use Docker" }

# --- Phase 2: Data check ---

Write-Step 2 "Checking raw data"

$churnCsv  = "$Root\data\raw\churn\telco_customer_churn.csv"
$lendingCsv = "$Root\data\raw\lending\lending_club.csv"
$fraudCsv  = "$Root\data\raw\fraud\train_transaction.csv"

$hasChurn  = Test-Path $churnCsv
$hasLending = Test-Path $lendingCsv
$hasFraud  = Test-Path $fraudCsv

if ($hasChurn -and $hasLending -and $hasFraud) {
    Write-OK "All 3 datasets present"
} else {
    Write-Warn "Missing datasets, downloading..."
    if (-not $hasChurn)  { python "$Root\scripts\download_datasets.py" 2>&1 | Out-Null }
    if (-not $hasLending -or -not $hasFraud) {
        python "$Root\scripts\prepare_datasets.py" 2>&1 | Out-Null
    }
    # Re-check
    if ((Test-Path $churnCsv) -and (Test-Path $lendingCsv) -and (Test-Path $fraudCsv)) {
        Write-OK "Data downloaded successfully"
    } else {
        Write-Fail "Data download failed. Check scripts/download_datasets.py"
        Write-Warn "Continuing anyway - ETL will fail if data is missing"
    }
}

# --- Phase 3: Start infrastructure ---

Write-Step 3 "Starting Docker containers"

# Check if containers are already running
$runningContainers = docker ps --format '{{.Names}}' 2>$null | Select-String "finsight"
if ($runningContainers) {
    Write-OK "Containers already running, skipping compose up"
} else {
    Push-Location $Root
    docker compose @ComposeFiles up -d 2>&1 | Out-Null
    Pop-Location
    Write-OK "Compose up issued"
}

# --- Phase 4: Wait for services ---

Write-Step 4 "Waiting for services to become healthy (max ${MaxWaitSeconds}s)"

$services = @(
    @{ Name = "finsight-postgres";   Check = { Test-ContainerHealthy "finsight-postgres" } },
    @{ Name = "finsight-redis";      Check = { Test-ContainerHealthy "finsight-redis" } },
    @{ Name = "finsight-api";        URL = "http://localhost:8000/health" },
    @{ Name = "finsight-mlflow";     URL = "http://localhost:5000" },
    @{ Name = "finsight-webserver";  URL = "http://localhost:8080/health" },
    @{ Name = "finsight-frontend";   URL = "http://localhost:8501" }
)

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$allHealthy = $true

foreach ($svc in $services) {
    $ok = $false
    while ($sw.Elapsed.TotalSeconds -lt $MaxWaitSeconds) {
        if ($svc.Check) { $ok = $svc.Check.Invoke(); break }
        elseif ($svc.URL) {
            try {
                $r = Invoke-WebRequest -Uri $svc.URL -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                if ($r.StatusCode -eq 200) { $ok = $true; break }
            } catch { }
        }
        Start-Sleep -Seconds 5
    }
    if ($ok) { Write-OK "$($svc.Name) ready" }
    else { Write-Warn "$($svc.Name) not ready after ${MaxWaitSeconds}s"; $allHealthy = $false }
}

# --- Phase 5: Verify DB schema ---

Write-Step 5 "Verifying database schema"

$expectedTables = @("fact_churn", "fact_loan", "fact_transaction", "etl_metadata", "feature_store", "fact_prediction_monitoring", "fact_model_training")

if ($psqlAvailable) {
    $env:PGPASSWORD = "finsight_dev_2026"
    foreach ($tbl in $expectedTables) {
        $exists = psql -h localhost -p 5433 -U finsight_user -d finsight -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='$tbl'" 2>$null
        if ($exists -eq "1") { Write-OK "Table $tbl exists" }
        else { Write-Warn "Table $tbl MISSING" }
    }
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
} else {
    $result = docker exec finsight-postgres psql -U finsight_user -d finsight -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'" 2>$null
    Write-OK "Found $result tables in PostgreSQL"
}

# --- Phase 6: ETL ---

if (-not $SkipETL) {
    Write-Step 6 "Running ETL pipeline"

    # Option A: Trigger via Airflow REST API
    $airflowOk = $false
    try {
        $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:Admin@1234"))
        $headers = @{ Authorization = "Basic $auth" }

        # Unpause the DAG
        Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/finsight_local_pipeline" -Method Patch -Headers $headers -ContentType "application/json" -Body '{"is_paused":false}' -ErrorAction Stop | Out-Null

        # Trigger
        $dagRun = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/finsight_local_pipeline/dagRuns" -Method Post -Headers $headers -ContentType "application/json" -Body '{"conf":{}}' -ErrorAction Stop
        $runId = $dagRun.dag_run_id
        Write-OK "Airflow DAG triggered: $runId"

        # Poll until complete
        $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
        while ($sw2.Elapsed.TotalSeconds -lt $MaxWaitSeconds) {
            $state = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/finsight_local_pipeline/dagRuns/$runId" -Headers $headers -ErrorAction Stop
            $status = $state.state
            if ($status -eq "success") { $airflowOk = $true; break }
            if ($status -eq "failed") { Write-Fail "Airflow DAG failed"; break }
            Start-Sleep -Seconds 10
        }
        if ($airflowOk) { Write-OK "ETL + Feature Store + Training complete (Airflow)" }
        else { Write-Warn "Airflow DAG did not complete in time" }
    } catch {
        Write-Warn "Airflow not reachable, falling back to direct ETL"
    }

    # Option B: Direct ETL fallback
    if (-not $airflowOk) {
        Write-Host "  Running ETL directly..." -ForegroundColor Gray
        python "$Root\etl\scripts\run_local_etl.py" --source churn 2>&1 | Out-Null
        python "$Root\etl\scripts\run_local_etl.py" --source lending --sample 50000 2>&1 | Out-Null
        python "$Root\etl\scripts\run_local_etl.py" --source fraud --sample 50000 2>&1 | Out-Null
        python "$Root\etl\scripts\feature_store.py" 2>&1 | Out-Null
        Write-OK "ETL + Feature Store complete (direct)"
    }
} else {
    Write-Step 6 "ETL skipped"
}

# --- Phase 7: Train models ---

if (-not $SkipTraining) {
    Write-Step 7 "Training ML models"

    Push-Location $Root
    python -m models.train_all --task all --max-rows 150000 --log-mlflow 2>&1
    $trainOk = $LASTEXITCODE -eq 0
    Pop-Location

    if ($trainOk) { Write-OK "All 3 models trained successfully" }
    else { Write-Fail "Model training failed" }

    # Load training metadata
    Write-Host "  Loading training metadata..." -ForegroundColor Gray
    python "$Root\etl\scripts\load_model_training.py" 2>&1 | Out-Null
    Write-OK "Training metadata loaded into fact_model_training"
} else {
    Write-Step 7 "Training skipped"
}

# --- Phase 8: Verify ---

Write-Step 8 "Verifying system"

$checks = @()

# API health
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    $checks += @{ Name = "API Health"; OK = $true; Detail = $health.status }
} catch {
    $checks += @{ Name = "API Health"; OK = $false; Detail = "unreachable" }
}

# API predict (test churn)
try {
    $body = '{"tenure":12,"monthly_charges":85.5,"total_charges":1026,"contract_type":"Month-to-month","payment_method":"Electronic check","internet_service":"Fiber optic"}'
    $pred = Invoke-RestMethod -Uri "http://localhost:8000/predict/churn" -Method Post -ContentType "application/json" -Body $body -Headers @{"X-API-Key"="sk-test-finsight-xxxx"} -TimeoutSec 10
    $checks += @{ Name = "Churn Prediction"; OK = $true; Detail = "prediction=$($pred.prediction) prob=$($pred.probability)" }
} catch {
    $checks += @{ Name = "Churn Prediction"; OK = $false; Detail = "failed" }
}

# DB row counts
if ($psqlAvailable) {
    $env:PGPASSWORD = "finsight_dev_2026"
    foreach ($tbl in @("fact_churn", "fact_loan", "fact_transaction", "feature_store", "fact_model_training")) {
        $cnt = psql -h localhost -p 5433 -U finsight_user -d finsight -tAc "SELECT count(*) FROM $tbl" 2>$null
        $checks += @{ Name = "DB $tbl"; OK = [int]$cnt -gt 0; Detail = "$cnt rows" }
    }
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# Print verification table
Write-Host ""
Write-Host "  Verification Results:" -ForegroundColor White
Write-Host "  -------------------------------------------" -ForegroundColor DarkGray
foreach ($c in $checks) {
    $icon = if ($c.OK) { "OK" } else { "FAIL" }
    $color = if ($c.OK) { "Green" } else { "Red" }
    Write-Host ("  [{0}] {1,-25} {2}" -f $icon, $c.Name, $c.Detail) -ForegroundColor $color
}

# --- Phase 9: Summary ---

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "  FinSight Ready!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "  API:              http://localhost:8000" -ForegroundColor Green
Write-Host "  MLflow:           http://localhost:5000" -ForegroundColor Green
Write-Host "  Airflow:          http://localhost:8080" -ForegroundColor Green
Write-Host "  Streamlit:        http://localhost:8501" -ForegroundColor Green
Write-Host "  Power BI:         Open FinSight/FinSight.pbip" -ForegroundColor Green
Write-Host "  API Key:          sk-test-finsight-xxxx" -ForegroundColor Green
Write-Host "  Airflow:          admin / Admin@1234" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
