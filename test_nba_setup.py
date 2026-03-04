"""
Test NBA data layer setup.
"""
import sys
from datetime import date

# Initialize database
print("=" * 60)
print("Testing NBA Data Layer Setup")
print("=" * 60)

# Step 1: Initialize database
print("\n📦 Step 1: Initialize database...")
try:
    from app.nba.database import init_database, get_db_session
    init_database()
    print("   ✅ Database initialized")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Step 2: Bootstrap teams
print("\n🏀 Step 2: Bootstrap NBA teams...")
try:
    from app.nba.database import bootstrap_teams
    team_count = bootstrap_teams()
    print(f"   ✅ Loaded {team_count} teams")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Step 3: Test team lookup
print("\n🔍 Step 3: Test team lookup...")
try:
    from app.nba.models import DimTeam
    db = get_db_session()
    
    # Find Lakers
    lakers = db.query(DimTeam).filter_by(abbreviation="LAL").first()
    if lakers:
        print(f"   ✅ Found: {lakers.full_name} (ID: {lakers.team_id})")
    else:
        print("   ⚠️ Lakers not found (might need different lookup)")
    
    # Count all teams
    total = db.query(DimTeam).count()
    print(f"   ✅ Total teams in database: {total}")
    
    db.close()
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Step 4: Test heuristics (without game data)
print("\n📊 Step 4: Test heuristics engine...")
try:
    from app.nba.heuristics import NBAHeuristics
    db = get_db_session()
    
    heuristics = NBAHeuristics(db)
    
    # Get Lakers team ID
    lakers = db.query(DimTeam).filter_by(abbreviation="LAL").first()
    if lakers:
        rest = heuristics.calculate_rest_advantage(lakers.team_id, date.today())
        print(f"   ✅ Rest advantage calculated: {rest}")
    else:
        print("   ⚠️ Skipping (no team found)")
    
    db.close()
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Step 5: Test cache
print("\n💾 Step 5: Test cache layer...")
try:
    from app.nba.cache import get_cache
    
    cache = get_cache()
    
    # Set and get
    cache.set("test:key", {"hello": "world"}, ttl=60)
    result = cache.get("test:key")
    
    if result and result.get("hello") == "world":
        print("   ✅ Cache working: set/get verified")
    else:
        print("   ❌ Cache not working properly")
    
    stats = cache.get_stats()
    print(f"   ✅ Cache stats: {stats}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "=" * 60)
print("✅ NBA Data Layer Setup Complete!")
print("=" * 60)

print("\n📋 Available API endpoints:")
print("   - GET /api/nba/teams")
print("   - GET /api/nba/games/today")
print("   - GET /api/nba/edge/{team_a}/{team_b}")
print("   - GET /api/nba/rest/{team}")
print("   - GET /api/nba/tank/{team}")
print("   - GET /api/nba/injuries/{team}")
print("   - GET /api/nba/standings/{team}")
print("   - GET /api/nba/matchup/{team_a}/{team_b}")
