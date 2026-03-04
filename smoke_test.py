#!/usr/bin/env python3
"""
Smoke tests for DNA deployment.
Quick verification that critical paths work.
"""
import sys
import requests
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Health: {data['status']} (git: {data.get('git_sha', 'unknown')[:8]})")
            return True
        else:
            print(f"❌ Health: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health: {e}")
        return False

def test_app_loads():
    """Test main app page loads."""
    try:
        r = requests.get(f"{BASE_URL}/app", timeout=5)
        if r.status_code == 200 and "DNA" in r.text:
            print("✅ App page: Loads")
            return True
        else:
            print(f"❌ App page: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ App page: {e}")
        return False

def test_evaluate():
    """Test bet evaluation works."""
    try:
        r = requests.post(
            f"{BASE_URL}/app/evaluate",
            json={"input": "LAL -4.5", "tier": "BETTER"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if "explain" in data:
                print(f"✅ Evaluate: Works (confidence: {data['explain'].get('confidence', 'N/A')})")
                return True
        print(f"❌ Evaluate: Invalid response")
        return False
    except Exception as e:
        print(f"❌ Evaluate: {e}")
        return False

def test_nba_teams():
    """Test NBA teams endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/api/nba/teams", timeout=5)
        if r.status_code == 200:
            teams = r.json()
            print(f"✅ NBA teams: {len(teams)} teams loaded")
            return True
        else:
            print(f"❌ NBA teams: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ NBA teams: {e}")
        return False

def main():
    print("=" * 60)
    print("DNA SMOKE TESTS")
    print("=" * 60)
    print(f"Testing: {BASE_URL}")
    print()
    
    # Wait for server to be ready
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            break
        except:
            print(f"Waiting for server... ({i+1}/10)")
            time.sleep(1)
    
    tests = [
        test_health,
        test_app_loads,
        test_evaluate,
        test_nba_teams,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        time.sleep(0.5)
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Ready for production")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Fix before deploying")
        return 1

if __name__ == "__main__":
    sys.exit(main())
