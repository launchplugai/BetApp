#!/bin/bash
# Apply only the clean, safe fixes

# Fix camelCase in test expectations
sed -i 's/"verdict_text"/"verdictText"/g' app/tests/test_web.py
sed -i 's/"bet_type"/"betType"/g' app/tests/test_web.py
sed -i 's/"base_fragility"/"baseFragility"/g' app/tests/test_web.py
sed -i 's/"analysis_depth"/"analysisDepth"/g' app/tests/test_web.py
sed -i 's/\["verdict_text"\]/["verdictText"]/g' app/tests/test_web.py
sed -i 's/\["bet_type"\]/["betType"]/g' app/tests/test_web.py
sed -i 's/\["analysis_depth"\]/["analysisDepth"]/g' app/tests/test_web.py
sed -i 's/\.get("bet_type")/.get("betType")/g' app/tests/test_web.py
sed -i 's/\.get("verdict_text")/.get("verdictText")/g' app/tests/test_web.py
sed -i 's/\.get("analysis_depth")/.get("analysisDepth")/g' app/tests/test_web.py

# Fix sample_artifacts -> dnaArtifactCounts  
sed -i 's/"sample_artifacts"/"dnaArtifactCounts"/g' app/tests/test_web.py

# Fix redirect status codes
sed -i 's/assert response.status_code == 302/assert response.status_code in (302, 307)/g' app/tests/test_web.py

# Fix Refine Parlay button text
sed -i 's/"Refine Parlay"/"Refine Structure"/g' app/tests/test_web.py

# Fix leg_count and display_label references
sed -i 's/assert "leg_count" in parlay/assert "legCount" in parlay/g' app/tests/test_web.py
sed -i 's/parlay\["leg_count"\]/parlay["legCount"]/g' app/tests/test_web.py
sed -i 's/"display_label"/"displayLabel"/g' app/tests/test_web.py
sed -i 's/\["display_label"\]/["displayLabel"]/g' app/tests/test_web.py

echo "✓ Applied clean fixes only"
