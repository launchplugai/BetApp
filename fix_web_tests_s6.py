#!/usr/bin/env python3
"""
S6: Batch fix web tests to use app_js fixture for JavaScript checks.

Only updates tests that check JavaScript content, leaves HTML/CSS tests alone.
"""

import re

# Read the test file
with open("app/tests/test_web.py", "r") as f:
    content = f.read()

# Add app_js fixture if not already there
if "@pytest.fixture\ndef app_js(" not in content:
    fixture_code = '''
@pytest.fixture
def app_js(client):
    """Fetch app.js content for JS-specific tests (S6 refactor)."""
    response = client.get("/static/js/app.js")
    if response.status_code == 200:
        return response.text
    return ""
'''
    # Insert after client_disabled fixture
    content = content.replace(
        '    return TestClient(app)\n\n\n# =============',
        f'    return TestClient(app)\n{fixture_code}\n\n# ============='
    )

# Target: TestTicket36OcrRegressionRepair, TestTicket37LegIdentity, TestTicket37BHashUpgrade, TestTicket38AOcrErrorRendering
# Only update these specific classes

# Pattern: def test_NAME(self, client): followed by client.get("/app") and html = response.text
# Replace with: def test_NAME(self, app_js): and remove those lines, replace "html" with "app_js"

classes_to_fix = [
    "TestTicket36OcrRegressionRepair",
    "TestTicket37LegIdentity", 
    "TestTicket37BHashUpgrade",
    "TestTicket38AOcrErrorRendering"
]

for class_name in classes_to_fix:
    # Find the class definition
    class_pattern = f"class {class_name}:"
    if class_pattern not in content:
        continue
    
    # Find class start and next class start
    class_start = content.find(class_pattern)
    next_class = content.find("\nclass ", class_start + 1)
    if next_class == -1:
        next_class = len(content)
    
    # Extract class content
    class_content = content[class_start:next_class]
    original_class = class_content
    
    # Fix each test method in this class
    test_pattern = re.compile(
        r'(    def test_\w+\(self), client\):\s*\n'
        r'(.*?)'
        r'        response = client\.get\("/app"\)\s*\n'
        r'        assert response\.status_code == 200\s*\n'
        r'        html = response\.text\s*\n',
        re.DOTALL
    )
    
    def replacer(match):
        method_decl = match.group(1)
        docstring = match.group(2)
        return f'{method_decl}, app_js):\n{docstring}'
    
    class_content = test_pattern.sub(replacer, class_content)
    
    # Replace "in html" with "in app_js" for these classes
    class_content = class_content.replace(' in html', ' in app_js')
    class_content = class_content.replace('html.count', 'app_js.count')
    class_content = class_content.replace('(html)', '(app_js)')
    
    # Replace in original content
    content = content.replace(original_class, class_content)

# Write back
with open("app/tests/test_web.py", "w") as f:
    f.write(content)

print("✓ Fixed web tests for S6 refactor")
