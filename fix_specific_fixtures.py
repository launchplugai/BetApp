#!/usr/bin/env python3
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
        pattern = rf"(class {class_name}:.*?)(    def {method_name}\(self), \w+\):)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            old_sig = match.group(2)
            new_sig = f"    def {method_name}(self, {fixture}):"
            content = content.replace(old_sig, new_sig)

with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Updated specific test method fixtures")
