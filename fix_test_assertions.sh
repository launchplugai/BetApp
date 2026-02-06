#!/bin/bash
# Fix test assertions to check correct fixtures

cd /var/lib/openbot/workdir/target

# For tests that check JS but still use html variable
# Change the test to use app_js fixture and skip HTTP request

# Tests between lines 1165-1220 (SessionManager tests)
sed -i '1165,1220s/ in html/ in app_js/g' app/tests/test_web.py
sed -i '1165,1220s/html,/app_js,/g' app/tests/test_web.py

# Tests between lines 1220-1310 (Session/Workbench CSS tests)
sed -i '1220,1310s/ in html/ in app_css/g' app/tests/test_web.py
sed -i '1220,1310s/html,/app_css,/g' app/tests/test_web.py

# Tests between lines 1330-1400 (OCR parsing tests)
sed -i '1330,1400s/ in html/ in app_js/g' app/tests/test_web.py
sed -i '1330,1400s/html,/app_js,/g' app/tests/test_web.py

# Tests between lines 1340-1420 (OCR CSS and clarity tests)
sed -i '1340,1380s/ in html/ in app_js/g' app/tests/test_web.py
sed -i '1347s/ in app_js/ in app_css/' app/tests/test_web.py  # leg-source-tag is CSS
sed -i '1354s/ in app_js/ in app_css/' app/tests/test_web.py  # ocr-leg is CSS
sed -i '1370s/ in app_js/ in app_css/' app/tests/test_web.py  # clarity classes are CSS

# Fix: dna_artifact_counts should be camelCase
sed -i 's/"dna_artifact_counts"/"dnaArtifactCounts"/g' app/tests/test_web.py

echo "✓ Fixed test assertions"
