#!/usr/bin/env python3
"""
Automated Browser Testing for DNA Platform

Headless browser that captures screenshots and HTML for debugging.
No manual interaction needed.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from datetime import datetime

async def test_dna_website():
    """Test DNA website and capture state."""
    
    results_dir = Path("./test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        tests = []
        
        # Test 1: Main app page
        try:
            await page.goto("https://dna-production-cb47.up.railway.app/app")
            await page.wait_for_load_state('networkidle')
            
            # Check for "coming soon" or error messages
            content = await page.content()
            
            if "coming soon" in content.lower():
                tests.append({
                    "page": "/app",
                    "status": "ISSUE_FOUND",
                    "issue": "Contains 'coming soon' message",
                    "screenshot": f"app_issue_{timestamp}.png"
                })
                await page.screenshot(path=results_dir / f"app_issue_{timestamp}.png")
            else:
                tests.append({
                    "page": "/app", 
                    "status": "OK",
                    "screenshot": f"app_ok_{timestamp}.png"
                })
                await page.screenshot(path=results_dir / f"app_ok_{timestamp}.png")
            
            # Save HTML for inspection
            with open(results_dir / f"app_{timestamp}.html", "w") as f:
                f.write(content)
                
        except Exception as e:
            tests.append({
                "page": "/app",
                "status": "ERROR",
                "error": str(e)
            })
        
        # Test 2: Builder screen
        try:
            await page.goto("https://dna-production-cb47.up.railway.app/app?screen=builder")
            await page.wait_for_load_state('networkidle')
            
            content = await page.content()
            
            if "coming soon" in content.lower():
                tests.append({
                    "page": "/app?screen=builder",
                    "status": "ISSUE_FOUND",
                    "issue": "Builder shows 'coming soon'",
                    "screenshot": f"builder_issue_{timestamp}.png"
                })
                await page.screenshot(path=results_dir / f"builder_issue_{timestamp}.png")
                
                # Save the HTML to find what template to fix
                with open(results_dir / f"builder_{timestamp}.html", "w") as f:
                    f.write(content)
            else:
                tests.append({
                    "page": "/app?screen=builder",
                    "status": "OK"
                })
                
        except Exception as e:
            tests.append({
                "page": "/app?screen=builder",
                "status": "ERROR", 
                "error": str(e)
            })
        
        await browser.close()
        
        # Print results
        print("=" * 70)
        print("BROWSER TEST RESULTS")
        print("=" * 70)
        
        for test in tests:
            print(f"\n📄 {test['page']}")
            print(f"   Status: {test['status']}")
            if 'issue' in test:
                print(f"   Issue: {test['issue']}")
            if 'screenshot' in test:
                print(f"   Screenshot: {results_dir}/{test['screenshot']}")
        
        print(f"\n📁 Results saved to: {results_dir}/")
        print("=" * 70)
        
        return tests

if __name__ == "__main__":
    asyncio.run(test_dna_website())
