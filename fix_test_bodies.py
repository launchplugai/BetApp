#!/usr/bin/env python3
"""
S6: Fix test method bodies to use correct fixtures
"""

import re

with open("app/tests/test_web.py", "r") as f:
    content = f.read()

# Pattern to find test methods that make HTTP requests but should use fixtures
# These tests currently do: client.get("/app"); html = response.text; assert X in html

test_fixes = {
    # JS checks - should use app_js fixture
    'test_session_manager_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_session_manager_get_session': ('client', 'app_js', 'html', 'app_js'),
    'test_session_manager_save_session': ('client', 'app_js', 'html', 'app_js'),
    'test_local_storage_usage': ('client', 'app_js', 'html', 'app_js'),
    'test_parse_ocr_to_legs_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_parse_ocr_line_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_get_ocr_leg_clarity_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_get_clarity_display_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_has_legs_needing_review_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_show_ocr_review_gate_exists': ('client', 'app_js', 'html', 'app_js'),
    'test_ocr_source_tag_in_code': ('client', 'app_js', 'html', 'app_js'),
    'test_clear_match_label_exists': ('client', 'app_js', 'html', 'app_js'),
    
    # CSS checks - should use app_css fixture  
    'test_image_upload_section_styles': ('client', 'app_css', 'html', 'app_css'),
    'test_analysis_badges_styles': ('client', 'app_css', 'html', 'app_css'),
    'test_session_bar_styles': ('client', 'app_css', 'html', 'app_css'),
    'test_workbench_styles': ('client', 'app_css', 'html', 'app_css'),
    'test_desktop_media_query': ('client', 'app_css', 'html', 'app_css'),
    'test_leg_source_tag_css_exists': ('client', 'app_css', 'html', 'app_css'),
    'test_ocr_leg_css_exists': ('client', 'app_css', 'html', 'app_css'),
    'test_clear_clarity_css_exists': ('client', 'app_css', 'html', 'app_css'),
    'test_ocr_review_gate_styles': ('client', 'app_css', 'html', 'app_css'),
}

for test_name, (old_fixture, new_fixture, old_var, new_var) in test_fixes.items():
    # Find the test method
    pattern = rf'(    def {test_name}\(self, {old_fixture}\):.*?)(response = client\.get\("/app"\)\s+assert response\.status_code == 200\s+html = response\.text)'
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        # Replace the fixture parameter
        content = re.sub(
            rf'(    def {test_name}\(self), {old_fixture}\):',
            rf'\1, {new_fixture}):',
            content
        )
        
        # Remove the HTTP request lines (response = client.get...; html = response.text)
        pattern_to_remove = r'response = client\.get\("/app"\)\s+assert response\.status_code == 200\s+html = response\.text\s+'
        
        # Find the test method
        test_pattern = rf'(    def {test_name}\(self, {new_fixture}\):.*?)(response = client\.get.*?html = response\.text\s+)'
        content = re.sub(test_pattern, r'\1', content, flags=re.DOTALL)
        
        # Replace html variable with the fixture name in assertions
        # But only within this test method - need to be careful
        # For now, do a simple replacement in common patterns
        if old_var != new_var:
            # Replace "in html" with "in app_js" or "in app_css"
            content = content.replace(f' in {old_var},', f' in {new_var},')
            content = content.replace(f' in {old_var}', f' in {new_var}')

with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Fixed test method bodies")
