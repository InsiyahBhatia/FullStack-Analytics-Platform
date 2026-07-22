"""
Post-Overhaul Fixes for FinSight Dashboard
===========================================
Fixes review issues:
1. Increase branding title width from 300px to 400px
2. Remove redundant page_title_header visuals (covered by navigator)
3. Rename old scripts to .bak to prevent accidental runs
"""

import json
import os
import shutil
import glob

# Paths
PROJECT_ROOT = r"D:\FinSight\FinSight"
DEFINITION_DIR = os.path.join(PROJECT_ROOT, "FinSight.Report", "definition")
PAGES_DIR = os.path.join(DEFINITION_DIR, "pages")

# =============================================================================
# FIX 1: Increase branding title width to 400px
# =============================================================================
print("=" * 60)
print("FIX 1: Increasing branding title width to 400px")
print("=" * 60)

branding_files = glob.glob(os.path.join(PAGES_DIR, "*", "visuals", "branding_title", "visual.json"))
for bf in branding_files:
    with open(bf, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Increase width from 300 to 400
    data["position"]["width"] = 400
    # Also widen the branding title to accommodate the text
    data["position"]["height"] = 48
    
    with open(bf, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    page_name = os.path.basename(os.path.dirname(os.path.dirname(bf)))
    print("  [OK] Increased branding width for: " + page_name)

# =============================================================================
# FIX 2: Remove redundant page_title_header visuals
# =============================================================================
print("")
print("=" * 60)
print("FIX 2: Removing redundant page_title_header visuals")
print("=" * 60)

for page_name in ["executive_overview", "lending_analytics", "fraud_analytics", 
                   "customer_churn", "customer_detail", "etl_monitoring",
                   "ml_monitoring", "real_time_monitoring"]:
    pth_dir = os.path.join(PAGES_DIR, page_name, "visuals", "page_title_header")
    if os.path.exists(pth_dir):
        shutil.rmtree(pth_dir)
        print("  [OK] Removed page_title_header from: " + page_name)
    else:
        print("  [--] Already removed (or never existed): " + page_name)

# =============================================================================
# FIX 3: Rename old scripts to .bak to prevent accidental runs
# =============================================================================
print("")
print("=" * 60)
print("FIX 3: Renaming old scripts to .bak extension")
print("=" * 60)

old_scripts = [
    "apply_polish.py",
    "global_ui_overhaul.py", 
    "revert_colors.py",
    "update_backgrounds.py"
]

for script in old_scripts:
    src = os.path.join(DEFINITION_DIR, script)
    dst = os.path.join(DEFINITION_DIR, script + ".bak")
    if os.path.exists(src):
        shutil.move(src, dst)
        print("  [OK] Renamed " + script + " -> " + script + ".bak")
    else:
        print("  [--] Not found (already renamed?): " + script)

# Also rename scripts in SemanticModel
semantic_scripts = [
    "fix_columns.py",
    "fix_datatype.py",
    "fix_indentation.py",
    "fix_indentation2.py",
    "fix_rankx.py",
    "fix_tmdl.py",
    "fix_variant.py"
]

semantic_dir = os.path.join(PROJECT_ROOT, "FinSight.SemanticModel", "definition")
for script in semantic_scripts:
    src = os.path.join(semantic_dir, script)
    dst = os.path.join(semantic_dir, script + ".bak")
    if os.path.exists(src):
        shutil.move(src, dst)
        print("  [OK] Renamed " + script + " -> " + script + ".bak")

print("")
print("=" * 60)
print("FIXES COMPLETE")
print("=" * 60)
print("")
print("Summary:")
print("  * Branding title width increased to 400px")
print("  * Redundant page titles removed")
print("  * " + str(len(old_scripts) + len(semantic_scripts)) + " old scripts renamed to .bak")
