"""
UI Smoke Tests for Dashboard Page
"""
import pytest
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_dashboard_loads():
    """Dashboard page loads without errors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load dashboard
        await page.goto(f"{BASE_URL}/app?screen=dashboard")
        await page.wait_for_timeout(2000)
        
        # Check title
        title = await page.title()
        assert "Dashboard" in title or "DNA" in title
        
        # Check for key elements
        assert await page.locator('#user-name').count() > 0
        assert await page.locator('#user-balance').count() > 0
        
        await browser.close()

@pytest.mark.asyncio
async def test_dashboard_navigation():
    """Dashboard navigation links work."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=dashboard")
        await page.wait_for_timeout(2000)
        
        # Check nav links exist
        assert await page.locator('#nav-home').count() > 0
        assert await page.locator('#nav-browse').count() > 0
        assert await page.locator('#nav-builder').count() > 0
        
        await browser.close()

@pytest.mark.asyncio
async def test_dashboard_console_no_errors():
    """No console errors on dashboard load."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        await page.goto(f"{BASE_URL}/app?screen=dashboard")
        await page.wait_for_timeout(3000)
        
        # Filter out expected errors
        critical_errors = [e for e in errors if '401' not in e and 'Unauthorized' not in e]
        
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"
        
        await browser.close()
