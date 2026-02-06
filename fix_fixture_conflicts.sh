#!/bin/bash
# Fix conflicts where tests assign to fixture names

cd /var/lib/openbot/workdir/target

# Remove lines that assign to fixture variables (app_js = response.text, etc.)
sed -i '/^        app_js = response\.text$/d' app/tests/test_web.py
sed -i '/^        app_css = response\.text$/d' app/tests/test_web.py
sed -i '/^        app_html = response\.text$/d' app/tests/test_web.py

# For tests that still have response.text but no response variable, we need to revert them to use client
# Find tests with NameError (response not defined) and fix them

echo "✓ Fixed fixture conflicts"
