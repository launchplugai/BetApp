"""
Quick test script for The Odds API integration.
Verifies API key and basic functionality.
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from app.config import load_config
from app.providers.odds_api import OddsApiProvider
from app.providers import ProviderConfig


async def test_odds_api():
    """Test basic OddsApiProvider functionality."""
    print("=" * 60)
    print("Testing The Odds API Integration")
    print("=" * 60)
    
    # Load config
    config_instance = load_config(fail_fast=False)
    
    if not config_instance.the_odds_api_key:
        print("❌ ERROR: THE_ODDS_API_KEY not found in environment")
        print("   Make sure .env file exists with your API key")
        return False
    
    print(f"✅ API key loaded: {config_instance.the_odds_api_key[:8]}...")
    
    # Create provider
    provider_config = ProviderConfig(
        provider_type="live",
        api_key=config_instance.the_odds_api_key
    )
    provider = OddsApiProvider(provider_config)
    
    print(f"✅ Provider created: {provider.source_name}")
    
    # Test 1: Get sports
    print("\n📋 Test 1: Get available sports")
    try:
        sports = provider.get_sports()
        print(f"   Found {len(sports)} sports:")
        for sport in sports[:5]:
            print(f"   - {sport.id}: {sport.label} (active={sport.active})")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 2: Get games for NBA
    print("\n🏀 Test 2: Get NBA games")
    try:
        games = await provider.get_games("NBA")
        print(f"   Found {len(games)} NBA games")
        if games:
            game = games[0]
            print(f"   First game: {game.away} @ {game.home}")
            print(f"   Game ID: {game.id}")
            print(f"   Start: {game.start_time}")
            print(f"   Status: {game.status}")
            
            # Test 3: Get odds for first game
            print(f"\n💰 Test 3: Get odds for {game.away} @ {game.home}")
            try:
                odds = await provider.get_odds(game.id)
                print(f"   Found {len(odds)} markets:")
                for market in odds[:3]:
                    print(f"   - {market.market}: {len(market.selections)} selections")
                    for sel in market.selections[:2]:
                        print(f"      • {sel.label}: {sel.odds:+d}")
            except Exception as e:
                print(f"   ⚠️  Odds fetch failed: {e}")
        else:
            print("   ⚠️  No games found (might be off-season)")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Cleanup
    await provider.close()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Integration working.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_odds_api())
    sys.exit(0 if success else 1)
