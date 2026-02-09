#!/usr/bin/env python3
"""
Debug script: Trace leg building through pipeline.
"""
import sys
sys.path.insert(0, '/var/lib/openbot/workdir/target')

from app.airlock import airlock_ingest
from app.pipeline import run_evaluation, _parse_bet_text, recognize_entities

# Test cases
test_inputs = [
    "LAL -4.5",
    "LeBron James over 27.5 points",
    "Lakers +3.5, Celtics ML",
    "LAL -4.5 + GSW ML",
    "Lakers -5 and Celtics +3",
]

print("=" * 70)
print("LEG BUILDING DEBUG")
print("=" * 70)

for bet_text in test_inputs:
    print(f"\n📝 Input: '{bet_text}'")
    print("-" * 70)
    
    # Step 1: Airlock validation
    try:
        normalized = airlock_ingest(bet_text, tier="BETTER")
        print(f"✅ Airlock: Validated (tier={normalized.tier})")
    except Exception as e:
        print(f"❌ Airlock failed: {e}")
        continue
    
    # Step 2: Entity recognition
    entities = recognize_entities(bet_text)
    print(f"🔍 Entities: sport={entities.get('sport_guess')}, teams={entities.get('teams_mentioned')}")
    
    # Step 3: Parse legs
    blocks = _parse_bet_text(bet_text)
    print(f"🧱 Blocks: {len(blocks)} leg(s)")
    
    for i, block in enumerate(blocks):
        print(f"   Leg {i+1}: {block.bet_type.value} | '{block.selection[:40]}...' | frag={block.base_fragility}")
    
    # Step 4: Full evaluation
    try:
        result = run_evaluation(normalized)
        print(f"📊 Result: confidence={result.explain.get('confidence', 'N/A')}")
        if hasattr(result, 'nba_heuristics'):
            print(f"🏀 NBA: {result.nba_heuristics}")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
