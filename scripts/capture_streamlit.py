import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("d:/FinSight/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {
        "name": "Executive summary",
        "file": "streamlit_01_executive_summary.png",
        "header": "Executive summary",
    },
    {
        "name": "Churn & retention",
        "file": "streamlit_02_churn_retention.png",
        "header": "Customer churn",
    },
    {
        "name": "Lending risk",
        "file": "streamlit_03_lending_risk.png",
        "header": "Lending:",
    },
    {
        "name": "Fraud analysis",
        "file": "streamlit_04_fraud_analysis.png",
        "header": "Fraud:",
    },
    {
        "name": "Data health",
        "file": "streamlit_05_data_health.png",
        "header": "Data health",
    },
    {
        "name": "Model performance",
        "file": "streamlit_06_model_performance.png",
        "header": "Model performance",
    },
    {
        "name": "Churn predictor",
        "file": "streamlit_07_churn_predictor.png",
        "header": "Customer churn predictor",
        "submit_button": "Predict churn",
    },
    {
        "name": "Loan default predictor",
        "file": "streamlit_08_loan_default_predictor.png",
        "header": "Loan default predictor",
        "submit_button": "Predict default",
    },
    {
        "name": "Fraud predictor",
        "file": "streamlit_09_fraud_predictor.png",
        "header": "Fraud detection predictor",
        "submit_button": "Predict fraud",
    },
    {
        "name": "Batch scoring",
        "file": "streamlit_10_batch_scoring.png",
        "header": "Batch scoring",
    },
]

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        print("Navigating to http://localhost:8501...", flush=True)
        page.goto("http://localhost:8501", wait_until="networkidle")
        time.sleep(3)

        for cfg in PAGES:
            name = cfg["name"]
            filename = cfg["file"]
            header = cfg["header"]
            print(f"Selecting page: {name}...", flush=True)

            # Click the radio item in sidebar
            radio = page.locator('[data-testid="stSidebar"] label').filter(has_text=name).first
            radio.click()
            time.sleep(1)

            # Wait for heading
            try:
                page.wait_for_selector(f':is(h1, h2, h3):has-text("{header}")', timeout=10000)
            except Exception as e:
                print(f"  Warning waiting for header: {e}", flush=True)

            time.sleep(3)  # Wait for charts & skeletons to finish rendering

            # If this is a predictor page, submit form
            if "submit_button" in cfg:
                btn_text = cfg["submit_button"]
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if btn.count() > 0:
                    print(f"  Submitting form: {btn_text}...", flush=True)
                    btn.click()
                    time.sleep(2)

            dest = SCREENSHOT_DIR / filename
            page.screenshot(path=str(dest), full_page=False)
            print(f"  Saved {dest} ({dest.stat().st_size} bytes)", flush=True)

        browser.close()
        print("Done capturing all pages successfully!", flush=True)

if __name__ == "__main__":
    capture_all()
