#!/usr/bin/env python3
"""
S6: Fix all remaining test failures after refactor.
"""

import re

with open("app/tests/test_web.py", "r") as f:
    content = f.read()

# Step 1: Map test methods to correct fixtures based on what they check
# JS checks -> app_js
# CSS checks -> app_css
# API response checks -> keep client

js_check_patterns = [
    'SessionManager',
    'localStorage',
    'parseOcrToLegs',
    'parseOcrLine',
    'getOcrLegClarity',
    'showResults',
    'toggleDebug',
    'debugMode',
    'reEvaluateParlay',
    'refineParlay',
    'resetForm',
    'function ',
    'const ',
    'let ',
    '.call(',
    '.apply(',
]

css_check_patterns = [
    '.css',
    'media query',
    '-btn',
    '-section',
    '-panel',
    'workbench',
    'leg-source-tag',
    'ocr-leg',
    'clarity',
    'locked',
    'editable',
    'analysis-badges',
    'session-bar',
]

# Step 2: Find all test methods and determine which fixture they need
test_method_pattern = re.compile(
    r'(    def (test_\w+)\(self(?:, (app_html|app_js|app_css|client))?\):.*?(?=\n    def |\nclass |\Z))',
    re.DOTALL
)

matches = list(test_method_pattern.finditer(content))

replacements = []

for match in matches:
    full_method = match.group(1)
    method_name = match.group(2)
    current_fixture = match.group(3) or 'client'
    
    # Skip if already correct
    method_body = full_method
    
    # Determine correct fixture
    correct_fixture = current_fixture
    
    # Check if it's an API test (needs client)
    if 'response = client.' in method_body or 'TestClient' in method_body:
        if '.get("/app")' not in method_body and '.get("/static/' not in method_body:
            correct_fixture = 'client'
            continue  # Already using client, skip
    
    # Check if it needs app_js
    needs_js = any(pattern in method_body for pattern in js_check_patterns)
    
    # Check if it needs app_css  
    needs_css = any(pattern in method_body for pattern in css_check_patterns)
    
    # Check if it's checking HTML structure
    checks_html_structure = (
        'in app_html' in method_body or
        'id="' in method_body or
        '<div' in method_body or
        'class="card' in method_body
    )
    
    if needs_js and not needs_css:
        correct_fixture = 'app_js'
    elif needs_css and not needs_js:
        correct_fixture = 'app_css'
    elif needs_js and needs_css:
        # Needs both - update to use both fixtures
        if current_fixture != 'app_js':
            # Change signature to include both
            old_sig = f'    def {method_name}(self, {current_fixture}):'
            new_sig = f'    def {method_name}(self, app_js, app_css):'
            replacements.append((old_sig, new_sig))
        continue
    elif checks_html_structure:
        correct_fixture = 'app_html'
    
    # Update fixture if needed
    if correct_fixture != current_fixture:
        old_sig = f'    def {method_name}(self, {current_fixture}):'
        new_sig = f'    def {method_name}(self, {correct_fixture}):'
        replacements.append((old_sig, new_sig))

# Apply replacements
for old, new in replacements:
    content = content.replace(old, new)

# Step 3: Fix specific test issues

# Fix API response format checks
content = content.replace(
    "assert 'error' in response.json()",
    "assert 'detail' in response.json()"
)

# Fix CSS checks in app_html
css_classes_to_check_in_css = [
    'image-upload-section',
    'analysis-badges',
    'session-bar',
    'workbench',
    'leg-source-tag',
    'ocr-leg',
    'result-leg-controls',
    'leg-lock-btn',
    'leg-remove-btn',
    'reevaluate-btn',
]

# For tests checking CSS classes, route to app_css
for css_class in css_classes_to_check_in_css:
    # Find assertions checking for these classes in app_html
    pattern = rf'(assert ".*{re.escape(css_class)}.*" in app_html)'
    if re.search(pattern, content):
        content = re.sub(
            rf'(    def test_\w+_css\w*\(self), app_html\):',
            r'\1, app_css):',
            content
        )

# Fix JS function checks
js_functions = [
    'SessionManager',
    'parseOcrToLegs', 
    'parseOcrLine',
    'getOcrLegClarity',
    'showResults',
    'toggleDebug',
    'reEvaluateParlay',
    'refineParlay',
]

for func in js_functions:
    # Change checks from app_html to app_js
    content = re.sub(
        rf'assert "{re.escape(func)}" in app_html',
        f'assert "{func}" in app_js',
        content
    )
    content = re.sub(
        rf'assert \'{re.escape(func)}\' in app_html',
        f"assert '{func}' in app_js",
        content
    )

# Write back
with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Fixed fixture routing for remaining tests")

# Step 4: Create comprehensive fixture update script
update_script = '''#!/usr/bin/env python3
import re

with open("app/tests/test_web.py", "r") as f:
    content = f.read()

# Map specific test classes to fixtures
updates = {
    # JS tests
    "TestTicket32CoreWorkspace": {
        "test_session_manager_object_exists": "app_js",
        "test_session_manager_get_session": "app_js",
        "test_session_manager_save_session": "app_js",
        "test_local_storage_usage": "app_js",
    },
    "TestTicket34OcrBuilderPrecision": {
        "test_parse_ocr_to_legs_exists": "app_js",
        "test_parse_ocr_line_exists": "app_js",
        "test_ocr_source_tag_in_code": "app_js",
        "test_get_ocr_leg_clarity_exists": "app_js",
    },
    "TestTicket35InlineRefineLoop": {
        "test_show_results_populates_results_legs": "app_js",
        "test_results_legs_preserve_original_index": "app_js",
        "test_toggle_lock_function_exists": "app_js",
        "test_lock_icons_in_code": "app_js",
        "test_lock_button_titles_exist": "app_js",
    },
}

for class_name, method_fixes in updates.items():
    for method_name, fixture in method_fixes.items():
        # Find and update method signature
        pattern = rf"(class {class_name}:.*?)(    def {method_name}\\(self), \\w+\\):)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            old_sig = match.group(2)
            new_sig = f"    def {method_name}(self, {fixture}):"
            content = content.replace(old_sig, new_sig)

with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Updated specific test method fixtures")
'''

with open("fix_specific_fixtures.py", "w") as f:
    f.write(update_script)

print("✓ Created fixture update script")
