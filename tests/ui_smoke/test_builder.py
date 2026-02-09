"""
UI Smoke Tests for Builder Page

Tests all "light switches" (interactive elements) on builder page.
"""
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_builder_loads():
    """Builder page loads without errors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load builder with protocol context
        await page.goto(f"{BASE_URL}/app?screen=builder&protocolId=nba-lal-gsw-2026-02-09")
        
        # Check title
        title = await page.title()
        assert "BUILD PARLAY" in title or "Builder" in title
        
        await browser.close()

@pytest.mark.asyncio
async def test_all_tabs_exist():
    """All market tabs present and clickable."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        
        tabs = ['MAIN LINES', 'PLAYER PROPS', 'QUARTERS', 'HALVES']
        for tab in tabs:
            tab_btn = await page.locator(f'text={tab}').count()
            assert tab_btn > 0, f"Tab {tab} not found"
        
        await browser.close()

@pytest.mark.asyncio
async def test_tab_switching():
    """Clicking tabs switches market view."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        await page.wait_for_timeout(2000)  # Wait for load
        
        # Click QUARTERS tab
        await page.click('text=QUARTERS')
        await page.wait_for_timeout(500)
        
        # Should show quarter lines
        content = await page.content()
        assert 'Q1' in content or 'Q2' in content, "Quarters not shown"
        
        # Click HALVES tab
        await page.click('text=HALVES')
        await page.wait_for_timeout(500)
        
        content = await page.content()
        assert '1ST HALF' in content.upper() or '2ND HALF' in content.upper(), "Halves not shown"
        
        await browser.close()

@pytest.mark.asyncio
async def test_add_leg_highlights():
    """Clicking bet button adds leg and highlights."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        await page.wait_for_timeout(2000)
        
        # Click first spread button
        spread_buttons = await page.locator('button:has-text("(")').all()
        if len(spread_buttons) > 0:
            await spread_buttons[0].click()
            await page.wait_for_timeout(500)
            
            # Check for leg-selected class
            selected = await page.locator('.leg-selected').count()
            assert selected > 0, "Button should have leg-selected class"
            
            # Check leg count updated
            leg_count = await page.locator('#leg-count').text_content()
            assert leg_count == '1', f"Expected 1 leg, got {leg_count}"
        
        await browser.close()

@pytest.mark.asyncio
async def test_quarters_have_buttons():
    """Quarters tab has clickable buttons."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        await page.wait_for_timeout(2000)
        
        # Switch to quarters
        await page.click('text=QUARTERS')
        await page.wait_for_timeout(500)
        
        # Find and click a quarter spread button
        q_buttons = await page.locator('button:has-text("Q1")').all()
        if len(q_buttons) > 0:
            # Get parent div's buttons
            buttons = await page.locator('.bg-card button').all()
            if len(buttons) > 0:
                await buttons[0].click()
                await page.wait_for_timeout(500)
                
                # Verify leg added
                leg_count = await page.locator('#leg-count').text_content()
                assert int(leg_count) > 0, "Quarter leg not added"
        
        await browser.close()

@pytest.mark.asyncio
async def test_analyze_button_enables():
    """Analyze button enables when legs added."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        await page.wait_for_timeout(2000)
        
        # Check analyze button initially disabled
        analyze_btn = await page.locator('#analyze-btn')
        is_disabled = await analyze_btn.is_disabled()
        assert is_disabled, "Analyze should be disabled with no legs"
        
        # Add a leg
        buttons = await page.locator('button:has-text("(")').all()
        if len(buttons) > 0:
            await buttons[0].click()
            await page.wait_for_timeout(500)
            
            # Check enabled
            is_enabled = await analyze_btn.is_enabled()
            assert is_enabled, "Analyze should enable with legs"
        
        await browser.close()

@pytest.mark.asyncio
async def test_console_no_errors():
    """No console errors on builder load."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        await page.goto(f"{BASE_URL}/app?screen=builder")
        await page.wait_for_timeout(3000)
        
        # Filter out expected/harmless errors
        critical_errors = [e for e in errors if '404' not in e and 'favicon' not in e.lower()]
        
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"
        
        await browser.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
