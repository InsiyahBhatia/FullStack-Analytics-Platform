"""
FinSight Light Mode Professional Transformation
================================================
Transforms from dark theme to professional light theme with:
- Clean white/slate background palette
- Improved FinSight header branding with deep navy header bar
- Better page navigation UI with consistent styling
- Professional card visuals with subtle shadows
"""

import json
import os
import shutil
import glob

PROJECT_ROOT = r"D:\FinSight\FinSight"
DEFINITION_DIR = os.path.join(PROJECT_ROOT, "FinSight.Report", "definition")
PAGES_DIR = os.path.join(DEFINITION_DIR, "pages")
STATIC_RESOURCES = os.path.join(PROJECT_ROOT, "FinSight.Report", "StaticResources", "RegisteredResources")
REPORT_JSON = os.path.join(DEFINITION_DIR, "report.json")

# =============================================================================
# STEP 1: Create professional light theme JSON
# =============================================================================
print("=" * 60)
print("STEP 1: Creating professional light theme")
print("=" * 60)

light_theme = {
    "name": "FinSight Light",
    "dataColors": [
        "#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED",
        "#0891B2", "#DB2777", "#65A30D", "#0D9488", "#4F46E5",
        "#EA580C", "#9333EA"
    ],
    "background": "#FFFFFF",
    "foreground": "#1F2937",
    "foregroundNeutralSecondary": "#6B7280",
    "foregroundNeutralTertiary": "#9CA3AF",
    "backgroundLight": "#F3F4F6",
    "backgroundNeutral": "#E5E7EB",
    "tableAccent": "#2563EB",
    "good": "#059669",
    "neutral": "#D97706",
    "bad": "#DC2626",
    "maximum": "#2563EB",
    "center": "#D97706",
    "minimum": "#DBEAFE",
    "null": "#EA580C",
    "hyperlink": "#2563EB",
    "visitedHyperlink": "#1D4ED8",
    "textClasses": {
        "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": "#1F2937"},
        "title": {"fontSize": 14, "fontFace": "Segoe UI Semibold", "color": "#1F2937"},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#374151"},
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#6B7280"}
    },
    "visualStyles": {},
    "page": {
        "background": [{"color": {"solid": {"color": "#F5F7FA"}}, "transparency": 0}],
        "outspace": [{"color": {"solid": {"color": "#F5F7FA"}}}],
        "outspacePane": [{
            "backgroundColor": {"solid": {"color": "#FFFFFF"}},
            "transparency": 0,
            "foregroundColor": {"solid": {"color": "#374151"}},
            "titleSize": 16,
            "searchTextSize": 13,
            "headerSize": 14,
            "fontFamily": "Segoe UI",
            "border": {"solid": {"color": "#E5E7EB"}},
            "borderColor": {"solid": {"color": "#E5E7EB"}},
            "checkboxAndApplyColor": {"solid": {"color": "#2563EB"}},
            "inputBoxColor": {"solid": {"color": "#FFFFFF"}},
            "width": 320
        }]
    }
}

# Add visualStyles
vs_all = {
    "background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0, "show": True}],
    "border": [{"show": True, "color": {"solid": {"color": "#E5E7EB"}}, "radius": 6, "width": 1}],
    "dropShadow": [{"show": True, "preset": "Low", "color": {"solid": {"color": "#000000"}}, "transparency": 80, "shadowBlur": 8, "shadowSpread": 0, "angle": 90, "shadowDistance": 2}],
    "title": [{"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True, "alignment": "Left", "background": {"solid": {"color": "#FFFFFF"}}, "show": True, "titleWrap": True}],
    "visualHeader": [{"show": True, "background": {"solid": {"color": "#FFFFFF"}}, "border": {"solid": {"color": "#E5E7EB"}}, "transparency": 0, "foreground": {"solid": {"color": "#374151"}}}],
    "outspacePane": [{"backgroundColor": {"solid": {"color": "#FFFFFF"}}, "transparency": 0, "border": True, "borderColor": {"solid": {"color": "#E5E7EB"}}}]
}

light_theme["visualStyles"]["*"] = {"*": vs_all}
light_theme["visualStyles"]["cardVisual"] = {
    "*": {
        "value": [{"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 28, "fontFamily": "Segoe UI", "bold": True}],
        "label": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 12, "fontFamily": "Segoe UI"}],
        "accentBar": [{"show": True, "color": {"solid": {"color": "#2563EB"}}, "width": 4, "position": "Left"}]
    }
}
light_theme["visualStyles"]["lineChart"] = {
    "*": {
        "line": [{"width": 2, "roundDot": True, "dotSize": 6}],
        "dataPoint": [{"show": True, "color": {"solid": {"color": "#2563EB"}}}],
        "categoryAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}}],
        "valueAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}}],
        "legend": [{"show": True, "position": "Top", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}],
        "title": [{"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}]
    }
}
light_theme["visualStyles"]["barChart"] = {
    "*": {
        "dataPoint": [{"color": {"solid": {"color": "#2563EB"}}}],
        "categoryAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": False}}],
        "valueAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}}],
        "legend": [{"show": False, "position": "Top"}],
        "dataLabels": [{"show": True, "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 10, "fontFamily": "Segoe UI", "labelPosition": "OutsideEnd", "displayUnits": 0, "precision": 1}]
    }
}
light_theme["visualStyles"]["columnChart"] = {
    "*": {
        "dataPoint": [{"color": {"solid": {"color": "#2563EB"}}}],
        "categoryAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": False}}],
        "valueAxis": [{"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}}],
        "legend": [{"show": False, "position": "Top"}]
    }
}
light_theme["visualStyles"]["donutChart"] = {
    "*": {
        "labels": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "labelStyle": "CategoryDataValue", "labelDisplayUnits": 0, "precision": 1, "position": "OutsideEnd"}],
        "legend": [{"show": True, "position": "Right", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}],
        "title": [{"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}]
    }
}
light_theme["visualStyles"]["pieChart"] = {
    "*": {
        "labels": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "labelStyle": "Data value, percent of total", "labelDisplayUnits": 0, "precision": 1}],
        "legend": [{"show": True, "position": "RightCenter", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}]
    }
}
light_theme["visualStyles"]["tableEx"] = {
    "*": {
        "grid": [{"verticalGridlines": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}, "horizontalGridlines": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}, "outline": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}}],
        "columnHeaders": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#F9FAFB"}}, "outline": "BottomOnly", "outlineColor": {"solid": {"color": "#E5E7EB"}}}],
        "values": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "alternatingRowBackground": {"solid": {"color": "#F9FAFB"}}}],
        "total": [{"show": True, "fontColor": {"solid": {"color": "#2563EB"}}, "fontSize": 11, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#F9FAFB"}}}]
    }
}
light_theme["visualStyles"]["slicer"] = {
    "*": {
        "slicerHeader": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 12, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#FFFFFF"}}, "outline": "Frame", "outlineColor": {"solid": {"color": "#E5E7EB"}}}],
        "slicerText": [{"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}]
    }
}
light_theme["visualStyles"]["treemap"] = {
    "*": {
        "labels": [{"show": True, "fontColor": {"solid": {"color": "#FFFFFF"}}, "fontSize": 11, "fontFamily": "Segoe UI"}],
        "title": [{"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}]
    }
}
light_theme["visualStyles"]["textbox"] = {"*": {"general": [{"verticalAlignment": "Middle"}]}}
light_theme["visualStyles"]["shape"] = {"*": {"background": [{"show": False}], "general": [{"keepLayerOrder": True}], "visualHeader": [{"show": False}]}}
light_theme["visualStyles"]["pageNavigator"] = {"*": {"background": [{"show": False}], "visualHeader": [{"show": False}]}}
light_theme["visualStyles"]["image"] = {"*": {"background": [{"show": False}], "visualHeader": [{"show": False}]}}

# Write the light theme
for dest in [STATIC_RESOURCES, os.path.join(DEFINITION_DIR, "RegisteredResources")]:
    fp = os.path.join(dest, "finsight_light_theme.json")
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(light_theme, f, indent=2)
    print("  [OK] Wrote " + fp)

# =============================================================================
# STEP 2: Update report.json to use light theme
# =============================================================================
print("")
print("=" * 60)
print("STEP 2: Updating report.json to use light theme")
print("=" * 60)

with open(REPORT_JSON, 'r', encoding='utf-8') as f:
    report = json.load(f)

report["themeCollection"]["customTheme"] = {
    "name": "finsight_light_theme.json",
    "reportVersionAtImport": {"visual": "2.10.0", "report": "3.4.0", "page": "2.3.1"},
    "type": "RegisteredResources"
}

for pkg in report["resourcePackages"]:
    if pkg["name"] == "RegisteredResources":
        pkg["items"] = [{"name": "finsight_light_theme.json", "path": "finsight_light_theme.json", "type": "CustomTheme"}]

with open(REPORT_JSON, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
print("  [OK] Updated report.json")

# =============================================================================
# STEP 3: Update page backgrounds to light
# =============================================================================
print("")
print("=" * 60)
print("STEP 3: Updating page backgrounds to light")
print("=" * 60)

PAGE_BG = "#F5F7FA"
page_files = glob.glob(os.path.join(PAGES_DIR, "*", "page.json"))

for page_file in sorted(page_files):
    with open(page_file, 'r', encoding='utf-8') as f:
        page_data = json.load(f)
    page_name = os.path.basename(os.path.dirname(page_file))

    if "objects" not in page_data:
        page_data["objects"] = {}

    page_data["objects"]["background"] = [{
        "properties": {
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + PAGE_BG + "'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}}
        }
    }]
    page_data["objects"]["outspace"] = [{
        "properties": {
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + PAGE_BG + "'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}}
        }
    }]
    page_data["displayOption"] = "FitToPage"
    page_data["height"] = 800
    page_data["width"] = 1280

    with open(page_file, 'w', encoding='utf-8') as f:
        json.dump(page_data, f, indent=2)
    print("  [OK] Updated page: " + page_name)

# =============================================================================
# STEP 4: Update header and navigation
# =============================================================================
print("")
print("=" * 60)
print("STEP 4: Updating headers with navy branding + nav")
print("=" * 60)

NAVY = "#1E3A5F"
BLUE = "#2563EB"

# Build header_bg config as JSON string to avoid Python bracket issues
header_bg_template = json.loads("""{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "header_bg",
  "position": {"x": 0, "y": 0, "z": 1000, "height": 72, "width": 1280, "tabOrder": 1000},
  "visual": {
    "visualType": "shape",
    "objects": {
      "fill": [{"properties": {"fillColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'NAVY'"}}}}}, "transparency": {"expr": {"Literal": {"Value": "0D"}}}}}],
      "shape": [{"properties": {"tileShape": {"expr": {"Literal": {"Value": "'rectangle'"}}}}}],
      "text": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}, "text": {"expr": {"Literal": {"Value": "''"}}}, "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}}, "fontSize": {"expr": {"Literal": {"Value": "0D"}}}}}]
    }
  }
}""")

accent_line = json.loads("""{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "header_accent_line",
  "position": {"x": 0, "y": 72, "z": 999, "height": 3, "width": 1280, "tabOrder": 999},
  "visual": {
    "visualType": "shape",
    "objects": {
      "fill": [{"properties": {"fillColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'BLUE'"}}}}}, "transparency": {"expr": {"Literal": {"Value": "0D"}}}}}],
      "shape": [{"properties": {"tileShape": {"expr": {"Literal": {"Value": "'rectangle'"}}}}}]
    }
  }
}""")

branding_title = json.loads("""{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "branding_title",
  "position": {"x": 24, "y": 14, "z": 1001, "height": 44, "width": 420, "tabOrder": 1001},
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [{
        "properties": {
          "paragraphs": [{
            "textRuns": [
              {"textStyle": {"fontFamily": "Segoe UI", "fontSize": 22, "fontWeight": 700, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}}}, "value": "FinSight"},
              {"textStyle": {"fontFamily": "Segoe UI", "fontSize": 22, "fontWeight": 200, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#93C5FD'"}}}}}}, "value": " | "},
              {"textStyle": {"fontFamily": "Segoe UI", "fontSize": 14, "fontWeight": 400, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#BFDBFE'"}}}}}}, "value": "Financial Intelligence Platform"}
            ],
            "horizontalAlignment": "Left"
          }],
          "verticalAlignment": "Middle"
        }
      }]
    },
    "visualContainerObjects": {
      "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
      "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
      "visualHeader": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
    }
  }
}""")

page_nav = json.loads("""{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
  "name": "page_navigator",
  "position": {"x": 460, "y": 16, "z": 13000, "height": 40, "width": 560, "tabOrder": 13000},
  "visual": {
    "visualType": "pageNavigator",
    "drillFilterOtherVisuals": true,
    "visualContainerObjects": {
      "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}, "transparency": {"expr": {"Literal": {"Value": "100D"}}}}],
      "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
    }
  }
}""")

# Apply color substitutions
header_bg_str = json.dumps(header_bg_template).replace("'NAVY'", "'" + NAVY + "'")
header_bg = json.loads(header_bg_str)
accent_str = json.dumps(accent_line).replace("'BLUE'", "'" + BLUE + "'")
accent_line = json.loads(accent_str)

PAGE_DISPLAY_NAMES = {
    "executive_overview": "Executive Overview",
    "lending_analytics": "Lending Analytics",
    "fraud_analytics": "Fraud Analytics",
    "customer_churn": "Customer Churn",
    "customer_detail": "Customer Detail",
    "etl_monitoring": "ETL Monitoring",
    "ml_monitoring": "ML Monitoring",
    "real_time_monitoring": "Real-Time Monitoring"
}

for page_name, display_name in PAGE_DISPLAY_NAMES.items():
    visuals_dir = os.path.join(PAGES_DIR, page_name, "visuals")
    os.makedirs(visuals_dir, exist_ok=True)

    # header_bg
    hdr = json.loads(json.dumps(header_bg))
    hdr["visual"]["objects"]["text"][0]["properties"]["text"]["expr"]["Literal"]["Value"] = "'" + display_name + "'"
    with open(os.path.join(visuals_dir, "header_bg", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(hdr, f, indent=2)

    # accent line
    with open(os.path.join(visuals_dir, "header_accent_line", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(accent_line, f, indent=2)

    # branding title
    with open(os.path.join(visuals_dir, "branding_title", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(branding_title, f, indent=2)

    # page navigator
    with open(os.path.join(visuals_dir, "page_navigator", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(page_nav, f, indent=2)

    print("  [OK] Updated " + page_name)

# =============================================================================
# STEP 5: Remove old hash-named navigators
# =============================================================================
print("")
print("=" * 60)
print("STEP 5: Removing old hash-named page navigators")
print("=" * 60)

for root, dirs, _ in os.walk(PAGES_DIR):
    for d in dirs:
        vf = os.path.join(root, d, "visual.json")
        if os.path.exists(vf):
            try:
                with open(vf, 'r', encoding='utf-8') as f:
                    vdata = json.load(f)
                vt = vdata.get("visual", {}).get("visualType", "")
                if vt == "pageNavigator" and d not in ("page_navigator",):
                    shutil.rmtree(os.path.join(root, d))
                    print("  [OK] Removed old navigator: " + d)
            except Exception:
                pass

# =============================================================================
# STEP 6: Update all visual backgrounds/text for light mode
# =============================================================================
print("")
print("=" * 60)
print("STEP 6: Updating visuals for light mode")
print("=" * 60)

LIGHT_BG = "#FFFFFF"
LIGHT_BORDER = "#E5E7EB"
TEXT_DARK = "#1F2937"
TEXT_MUTED = "#6B7280"
TITLE_COLOR = "#1F2937"
ACCENT = "#2563EB"
SHADOW = "#000000"

visual_files = glob.glob(os.path.join(PAGES_DIR, "*", "visuals", "*", "visual.json"))
skip_list = ("header_bg", "header_accent_line", "branding_title", "page_navigator")
updated = 0

for vf in sorted(visual_files):
    skip = any(s in vf for s in skip_list)
    if skip:
        continue

    with open(vf, 'r', encoding='utf-8') as f:
        vd = json.load(f)

    mod = False
    vt = vd.get("visual", {}).get("visualType", "")

    if "visual" not in vd:
        continue
    if "visualContainerObjects" not in vd["visual"]:
        vd["visual"]["visualContainerObjects"] = {}
    vco = vd["visual"]["visualContainerObjects"]

    # background
    if "background" in vco:
        for bg in vco["background"]:
            p = bg.get("properties", {})
            p["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BG + "'"}}}}}
            p["show"] = {"expr": {"Literal": {"Value": "true"}}}
            p["transparency"] = {"expr": {"Literal": {"Value": "0D"}}}
            mod = True
    else:
        vco["background"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BG + "'"}}}}}, "transparency": {"expr": {"Literal": {"Value": "0D"}}}}}]
        mod = True

    # border
    if "border" in vco:
        for b in vco["border"]:
            p = b.get("properties", {})
            p["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BORDER + "'"}}}}}
            p["show"] = {"expr": {"Literal": {"Value": "true"}}}
            p["radius"] = {"expr": {"Literal": {"Value": "6D"}}}
            mod = True

    # shadow
    if "dropShadow" in vco:
        for s in vco["dropShadow"]:
            p = s.get("properties", {})
            p["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + SHADOW + "'"}}}}}
            p["transparency"] = {"expr": {"Literal": {"Value": "85D"}}}
            mod = True

    # title
    if "title" in vco:
        for t in vco["title"]:
            p = t.get("properties", {})
            if "fontColor" in p:
                p["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TITLE_COLOR + "'"}}}}}
                mod = True
            if "background" in p:
                p["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BG + "'"}}}}}
                mod = True

    # visualHeader
    if "visualHeader" in vco:
        for vh in vco["visualHeader"]:
            p = vh.get("properties", {})
            if "background" in p:
                p["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BG + "'"}}}}}
                mod = True
            if "border" in p:
                p["border"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + LIGHT_BORDER + "'"}}}}}
                mod = True
            if "foreground" in p:
                p["foreground"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_DARK + "'"}}}}}
                mod = True

    # card visuals
    if vt in ("cardVisual", "card"):
        objs = vd.get("visual", {}).get("objects", {})
        for val in objs.get("value", []):
            p = val.get("properties", {})
            if "fontColor" in p:
                p["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_DARK + "'"}}}}}
                mod = True
        for accent in objs.get("accentBar", []):
            p = accent.get("properties", {})
            if "color" in p:
                p["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + ACCENT + "'"}}}}}
                mod = True
        for label in objs.get("label", []):
            p = label.get("properties", {})
            if "fontColor" in p:
                p["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_MUTED + "'"}}}}}
                mod = True

    if mod:
        updated += 1
        with open(vf, 'w', encoding='utf-8') as f:
            json.dump(vd, f, indent=2)

print("  [OK] Updated " + str(updated) + " visuals for light mode")

print("")
print("=" * 60)
print("LIGHT MODE TRANSFORMATION COMPLETE")
print("=" * 60)
print("")
print("Summary:")
print("  * Theme: finsight_light_theme.json (professional light theme)")
print("  * Background: Clean light gray (#F5F7FA) canvas")
print("  * Header: Deep navy (#1E3A5F) with FinSight branding")
print("  * Navigation: Centered page navigator in header bar")
print("  * Cards: White (#FFFFFF) with subtle shadows")
print("  * Borders: Light gray (#E5E7EB) with 6px rounded corners")
print("  * Text: Dark slate (#1F2937) for readability")
print("  * Visuals: " + str(updated) + " updated for light mode")
