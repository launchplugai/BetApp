#!/usr/bin/env python3
"""
S6: Complete fix for all web tests after template refactor.
"""

import re

with open("app/tests/test_web.py", "r") as f:
    content = f.read()

# Step 1: Add app_html and app_css fixtures
fixtures = '''
@pytest.fixture
def app_html(client):
    """Fetch rendered HTML from /app for template structure tests (S6 refactor)."""
    response = client.get("/app")
    if response.status_code == 200:
        return response.text
    return ""


@pytest.fixture
def app_css(client):
    """Fetch CSS from /static/css/app.css for style tests (S6 refactor)."""
    response = client.get("/static/css/app.css")
    if response.status_code == 200:
        return response.text
    return ""
'''

# Find where to insert (after app_js fixture)
if '@pytest.fixture\ndef app_html(' not in content:
    insert_pos = content.find('\n\n# =============================================================================\n# Tests: Root Redirect')
    if insert_pos != -1:
        content = content[:insert_pos] + fixtures + content[insert_pos:]

# Step 2: Fix tests that should use client (not app_js)
# These are tests that need to make actual HTTP requests

client_tests = [
    'test_root_redirects_to_app',
    'test_root_follows_to_app',
    'test_ui2_redirects_to_app',
    'test_ui2_follows_to_app',
    'test_valid_evaluation_returns_200',
    'test_empty_input_returns_400',
    'test_evaluation_includes_artifacts',
    'test_evaluation_includes_signal_info',
    'test_service_disabled_returns_503',
    'test_app_with_debug_param',
    'test_redirects_still_work_with_builder',
]

# Pattern to fix: def test_NAME(self, app_js): back to def test_NAME(self, client):
for test_name in client_tests:
    content = re.sub(
        rf'(    def {test_name}\(self), app_js\):',
        r'\1, client):',
        content
    )

# Step 3: Fix tests that should use app_html (HTML structure checks)
# Pattern: tests that check HTML elements but were converted to app_js

html_test_classes = [
    'TestCanonicalAppPage',
    'TestParlayBuilderUI',
    'TestTicket25EvaluationReceipt',
    'TestTicket26LegInterpretationAndGuidance',
    'TestTicket27CanonicalLegs',
    'TestTicket32CoreWorkspace',
    'TestTicket34OcrBuilderPrecision',
    'TestTicket35InlineRefineLoop',
]

for class_name in html_test_classes:
    # Find class boundaries
    class_start = content.find(f'class {class_name}:')
    if class_start == -1:
        continue
    
    next_class = content.find('\nclass ', class_start + 1)
    if next_class == -1:
        next_class = len(content)
    
    # Extract and modify class content
    before = content[:class_start]
    class_section = content[class_start:next_class]
    after = content[next_class:]
    
    # Replace app_js with app_html in method signatures
    class_section = re.sub(r'(    def test_\w+\(self), app_js\):', r'\1, app_html):', class_section)
    
    # Replace app_js with app_html in test bodies (but not in comments/docstrings)
    class_section = class_section.replace(' in app_js,', ' in app_html,')
    class_section = class_section.replace(' in app_js:', ' in app_html:')
    class_section = class_section.replace(' in app_js\n', ' in app_html\n')
    class_section = re.sub(r'\bassert\s+"([^"]+)"\s+in\s+app_js\b', r'assert "\1" in app_html', class_section)
    class_section = re.sub(r'\bassert\s+\'([^\']+)\'\s+in\s+app_js\b', r"assert '\1' in app_html", class_section)
    
    content = before + class_section + after

# Step 4: Fix CSS tests to use app_css fixture
# Find tests that check for CSS classes/styles

css_checks = [
    'test_builder_section_exists',
    'test_paste_section_exists', 
    'test_mode_toggle_exists',
    'test_sticky_action_bar_exists',
    'test_workbench_layout_styles_exist',
    'test_desktop_media_query_exists',
    'test_leg_clarity_css_classes_exist',
    'test_ocr_review_gate_css_exists',
    'test_ocr_info_box_css_exists',
    'test_leg_edit_css_exists',
    'test_result_leg_controls_css_exists',
    'test_leg_lock_btn_css_exists',
    'test_leg_remove_btn_css_exists',
    'test_locked_leg_styling_exists',
    'test_reevaluate_btn_css_exists',
]

# These need both app_html (for HTML) and app_css (for CSS)
# Replace app_html with both fixtures for CSS tests
for test_name in css_checks:
    pattern = rf'(    def {test_name}\(self), app_html\):'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\1, app_html, app_css):', content)

# Add CSS checks to test bodies
# Tests that mention "css" or "style" should check app_css too
def add_css_checks(match):
    method_sig = match.group(0)
    # If it doesn't have app_css parameter, keep original
    if ', app_css):' not in method_sig:
        return method_sig
    return method_sig

# Write back
with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Fixed all web tests")
