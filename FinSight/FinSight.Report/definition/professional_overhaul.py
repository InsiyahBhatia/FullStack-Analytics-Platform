"""
FinSight Professional Dashboard Overhaul
=========================================
Transforms the FinSight Power BI dashboard with:
- Professional dark theme (finsight_theme.json)
- FinSight branding with page titles in headers
- Consistent dark card styling across all visuals
- No white empty spaces
- Professional navigation preserved
"""

import json
import os
import shutil
import glob

# Paths
PROJECT_ROOT = r"D:\FinSight\FinSight"
DEFINITION_DIR = os.path.join(PROJECT_ROOT, "FinSight.Report", "definition")
PAGES_DIR = os.path.join(DEFINITION_DIR, "pages")
STATIC_RESOURCES = os.path.join(PROJECT_ROOT, "FinSight.Report", "StaticResources", "RegisteredResources")
REPORT_JSON = os.path.join(DEFINITION_DIR, "report.json")

# =============================================================================
# STEP 1: Copy finsight_theme.json to StaticResources for proper registration
# =============================================================================
print("=" * 60)
print("STEP 1: Copying finsight_theme.json to StaticResources")
print("=" * 60)

src_theme = os.path.join(DEFINITION_DIR, "RegisteredResources", "finsight_theme.json")
dst_theme = os.path.join(STATIC_RESOURCES, "finsight_theme.json")
if os.path.exists(src_theme):
    shutil.copy2(src_theme, dst_theme)
    print("  [OK] Copied to " + dst_theme)
else:
    print("  [ERR] Source theme not found at " + src_theme)

# =============================================================================
# STEP 2: Update report.json to use finsight_theme.json
# =============================================================================
print("")
print("=" * 60)
print("STEP 2: Updating report.json to use finsight_theme.json")
print("=" * 60)

with open(REPORT_JSON, 'r', encoding='utf-8') as f:
    report = json.load(f)

# Update custom theme
report["themeCollection"]["customTheme"] = {
    "name": "finsight_theme.json",
    "reportVersionAtImport": {
        "visual": "2.10.0",
        "report": "3.4.0",
        "page": "2.3.1"
    },
    "type": "RegisteredResources"
}

# Update resource packages - replace ShowMeTheNumbers with finsight_theme
for pkg in report["resourcePackages"]:
    if pkg["name"] == "RegisteredResources":
        pkg["items"] = [
            {
                "name": "finsight_theme.json",
                "path": "finsight_theme.json",
                "type": "CustomTheme"
            }
        ]

# Enable enhanced tooltips and visual styling
report["settings"]["useStylableVisualContainerHeader"] = True
report["settings"]["useEnhancedTooltips"] = True

with open(REPORT_JSON, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)

print("  [OK] Updated customTheme to finsight_theme.json")
print("  [OK] Updated RegisteredResources items")

# =============================================================================
# STEP 3: Update all page.json files with dark backgrounds
# =============================================================================
print("")
print("=" * 60)
print("STEP 3: Updating page backgrounds for dark theme")
print("=" * 60)

PAGE_BG = "#0D1117"

page_files = glob.glob(os.path.join(PAGES_DIR, "*", "page.json"))
for page_file in sorted(page_files):
    with open(page_file, 'r', encoding='utf-8') as f:
        page_data = json.load(f)
    
    page_name = os.path.basename(os.path.dirname(page_file))
    
    # Set page objects with dark background
    page_data["objects"] = {
        "background": [
            {
                "properties": {
                    "color": {
                        "solid": {
                            "color": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'" + PAGE_BG + "'"
                                    }
                                }
                            }
                        }
                    },
                    "transparency": {
                        "expr": {
                            "Literal": {
                                "Value": "0D"
                            }
                        }
                    }
                }
            }
        ],
        "outspace": [
            {
                "properties": {
                    "color": {
                        "solid": {
                            "color": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'" + PAGE_BG + "'"
                                    }
                                }
                            }
                        }
                    },
                    "transparency": {
                        "expr": {
                            "Literal": {
                                "Value": "0D"
                            }
                        }
                    }
                }
            }
        ]
    }
    
    # Ensure consistent page dimensions
    page_data["displayOption"] = "FitToPage"
    page_data["height"] = 800
    page_data["width"] = 1280
    
    with open(page_file, 'w', encoding='utf-8') as f:
        json.dump(page_data, f, indent=2)
    
    print("  [OK] Updated page: " + page_name)

# =============================================================================
# STEP 4: Update header_bg visuals with FinSight branding
# =============================================================================
print("")
print("=" * 60)
print("STEP 4: Updating header_bg visuals with FinSight branding")
print("=" * 60)

# Enhanced header with FinSight branding
HEADER_BG = "#161B22"
ACCENT_COLOR = "#58A6FF"

header_bg_config = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    "name": "header_bg",
    "position": {
        "x": 0,
        "y": 0,
        "z": 1000,
        "height": 72,
        "width": 1280,
        "tabOrder": 1000
    },
    "visual": {
        "visualType": "shape",
        "objects": {
            "fill": [
                {
                    "properties": {
                        "fillColor": {
                            "solid": {
                                "color": {
                                    "expr": {
                                        "Literal": {
                                            "Value": "'" + HEADER_BG + "'"
                                        }
                                    }
                                }
                            }
                        },
                        "transparency": {
                            "expr": {
                                "Literal": {
                                    "Value": "0D"
                                }
                            }
                        }
                    }
                }
            ],
            "shape": [
                {
                    "properties": {
                        "tileShape": {
                            "expr": {
                                "Literal": {
                                    "Value": "'rectangle'"
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
}

# Accent line below header
accent_line_config = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    "name": "header_accent_line",
    "position": {
        "x": 0,
        "y": 72,
        "z": 999,
        "height": 3,
        "width": 1280,
        "tabOrder": 999
    },
    "visual": {
        "visualType": "shape",
        "objects": {
            "fill": [
                {
                    "properties": {
                        "fillColor": {
                            "solid": {
                                "color": {
                                    "expr": {
                                        "Literal": {
                                            "Value": "'" + ACCENT_COLOR + "'"
                                        }
                                    }
                                }
                            }
                        },
                        "transparency": {
                            "expr": {
                                "Literal": {
                                    "Value": "0D"
                                }
                            }
                        }
                    }
                }
            ],
            "shape": [
                {
                    "properties": {
                        "tileShape": {
                            "expr": {
                                "Literal": {
                                    "Value": "'rectangle'"
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
}

# FinSight logo/text visual
finSight_branding = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    "name": "branding_title",
    "position": {
        "x": 20,
        "y": 12,
        "z": 1001,
        "height": 48,
        "width": 300,
        "tabOrder": 1001
    },
    "visual": {
        "visualType": "textbox",
        "objects": {
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "textRuns": [
                                    {
                                        "textStyle": {
                                            "fontFamily": "Segoe UI",
                                            "fontSize": 22,
                                            "fontWeight": 700,
                                            "color": {
                                                "solid": {
                                                    "color": {
                                                        "expr": {
                                                            "Literal": {
                                                                "Value": "'#E6EDF3'"
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        "value": "FinSight  "
                                    },
                                    {
                                        "textStyle": {
                                            "fontFamily": "Segoe UI",
                                            "fontSize": 14,
                                            "fontWeight": 400,
                                            "color": {
                                                "solid": {
                                                    "color": {
                                                        "expr": {
                                                            "Literal": {
                                                                "Value": "'#8B949E'"
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        "value": "Financial Intelligence Dashboard"
                                    }
                                ],
                                "horizontalAlignment": "Left"
                            }
                        ],
                        "verticalAlignment": "Middle"
                    }
                }
            ]
        },
        "visualContainerObjects": {
            "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "visualHeader": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
        }
    }
}

# Page title header (shows on each page)
def get_page_title_header(page_display_name):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
        "name": "page_title_header",
        "position": {
            "x": 450,
            "y": 18,
            "z": 1002,
            "height": 36,
            "width": 380,
            "tabOrder": 1002
        },
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "textStyle": {
                                                "fontFamily": "Segoe UI",
                                                "fontSize": 18,
                                                "fontWeight": 600,
                                                "color": {
                                                    "solid": {
                                                        "color": {
                                                            "expr": {
                                                                "Literal": {
                                                                    "Value": "'#E6EDF3'"
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            },
                                            "value": page_display_name
                                        }
                                    ],
                                    "horizontalAlignment": "Center"
                                }
                            ],
                            "verticalAlignment": "Middle"
                        }
                    }
                ]
            },
            "visualContainerObjects": {
                "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "visualHeader": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
            }
        }
    }

# Page name mapping
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

# Update or create header visuals for each page
for page_name, display_name in PAGE_DISPLAY_NAMES.items():
    page_folder = os.path.join(PAGES_DIR, page_name)
    visuals_dir = os.path.join(page_folder, "visuals")
    
    # Update header_bg
    header_dir = os.path.join(visuals_dir, "header_bg")
    os.makedirs(header_dir, exist_ok=True)
    
    # Add text overlay to header background
    header_with_text = json.loads(json.dumps(header_bg_config))
    header_with_text["visual"]["objects"]["text"] = [
        {
            "properties": {
                "show": {"expr": {"Literal": {"Value": "false"}}},
                "text": {"expr": {"Literal": {"Value": "'" + display_name + "'"}}},
                "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#E6EDF3'"}}}}},
                "fontSize": {"expr": {"Literal": {"Value": "0D"}}}
            }
        }
    ]
    
    with open(os.path.join(header_dir, "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(header_with_text, f, indent=2)
    
    # Create accent line
    accent_dir = os.path.join(visuals_dir, "header_accent_line")
    os.makedirs(accent_dir, exist_ok=True)
    with open(os.path.join(accent_dir, "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(accent_line_config, f, indent=2)
    
    # Create FinSight branding
    branding_dir = os.path.join(visuals_dir, "branding_title")
    os.makedirs(branding_dir, exist_ok=True)
    with open(os.path.join(branding_dir, "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(finSight_branding, f, indent=2)
    
    # Create page title header
    page_title_dir = os.path.join(visuals_dir, "page_title_header")
    os.makedirs(page_title_dir, exist_ok=True)
    with open(os.path.join(page_title_dir, "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(get_page_title_header(display_name), f, indent=2)
    
    print("  [OK] Updated header for: " + page_name)

# =============================================================================
# STEP 5: Update all visual.json files for dark theme consistency
# =============================================================================
print("")
print("=" * 60)
print("STEP 5: Updating visual styling for dark theme consistency")
print("=" * 60)

DARK_BG = "#161B22"
BORDER_COLOR = "#30363D"
SHADOW_COLOR = "#000000"
TEXT_PRIMARY = "#E6EDF3"
TEXT_SECONDARY = "#8B949E"
TITLE_COLOR = "#E6EDF3"
ACCENT_BAR_COLOR = "#58A6FF"

visual_files = glob.glob(os.path.join(PAGES_DIR, "*", "visuals", "*", "visual.json"))
updated_count = 0

for vf in sorted(visual_files):
    # Skip header/accent/branding/title visuals we just created
    skip_names = ["header_bg", "header_accent_line", "branding_title", "page_title_header", "global_nav_bar"]
    should_skip = False
    for skip in skip_names:
        if skip in vf:
            should_skip = True
            break
    if should_skip:
        continue
    
    with open(vf, 'r', encoding='utf-8') as f:
        v_data = json.load(f)
    
    modified = False
    visual_type = v_data.get("visual", {}).get("visualType", "")
    
    # Ensure visualContainerObjects exists
    if "visualContainerObjects" not in v_data.get("visual", {}):
        if "visual" not in v_data:
            continue
        v_data["visual"]["visualContainerObjects"] = {}
    
    vco = v_data["visual"]["visualContainerObjects"]
    
    # --- Update/Add Background ---
    if "background" not in vco:
        vco["background"] = [
            {
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + DARK_BG + "'"}}}}},
                    "transparency": {"expr": {"Literal": {"Value": "0D"}}}
                }
            }
        ]
        modified = True
    
    # --- Update/Add Border ---
    border_props = {
        "show": {"expr": {"Literal": {"Value": "true"}}},
        "radius": {"expr": {"Literal": {"Value": "4D"}}},
        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + BORDER_COLOR + "'"}}}}},
        "width": {"expr": {"Literal": {"Value": "1D"}}}
    }
    
    if "border" in vco:
        for border in vco["border"]:
            props = border.get("properties", {})
            if "color" in props:
                props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + BORDER_COLOR + "'"}}}}}
                modified = True
            if "show" in props:
                props["show"] = {"expr": {"Literal": {"Value": "true"}}}
                modified = True
    else:
        vco["border"] = [{"properties": border_props}]
        modified = True
    
    # --- Update/Add Drop Shadow ---
    shadow_props = {
        "show": {"expr": {"Literal": {"Value": "true"}}},
        "position": {"expr": {"Literal": {"Value": "'Outer'"}}},
        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'" + SHADOW_COLOR + "'"}}}}},
        "transparency": {"expr": {"Literal": {"Value": "60D"}}}
    }
    
    if "dropShadow" in vco:
        for shadow in vco["dropShadow"]:
            props = shadow.get("properties", {})
            if "color" in props:
                props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + SHADOW_COLOR + "'"}}}}}
                modified = True
            if "transparency" not in props:
                props["transparency"] = {"expr": {"Literal": {"Value": "60D"}}}
                modified = True
    else:
        vco["dropShadow"] = [{"properties": shadow_props}]
        modified = True
    
    # --- Update Title for dark theme ---
    if "title" in vco:
        for title in vco["title"]:
            props = title.get("properties", {})
            if "fontColor" in props:
                props["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TITLE_COLOR + "'"}}}}}
                modified = True
            # Add title background
            if "background" not in props:
                props["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + DARK_BG + "'"}}}}}
                modified = True
    
    # --- Update Visual Header for dark theme ---
    if "visualHeader" in vco:
        for vh in vco["visualHeader"]:
            props = vh.get("properties", {})
            if "background" in props:
                props["background"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + DARK_BG + "'"}}}}}
                modified = True
            if "border" in props:
                props["border"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + BORDER_COLOR + "'"}}}}}
                modified = True
            if "foreground" in props:
                props["foreground"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_PRIMARY + "'"}}}}}
                modified = True
    
    # --- Update card visual hardcoded colors ---
    if visual_type in ["cardVisual", "card"]:
        objs = v_data.get("visual", {}).get("objects", {})
        
        # Update value fontColor to light
        for val in objs.get("value", []):
            props = val.get("properties", {})
            if "fontColor" in props:
                props["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_PRIMARY + "'"}}}}}
                modified = True
            if "labelDisplayUnits" not in props:
                props["labelDisplayUnits"] = {"expr": {"Literal": {"Value": "0D"}}}
                modified = True
        
        # Update accent bar to theme color
        for accent in objs.get("accentBar", []):
            props = accent.get("properties", {})
            if "color" in props:
                props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + ACCENT_BAR_COLOR + "'"}}}}}
                modified = True
        
        # Update label colors
        for label in objs.get("label", []):
            props = label.get("properties", {})
            if "fontColor" in props:
                props["fontColor"] = {"solid": {"color": {"expr": {"Literal": {"Value": "'" + TEXT_SECONDARY + "'"}}}}}
                modified = True
    
    if modified:
        updated_count += 1
        with open(vf, 'w', encoding='utf-8') as f:
            json.dump(v_data, f, indent=2)

print("  [OK] Updated " + str(updated_count) + " visual files for dark theme consistency")

# =============================================================================
# STEP 6: Clean up old theme files
# =============================================================================
print("")
print("=" * 60)
print("STEP 6: Cleanup")
print("=" * 60)

# Remove the old ShowMeTheNumbers theme from definition RegisteredResources
old_theme_def = os.path.join(DEFINITION_DIR, "RegisteredResources", "ShowMeTheNumbers38403062065871878.json")
if os.path.exists(old_theme_def):
    os.remove(old_theme_def)
    print("  [OK] Removed old ShowMeTheNumbers theme from definition/RegisteredResources")

old_theme_static = os.path.join(STATIC_RESOURCES, "ShowMeTheNumbers38403062065871878.json")
if os.path.exists(old_theme_static):
    os.remove(old_theme_static)
    print("  [OK] Removed old ShowMeTheNumbers theme from StaticResources/RegisteredResources")

# =============================================================================
# STEP 7: Add page navigation to pages missing it
# =============================================================================
print("")
print("=" * 60)
print("STEP 7: Adding page navigation to missing pages")
print("=" * 60)

# Standard page navigator visual config
page_nav_config = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    "name": "page_navigator",
    "position": {
        "x": 340,
        "y": 0,
        "z": 13000,
        "height": 72,
        "width": 600,
        "tabOrder": 13000
    },
    "visual": {
        "visualType": "pageNavigator",
        "drillFilterOtherVisuals": True,
        "visualContainerObjects": {
            "background": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "false"}}},
                        "transparency": {"expr": {"Literal": {"Value": "100D"}}}
                    }
                }
            ],
            "border": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "false"}}}
                    }
                }
            ]
        }
    }
}

pages_missing_nav = ["ml_monitoring", "real_time_monitoring"]
for page_name in pages_missing_nav:
    page_folder = os.path.join(PAGES_DIR, page_name)
    visuals_dir = os.path.join(page_folder, "visuals")
    nav_dir = os.path.join(visuals_dir, "page_navigator")
    os.makedirs(nav_dir, exist_ok=True)
    with open(os.path.join(nav_dir, "visual.json"), 'w', encoding='utf-8') as f:
        json.dump(page_nav_config, f, indent=2)
    print("  [OK] Added page navigation to: " + page_name)

print("")
print("=" * 60)
print("OVERHAUL COMPLETE")
print("=" * 60)
print("")
print("Summary of changes:")
print("  * Theme: Switched to finsight_theme.json (professional dark theme)")
print("  * Pages: Dark backgrounds applied to all " + str(len(page_files)) + " pages")
print("  * Headers: FinSight branding + page titles on all pages")
print("  * Navigation: Accent line under header for visual separation")
print("  * Page nav: Added navigation to " + str(len(pages_missing_nav)) + " missing pages")
print("  * Visuals: " + str(updated_count) + " visuals updated for dark theme consistency")
print("  * White spaces: Eliminated with full dark canvas")
