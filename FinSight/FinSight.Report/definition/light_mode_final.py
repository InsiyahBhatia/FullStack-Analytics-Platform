"""
FinSight Light Mode - Final Transformation
Builds all header/nav visuals using Python dicts (no embedded JSON strings)
"""

import json
import os
import shutil
import glob

ROOT = r"D:\FinSight\FinSight"
DEF = os.path.join(ROOT, "FinSight.Report", "definition")
PAGES = os.path.join(DEF, "pages")
STATIC_RES = os.path.join(ROOT, "FinSight.Report", "StaticResources", "RegisteredResources")
REPORT_JSON = os.path.join(DEF, "report.json")

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json"

# === HELPERS ===
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}

def hex_color(h):
    return {"solid": {"color": {"expr": {"Literal": {"Value": "'" + h + "'"}}}}}

# === STEP 1: Light Theme ===
print("STEP 1: Writing light theme...")
lt = {
    "name": "FinSight Light",
    "dataColors": ["#2563EB","#059669","#D97706","#DC2626","#7C3AED","#0891B2","#DB2777","#65A30D","#0D9488","#4F46E5","#EA580C","#9333EA"],
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
            "transparency": 0, "foregroundColor": {"solid": {"color": "#374151"}},
            "titleSize": 16, "searchTextSize": 13, "headerSize": 14, "fontFamily": "Segoe UI",
            "border": {"solid": {"color": "#E5E7EB"}}, "borderColor": {"solid": {"color": "#E5E7EB"}},
            "checkboxAndApplyColor": {"solid": {"color": "#2563EB"}}, "inputBoxColor": {"solid": {"color": "#FFFFFF"}},
            "width": 320
        }]
    }
}

def make_vs(entries):
    result = {}
    for key, val in entries.items():
        result[key] = [val]
    return result

base_vs = {
    "background": {"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0, "show": True},
    "border": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}, "radius": 6, "width": 1},
    "dropShadow": {"show": True, "preset": "Low", "color": {"solid": {"color": "#000000"}}, "transparency": 80, "shadowBlur": 8, "shadowSpread": 0, "angle": 90, "shadowDistance": 2},
    "title": {"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True, "alignment": "Left", "background": {"solid": {"color": "#FFFFFF"}}, "show": True, "titleWrap": True},
    "visualHeader": {"show": True, "background": {"solid": {"color": "#FFFFFF"}}, "border": {"solid": {"color": "#E5E7EB"}}, "transparency": 0, "foreground": {"solid": {"color": "#374151"}}},
    "outspacePane": {"backgroundColor": {"solid": {"color": "#FFFFFF"}}, "transparency": 0, "border": True, "borderColor": {"solid": {"color": "#E5E7EB"}}}
}
lt["visualStyles"]["*"] = {"*": make_vs(base_vs)}
lt["visualStyles"]["cardVisual"] = {"*": make_vs({
    "value": {"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 28, "fontFamily": "Segoe UI", "bold": True},
    "label": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 12, "fontFamily": "Segoe UI"},
    "accentBar": {"show": True, "color": {"solid": {"color": "#2563EB"}}, "width": 4, "position": "Left"}
})}
lt["visualStyles"]["lineChart"] = {"*": make_vs({
    "line": {"width": 2, "roundDot": True, "dotSize": 6},
    "dataPoint": {"show": True, "color": {"solid": {"color": "#2563EB"}}},
    "categoryAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}},
    "valueAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}},
    "legend": {"show": True, "position": "Top", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"},
    "title": {"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}
})}
lt["visualStyles"]["barChart"] = {"*": make_vs({
    "dataPoint": {"color": {"solid": {"color": "#2563EB"}}},
    "categoryAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": False}},
    "valueAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}},
    "legend": {"show": False, "position": "Top"},
    "dataLabels": {"show": True, "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 10, "fontFamily": "Segoe UI", "labelPosition": "OutsideEnd", "displayUnits": 0, "precision": 1}
})}
lt["visualStyles"]["columnChart"] = {"*": make_vs({
    "dataPoint": {"color": {"solid": {"color": "#2563EB"}}},
    "categoryAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": False}},
    "valueAxis": {"fontColor": {"solid": {"color": "#6B7280"}}, "fontSize": 11, "fontFamily": "Segoe UI", "gridlines": {"show": True, "color": {"solid": {"color": "#F3F4F6"}}}},
    "legend": {"show": False, "position": "Top"}
})}
lt["visualStyles"]["donutChart"] = {"*": make_vs({
    "labels": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "labelStyle": "CategoryDataValue", "labelDisplayUnits": 0, "precision": 1, "position": "OutsideEnd"},
    "legend": {"show": True, "position": "Right", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"},
    "title": {"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}
})}
lt["visualStyles"]["pieChart"] = {"*": make_vs({
    "labels": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "labelStyle": "Data value, percent of total", "labelDisplayUnits": 0, "precision": 1},
    "legend": {"show": True, "position": "RightCenter", "fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}
})}
lt["visualStyles"]["tableEx"] = {"*": make_vs({
    "grid": {"verticalGridlines": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}, "horizontalGridlines": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}, "outline": {"show": True, "color": {"solid": {"color": "#E5E7EB"}}}},
    "columnHeaders": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#F9FAFB"}}, "outline": "BottomOnly", "outlineColor": {"solid": {"color": "#E5E7EB"}}},
    "values": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI", "alternatingRowBackground": {"solid": {"color": "#F9FAFB"}}},
    "total": {"show": True, "fontColor": {"solid": {"color": "#2563EB"}}, "fontSize": 11, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#F9FAFB"}}}
})}
lt["visualStyles"]["slicer"] = {"*": make_vs({
    "slicerHeader": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 12, "fontFamily": "Segoe UI", "bold": True, "background": {"solid": {"color": "#FFFFFF"}}, "outline": "Frame", "outlineColor": {"solid": {"color": "#E5E7EB"}}},
    "slicerText": {"fontColor": {"solid": {"color": "#374151"}}, "fontSize": 11, "fontFamily": "Segoe UI"}
})}
lt["visualStyles"]["treemap"] = {"*": make_vs({
    "labels": {"show": True, "fontColor": {"solid": {"color": "#FFFFFF"}}, "fontSize": 11, "fontFamily": "Segoe UI"},
    "title": {"fontColor": {"solid": {"color": "#1F2937"}}, "fontSize": 14, "fontFamily": "Segoe UI", "bold": True}
})}
lt["visualStyles"]["textbox"] = {"*": make_vs({"general": {"verticalAlignment": "Middle"}})}
lt["visualStyles"]["shape"] = {"*": make_vs({"background": {"show": False}, "general": {"keepLayerOrder": True}, "visualHeader": {"show": False}})}
lt["visualStyles"]["pageNavigator"] = {"*": make_vs({"background": {"show": False}, "visualHeader": {"show": False}})}
lt["visualStyles"]["image"] = {"*": make_vs({"background": {"show": False}, "visualHeader": {"show": False}})}

for dest in [STATIC_RES, os.path.join(DEF, "RegisteredResources")]:
    fp = os.path.join(dest, "finsight_light_theme.json")
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(lt, f, indent=2)
    print("  [OK] Wrote light theme to " + fp)

# === STEP 2: report.json ===
print("\nSTEP 2: Updating report.json...")
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
print("  [OK] report.json updated")

# === STEP 3: Page backgrounds ===
print("\nSTEP 3: Updating page backgrounds...")
PAGE_BG = "#F5F7FA"
for page_file in glob.glob(os.path.join(PAGES, "*", "page.json")):
    with open(page_file, 'r', encoding='utf-8') as f:
        pd = json.load(f)
    pn = os.path.basename(os.path.dirname(page_file))
    if "objects" not in pd:
        pd["objects"] = {}
    pd["objects"]["background"] = [{"properties": {"color": hex_color(PAGE_BG), "transparency": lit("0D")}}]
    pd["objects"]["outspace"] = [{"properties": {"color": hex_color(PAGE_BG), "transparency": lit("0D")}}]
    pd["displayOption"] = "FitToPage"
    pd["height"] = 800
    pd["width"] = 1280
    with open(page_file, 'w', encoding='utf-8') as f:
        json.dump(pd, f, indent=2)
    print("  [OK] " + pn)

# === STEP 4: Header + Nav visuals ===
print("\nSTEP 4: Building header and navigation...")

NAVY = "#1E3A5F"
BLUE = "#2563EB"

header_bg = {
    "$schema": SCHEMA, "name": "header_bg",
    "position": {"x": 0, "y": 0, "z": 1000, "height": 72, "width": 1280, "tabOrder": 1000},
    "visual": {
        "visualType": "shape", "drillFilterOtherVisuals": True,
        "objects": {
            "fill": [{"properties": {"fillColor": hex_color(NAVY), "transparency": lit("0D")}}],
            "shape": [{"properties": {"tileShape": lit("'rectangle'")}}],
            "text": [{"properties": {"show": lit("false"), "text": lit("''"), "fontColor": hex_color("#FFFFFF"), "fontSize": lit("0D")}}]
        }
    }
}

accent_line = {
    "$schema": SCHEMA, "name": "header_accent_line",
    "position": {"x": 0, "y": 72, "z": 999, "height": 3, "width": 1280, "tabOrder": 999},
    "visual": {
        "visualType": "shape", "drillFilterOtherVisuals": True,
        "objects": {
            "fill": [{"properties": {"fillColor": hex_color(BLUE), "transparency": lit("0D")}}],
            "shape": [{"properties": {"tileShape": lit("'rectangle'")}}]
        }
    }
}

branding = {
    "$schema": SCHEMA, "name": "branding_title",
    "position": {"x": 24, "y": 14, "z": 1001, "height": 44, "width": 420, "tabOrder": 1001},
    "visual": {
        "visualType": "textbox", "drillFilterOtherVisuals": True,
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
            "background": [{"properties": {"show": lit("false")}}],
            "border": [{"properties": {"show": lit("false")}}],
            "visualHeader": [{"properties": {"show": lit("false")}}]
        }
    }
}

page_nav = {
    "$schema": SCHEMA, "name": "page_navigator",
    "position": {"x": 460, "y": 16, "z": 13000, "height": 40, "width": 560, "tabOrder": 13000},
    "visual": {
        "visualType": "pageNavigator", "drillFilterOtherVisuals": True,
        "visualContainerObjects": {
            "background": [{"properties": {"show": lit("false"), "transparency": lit("100D")}}],
            "border": [{"properties": {"show": lit("false")}}]
        }
    }
}

DISPLAY_NAMES = {
    "executive_overview": "Executive Overview",
    "lending_analytics": "Lending Analytics",
    "fraud_analytics": "Fraud Analytics",
    "customer_churn": "Customer Churn",
    "customer_detail": "Customer Detail",
    "etl_monitoring": "ETL Monitoring",
    "ml_monitoring": "ML Monitoring",
    "real_time_monitoring": "Real-Time Monitoring"
}

for pn, dn in DISPLAY_NAMES.items():
    vis_dir = os.path.join(PAGES, pn, "visuals")
    os.makedirs(os.path.join(vis_dir, "header_bg"), exist_ok=True)
    os.makedirs(os.path.join(vis_dir, "header_accent_line"), exist_ok=True)
    os.makedirs(os.path.join(vis_dir, "branding_title"), exist_ok=True)
    os.makedirs(os.path.join(vis_dir, "page_navigator"), exist_ok=True)

    # header_bg with page name
    hb = json.loads(json.dumps(header_bg))
    hb["visual"]["objects"]["text"][0]["properties"]["text"] = lit("'" + dn + "'")
    with open(os.path.join(vis_dir, "header_bg", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(hb, f, indent=2)

    with open(os.path.join(vis_dir, "header_accent_line", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(accent_line, f, indent=2)
    with open(os.path.join(vis_dir, "branding_title", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(branding, f, indent=2)
    with open(os.path.join(vis_dir, "page_navigator", "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(page_nav, f, indent=2)
    print("  [OK] " + pn)

# === STEP 5: Remove old hash-named navigators ===
print("\nSTEP 5: Removing old navigators...")
for root, dirs, _ in os.walk(PAGES):
    for d in list(dirs):
        vf = os.path.join(root, d, "visual.json")
        if os.path.exists(vf):
            try:
                with open(vf, 'r', encoding='utf-8') as f:
                    vd = json.load(f)
                if vd.get("visual", {}).get("visualType") == "pageNavigator" and d not in ("page_navigator",):
                    shutil.rmtree(os.path.join(root, d))
                    print("  [OK] Removed " + d)
            except Exception:
                pass

# === STEP 6: Update visual styling ===
print("\nSTEP 6: Updating visuals for light mode...")

WHITE = "#FFFFFF"
BORDER = "#E5E7EB"
TEXT = "#1F2937"
MUTED = "#6B7280"
ACCENT = "#2563EB"
SHADOW = "#000000"

all_vis = glob.glob(os.path.join(PAGES, "*", "visuals", "*", "visual.json"))
skip = ("header_bg", "header_accent_line", "branding_title", "page_navigator")
updated = 0

for vf in sorted(all_vis):
    if any(s in vf for s in skip):
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
            p = bg.setdefault("properties", {})
            p["color"] = hex_color(WHITE)
            p["show"] = lit("true")
            p["transparency"] = lit("0D")
            mod = True
    else:
        vco["background"] = [{"properties": {"show": lit("true"), "color": hex_color(WHITE), "transparency": lit("0D")}}]
        mod = True

    # border
    if "border" in vco:
        for b in vco["border"]:
            p = b.setdefault("properties", {})
            p["color"] = hex_color(BORDER)
            p["show"] = lit("true")
            p["radius"] = lit("6D")
            mod = True

    # shadow
    if "dropShadow" in vco:
        for s in vco["dropShadow"]:
            p = s.setdefault("properties", {})
            p["color"] = hex_color(SHADOW)
            p["transparency"] = lit("85D")
            mod = True

    # title
    if "title" in vco:
        for t in vco["title"]:
            p = t.setdefault("properties", {})
            if "fontColor" in p:
                p["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT + "'"}}}}}
                mod = True
            if "background" in p:
                p["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + WHITE + "'"}}}}}
                mod = True

    # visualHeader
    if "visualHeader" in vco:
        for vh in vco["visualHeader"]:
            p = vh.setdefault("properties", {})
            if "background" in p:
                p["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + WHITE + "'"}}}}}
                mod = True
            if "border" in p:
                p["border"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + BORDER + "'"}}}}}
                mod = True
            if "foreground" in p:
                p["foreground"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT + "'"}}}}}
                mod = True

    # card visuals
    if vt in ("cardVisual", "card"):
        objs = vd.get("visual", {}).get("objects", {})
        for val in objs.get("value", []):
            p = val.get("properties", {})
            if "fontColor" in p:
                p["fontColor"] = hex_color(TEXT)
                mod = True
        for ac in objs.get("accentBar", []):
            p = ac.get("properties", {})
            if "color" in p:
                p["color"] = hex_color(ACCENT)
                mod = True
        for lbl in objs.get("label", []):
            p = lbl.get("properties", {})
            if "fontColor" in p:
                p["fontColor"] = hex_color(MUTED)
                mod = True

    if mod:
        updated += 1
        with open(vf, 'w', encoding='utf-8') as f:
            json.dump(vd, f, indent=2)

print("  [OK] Updated " + str(updated) + " visuals")

print("\n" + "=" * 50)
print("LIGHT MODE TRANSFORMATION COMPLETE")
print("=" * 50)
