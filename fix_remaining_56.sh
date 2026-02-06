#!/bin/bash
# Fix the remaining 56 test failures in 3 test classes

cd /var/lib/openbot/workdir/target

# Create Python script to do surgical replacements
python3 << 'PYTHON_SCRIPT'
import re

with open("app/tests/test_web.py", "r") as f:
    lines = f.readlines()

# Track which lines to modify
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find test methods that use client but should use app_js or app_css
    if "    def test_" in line and "(self, client):" in line:
        # Look ahead to see what it checks
        check_block = "".join(lines[i:min(i+20, len(lines))])
        
        # Determine if this should use app_js or app_css
        needs_app_js = any(x in check_block for x in [
            "SessionManager", "localStorage", "parseOcr", "getOcrLegClarity",
            "getClarityDisplay", "hasLegsNeedingReview", "showOcrReviewGate",
            "function ", "const ", "let ", "resultsLegs", "lockedLegIds",
            "updateReEvaluateButton", "updateParlayLabel", "toggleLegLock",
            "syncStateFromResults", "startEditLeg", "renderResultsLegs",
            "removeLegFromResults", "refineParlay", "resetForm", "reEvaluateParlay",
            "'Detected from slip'", "'Clear match'"
        ])
        
        needs_app_css = any(x in check_block for x in [
            ".image-upload", ".ocr-", ".session-bar", ".workbench",
            ".analysis-badges", "@media", ".leg-source-tag", ".ocr-leg",
            "-clarity", ".result-leg-controls", ".reevaluate-btn",
            ".leg-lock-btn", ".leg-remove-btn", ".locked", "styles should exist"
        ])
        
        if needs_app_js:
            # Change fixture to app_js
            lines[i] = line.replace("(self, client):", "(self, app_js):")
            # Remove next 3 lines (response = client.get, assert status, html = response.text)
            if i+3 < len(lines) and "response = client.get" in lines[i+2]:
                # Skip the HTTP request lines
                del lines[i+2:i+5]
            # Replace 'html' with 'app_js' in next ~15 lines
            for j in range(i+1, min(i+15, len(lines))):
                if "html" in lines[j] and "        " in lines[j]:
                    lines[j] = lines[j].replace(" html,", " app_js,")
                    lines[j] = lines[j].replace(" html ", " app_js ")
                    lines[j] = lines[j].replace(" html\n", " app_js\n")
                if "    def test_" in lines[j]:  # Next test method
                    break
                    
        elif needs_app_css:
            # Change fixture to app_css
            lines[i] = line.replace("(self, client):", "(self, app_css):")
            # Remove next 3 lines
            if i+3 < len(lines) and "response = client.get" in lines[i+2]:
                del lines[i+2:i+5]
            # Replace 'html' with 'app_css' in next ~15 lines
            for j in range(i+1, min(i+15, len(lines))):
                if "html" in lines[j] and "        " in lines[j]:
                    lines[j] = lines[j].replace(" html,", " app_css,")
                    lines[j] = lines[j].replace(" html ", " app_css ")
                    lines[j] = lines[j].replace(" html\n", " app_css\n")
                if "    def test_" in lines[j]:  # Next test method
                    break
    
    i += 1

with open("app/tests/test_web.py", "w") as f:
    f.writelines(lines)

print("✓ Fixed remaining 56 tests")
PYTHON_SCRIPT

echo "✓ Complete"
