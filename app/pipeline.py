# app/pipeline.py
"""
Pipeline Facade - Single entry point for all evaluation requests.

This is the ONLY place where core evaluation is called.
All routes MUST go through this facade:

    Airlock (validation) → Pipeline (evaluation) → Route (HTTP response)

The pipeline:
1. Parses text input into BetBlocks
2. Calls the canonical evaluate_parlay()
3. Fetches external context (Sprint 3: NBA availability)
4. Wraps response with plain-English explanations
5. Applies tier-based filtering

Routes should NOT:
- Import core.evaluation directly
- Reimplement parsing/summary logic
- Call evaluate_parlay() themselves
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.airlock import NormalizedInput, Tier

# Core evaluation - the ONLY direct import of core.evaluation in app/
from core.evaluation import EvaluationResponse, evaluate_parlay
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
)

# Context ingestion (Sprint 3)
from context.service import get_context
from context.apply import apply_context, ContextImpact

# Alerts (Sprint 4)
from alerts.service import check_for_alerts

# Sherlock integration (Ticket 17)
from app.sherlock_hook import run_sherlock_hook
from app.config import load_config

_logger = logging.getLogger(__name__)

# Load config for feature flags (Ticket 17)
_config = load_config(fail_fast=False)


# =============================================================================
# Signal System — Single Source of Truth (Ticket 5)
# =============================================================================

SIGNAL_MAP = {
    "blue": {"label": "Strong", "css": "signal-blue"},
    "green": {"label": "Solid", "css": "signal-green"},
    "yellow": {"label": "Fixable", "css": "signal-yellow"},
    "red": {"label": "Fragile", "css": "signal-red"},
}


# =============================================================================
# Pipeline Response
# =============================================================================


@dataclass(frozen=True)
class PipelineResponse:
    """
    Unified response from the evaluation pipeline.

    Contains:
    - Raw evaluation response from core engine
    - Plain-English interpretation
    - Tier-filtered explain content
    - Context data (Sprint 3)
    - Metadata for logging
    """
    # Core evaluation result
    evaluation: EvaluationResponse

    # Plain-English interpretation (always included)
    interpretation: dict

    # Explain content (tier-filtered)
    explain: dict

    # Context impact (Sprint 3 - additive only, does not modify engine)
    context: Optional[dict] = None

    # Primary failure diagnosis + delta preview (Ticket 4)
    primary_failure: Optional[dict] = None
    delta_preview: Optional[dict] = None

    # Signal system (Ticket 5)
    signal_info: Optional[dict] = None

    # Entity recognition (Ticket 14)
    entities: Optional[dict] = None

    # Sprint 2: Secondary factors (runners-up from scoring logic)
    secondary_factors: Optional[list] = None

    # Sprint 2: Human summary (2-3 sentences, always included)
    human_summary: Optional[str] = None

    # Ticket 17: Sherlock integration result (None if disabled)
    sherlock_result: Optional[dict] = None

    # Metadata
    leg_count: int = 0
    tier: str = "good"


# =============================================================================
# Entity Recognition (Ticket 14 — Sprint 2)
# =============================================================================

# NBA teams: keyword → abbreviation
_NBA_TEAMS = {
    "lakers": "LAL", "lal": "LAL", "los angeles lakers": "LAL",
    "celtics": "BOS", "bos": "BOS", "boston celtics": "BOS",
    "nuggets": "DEN", "den": "DEN", "denver": "DEN",
    "bucks": "MIL", "mil": "MIL", "milwaukee": "MIL",
    "warriors": "GSW", "gsw": "GSW", "golden state": "GSW",
    "suns": "PHX", "phx": "PHX", "phoenix": "PHX",
    "76ers": "PHI", "phi": "PHI", "sixers": "PHI", "philadelphia": "PHI",
    "mavericks": "DAL", "dal": "DAL", "dallas": "DAL", "mavs": "DAL",
    "heat": "MIA", "mia": "MIA", "miami": "MIA",
    "nets": "BKN", "bkn": "BKN", "brooklyn": "BKN",
    "knicks": "NYK", "nyk": "NYK",
    "bulls": "CHI", "chi": "CHI", "chicago": "CHI",
    "clippers": "LAC", "lac": "LAC",
    "thunder": "OKC", "okc": "OKC", "oklahoma": "OKC",
    "timberwolves": "MIN", "min": "MIN", "minnesota": "MIN", "wolves": "MIN",
    "kings": "SAC", "sac": "SAC", "sacramento": "SAC",
    "pelicans": "NOP", "nop": "NOP", "new orleans": "NOP",
    "grizzlies": "MEM", "mem": "MEM", "memphis": "MEM",
    "cavaliers": "CLE", "cle": "CLE", "cleveland": "CLE", "cavs": "CLE",
    "hawks": "ATL", "atl": "ATL", "atlanta": "ATL",
    "raptors": "TOR", "tor": "TOR", "toronto": "TOR",
    "pacers": "IND", "ind": "IND", "indiana": "IND",
    "hornets": "CHA", "cha": "CHA", "charlotte": "CHA",
    "wizards": "WAS", "was": "WAS", "washington": "WAS",
    "magic": "ORL", "orl": "ORL", "orlando": "ORL",
    "pistons": "DET", "det": "DET", "detroit": "DET",
    "jazz": "UTA", "uta": "UTA", "utah": "UTA",
    "rockets": "HOU", "hou": "HOU", "houston": "HOU",
    "spurs": "SAS", "sas": "SAS", "san antonio": "SAS",
    "trail blazers": "POR", "por": "POR", "portland": "POR", "blazers": "POR",
}

# NFL teams: keyword → abbreviation
_NFL_TEAMS = {
    "chiefs": "KC", "kc": "KC", "kansas city": "KC",
    "eagles": "PHI-NFL", "bills": "BUF", "buf": "BUF", "buffalo": "BUF",
    "cowboys": "DAL-NFL", "49ers": "SF", "niners": "SF", "san francisco": "SF",
    "ravens": "BAL", "bal": "BAL", "baltimore": "BAL",
    "bengals": "CIN", "cin": "CIN", "cincinnati": "CIN",
    "dolphins": "MIA-NFL", "lions": "DET-NFL", "packers": "GB", "gb": "GB",
    "green bay": "GB", "steelers": "PIT", "pit": "PIT", "pittsburgh": "PIT",
    "chargers": "LAC-NFL", "rams": "LAR", "lar": "LAR",
    "seahawks": "SEA", "sea": "SEA", "seattle": "SEA",
    "jaguars": "JAX", "jax": "JAX", "jacksonville": "JAX",
    "patriots": "NE", "ne": "NE", "new england": "NE",
    "giants": "NYG", "nyg": "NYG", "jets": "NYJ", "nyj": "NYJ",
    "broncos": "DEN-NFL", "texans": "HOU-NFL", "titans": "TEN", "ten": "TEN",
    "colts": "IND-NFL", "raiders": "LV", "lv": "LV", "las vegas": "LV",
    "saints": "NO", "no": "NO", "panthers": "CAR", "car": "CAR", "carolina": "CAR",
    "bears": "CHI-NFL", "commanders": "WAS-NFL", "falcons": "ATL-NFL",
    "cardinals": "ARI", "ari": "ARI", "arizona": "ARI",
    "buccaneers": "TB", "tb": "TB", "bucs": "TB", "tampa": "TB", "tampa bay": "TB",
    "vikings": "MIN-NFL",
}

# Known NBA players: nickname/partial → canonical name
_NBA_PLAYERS = {
    "lebron james": "LeBron James", "lebron": "LeBron James",
    "anthony davis": "Anthony Davis", "ad": "Anthony Davis",
    "jaylen brown": "Jaylen Brown", "jayson tatum": "Jayson Tatum", "tatum": "Jayson Tatum",
    "nikola jokic": "Nikola Jokic", "jokic": "Nikola Jokic",
    "jamal murray": "Jamal Murray",
    "giannis antetokounmpo": "Giannis Antetokounmpo", "giannis": "Giannis Antetokounmpo",
    "damian lillard": "Damian Lillard", "lillard": "Damian Lillard", "dame": "Damian Lillard",
    "stephen curry": "Stephen Curry", "curry": "Stephen Curry", "steph curry": "Stephen Curry",
    "klay thompson": "Klay Thompson",
    "kevin durant": "Kevin Durant", "durant": "Kevin Durant", "kd": "Kevin Durant",
    "devin booker": "Devin Booker", "booker": "Devin Booker",
    "joel embiid": "Joel Embiid", "embiid": "Joel Embiid",
    "tyrese maxey": "Tyrese Maxey", "maxey": "Tyrese Maxey",
    "luka doncic": "Luka Doncic", "luka": "Luka Doncic", "doncic": "Luka Doncic",
    "kyrie irving": "Kyrie Irving", "kyrie": "Kyrie Irving",
    "jimmy butler": "Jimmy Butler", "butler": "Jimmy Butler",
    "bam adebayo": "Bam Adebayo", "bam": "Bam Adebayo",
    "shai gilgeous-alexander": "Shai Gilgeous-Alexander", "sga": "Shai Gilgeous-Alexander",
    "donovan mitchell": "Donovan Mitchell", "mitchell": "Donovan Mitchell",
    "trae young": "Trae Young", "trae": "Trae Young",
    "lamelo ball": "LaMelo Ball", "lamelo": "LaMelo Ball",
    "paolo banchero": "Paolo Banchero", "paolo": "Paolo Banchero",
    "victor wembanyama": "Victor Wembanyama", "wemby": "Victor Wembanyama",
    "ja morant": "Ja Morant", "ja": "Ja Morant",
    "ant edwards": "Anthony Edwards", "anthony edwards": "Anthony Edwards",
    "de'aaron fox": "De'Aaron Fox", "fox": "De'Aaron Fox",
}

# NFL players
_NFL_PLAYERS = {
    "patrick mahomes": "Patrick Mahomes", "mahomes": "Patrick Mahomes",
    "josh allen": "Josh Allen", "jalen hurts": "Jalen Hurts", "hurts": "Jalen Hurts",
    "lamar jackson": "Lamar Jackson", "lamar": "Lamar Jackson",
    "joe burrow": "Joe Burrow", "burrow": "Joe Burrow",
    "travis kelce": "Travis Kelce", "kelce": "Travis Kelce",
    "tyreek hill": "Tyreek Hill", "tyreek": "Tyreek Hill",
    "derrick henry": "Derrick Henry",
    "ceedee lamb": "CeeDee Lamb", "ceedee": "CeeDee Lamb",
    "justin jefferson": "Justin Jefferson", "jj": "Justin Jefferson",
    "davante adams": "Davante Adams",
    "ja'marr chase": "Ja'Marr Chase", "jamarr chase": "Ja'Marr Chase",
    "saquon barkley": "Saquon Barkley", "saquon": "Saquon Barkley",
    "christian mccaffrey": "Christian McCaffrey", "cmc": "Christian McCaffrey",
    "dak prescott": "Dak Prescott", "dak": "Dak Prescott",
    "stefon diggs": "Stefon Diggs", "diggs": "Stefon Diggs",
}

# Market keywords → canonical market type
_MARKET_KEYWORDS = {
    "spread": "spread",
    "moneyline": "ml", "money line": "ml", "ml": "ml",
    "over": "total", "under": "total", "o/u": "total", "total": "total",
    "points": "points", "pts": "points",
    "rebounds": "rebounds", "reb": "rebounds", "rebs": "rebounds",
    "assists": "assists", "ast": "assists", "asts": "assists",
    "touchdowns": "td", "td": "td", "tds": "td", "anytime td": "td",
    "first td": "td", "atts": "td",
    "yards": "yardage", "rushing yards": "yardage", "receiving yards": "yardage",
    "passing yards": "yardage",
    "threes": "threes", "3-pointers": "threes", "3pt": "threes", "three pointers": "threes",
    "steals": "steals", "blocks": "blocks", "blk": "blocks",
    "strikeouts": "strikeouts", "k's": "strikeouts",
    "home run": "hr", "hr": "hr", "homer": "hr",
    "hits": "hits", "rbi": "rbi",
    "prop": "prop",
}

# Sport detection keywords
_SPORT_KEYWORDS = {
    "nba": "nba", "basketball": "nba",
    "nfl": "nfl", "football": "nfl", "touchdown": "nfl",
    "mlb": "mlb", "baseball": "mlb",
    "nhl": "nhl", "hockey": "nhl",
    "soccer": "soccer", "mls": "soccer", "premier league": "soccer",
    "ufc": "mma", "mma": "mma",
}


def _keyword_match(key: str, text: str) -> bool:
    """Match keyword in text, using word boundary for short keys (<=3 chars)."""
    import re
    if len(key) <= 3:
        return bool(re.search(r'\b' + re.escape(key) + r'\b', text))
    return key in text


def recognize_entities(text: str) -> dict:
    """
    Extract structured entities from bet text using heuristic keyword matching.

    Returns:
        dict with sport_guess, teams_mentioned, players_mentioned, markets_detected
    """
    text_lower = text.lower()

    # --- Teams ---
    teams_found: list[str] = []
    nba_team_hits = 0
    nfl_team_hits = 0

    # Check NBA teams (longer keys first to avoid partial matches)
    for key in sorted(_NBA_TEAMS.keys(), key=len, reverse=True):
        if _keyword_match(key, text_lower):
            abbr = _NBA_TEAMS[key]
            if abbr not in teams_found:
                teams_found.append(abbr)
                nba_team_hits += 1

    # Check NFL teams
    for key in sorted(_NFL_TEAMS.keys(), key=len, reverse=True):
        if _keyword_match(key, text_lower):
            abbr = _NFL_TEAMS[key]
            if abbr not in teams_found:
                teams_found.append(abbr)
                nfl_team_hits += 1

    # --- Players ---
    players_found: list[str] = []
    nba_player_hits = 0
    nfl_player_hits = 0

    for key in sorted(_NBA_PLAYERS.keys(), key=len, reverse=True):
        if _keyword_match(key, text_lower):
            name = _NBA_PLAYERS[key]
            if name not in players_found:
                players_found.append(name)
                nba_player_hits += 1

    for key in sorted(_NFL_PLAYERS.keys(), key=len, reverse=True):
        if _keyword_match(key, text_lower):
            name = _NFL_PLAYERS[key]
            if name not in players_found:
                players_found.append(name)
                nfl_player_hits += 1

    # --- Markets ---
    markets_found: list[str] = []
    for key in sorted(_MARKET_KEYWORDS.keys(), key=len, reverse=True):
        if _keyword_match(key, text_lower):
            market = _MARKET_KEYWORDS[key]
            if market not in markets_found:
                markets_found.append(market)

    # Pattern-based spread detection: +/-N.N (e.g. -5.5, +3)
    import re
    if "spread" not in markets_found and re.search(r'[+-]\d+\.?\d*', text_lower):
        markets_found.append("spread")

    # --- Sport guess ---
    sport_guess = "unknown"

    # Explicit sport keyword takes priority
    for key, sport in _SPORT_KEYWORDS.items():
        if key in text_lower:
            sport_guess = sport
            break

    # Infer from entity evidence if still unknown
    if sport_guess == "unknown":
        nba_evidence = nba_team_hits + nba_player_hits
        nfl_evidence = nfl_team_hits + nfl_player_hits
        # Prop markets like td/yardage strongly suggest NFL
        nfl_market_evidence = sum(1 for m in markets_found if m in ("td", "yardage"))
        nba_market_evidence = sum(1 for m in markets_found if m in ("points", "rebounds", "assists", "threes", "steals", "blocks"))
        nfl_evidence += nfl_market_evidence
        nba_evidence += nba_market_evidence

        if nba_evidence > 0 and nba_evidence >= nfl_evidence:
            sport_guess = "nba"
        elif nfl_evidence > 0:
            sport_guess = "nfl"
        elif any(m in markets_found for m in ("hr", "strikeouts", "hits", "rbi")):
            sport_guess = "mlb"

    return {
        "sport_guess": sport_guess,
        "teams_mentioned": teams_found,
        "players_mentioned": players_found,
        "markets_detected": markets_found,
    }


def _compute_volatility_flag(markets: list[str], leg_count: int, same_game_count: int) -> str:
    """
    Compute volatility flag based on market types and structure.

    Rules (heuristic, deterministic):
    - Props = High base
    - Totals = Med-High base
    - Spreads = Med base
    - ML = Low-Med base
    - Boosters: same-game stack +1, 4+ legs +1
    - Cap at High

    Returns: "low", "medium", "med-high", or "high"
    """
    # Base volatility from market types
    base_scores = {
        "points": 3, "rebounds": 3, "assists": 3, "td": 3, "yardage": 3,
        "threes": 3, "steals": 3, "blocks": 3, "strikeouts": 3, "hr": 3,
        "hits": 3, "rbi": 3, "prop": 3,  # Props = High
        "total": 2,  # Totals = Med-High
        "spread": 1,  # Spreads = Med
        "ml": 0,  # ML = Low-Med
    }

    # Compute max base score from markets
    market_score = 0
    for m in markets:
        market_score = max(market_score, base_scores.get(m, 0))

    # If no markets detected, use neutral
    if not markets:
        market_score = 1

    # Boosters
    booster = 0
    if same_game_count >= 2:
        booster += 1  # Same-game stack
    if leg_count >= 4:
        booster += 1  # 4+ legs

    total_score = market_score + booster

    # Map to labels (cap at high)
    if total_score >= 3:
        return "high"
    elif total_score == 2:
        return "med-high"
    elif total_score == 1:
        return "medium"
    else:
        return "low"


def _detect_same_game_indicator(blocks: list) -> dict:
    """
    Detect same-game parlay indicators from blocks.

    Returns dict with:
    - has_same_game: bool
    - same_game_count: int (max legs in any single game)
    - same_game_teams: list of team identifiers involved
    """
    if not blocks:
        return {"has_same_game": False, "same_game_count": 0, "same_game_teams": []}

    game_id_counts: dict[str, list] = {}
    for b in blocks:
        gid = b.game_id
        game_id_counts.setdefault(gid, []).append(b)

    # Find games with multiple legs
    same_game_groups = {gid: blks for gid, blks in game_id_counts.items() if len(blks) > 1}

    if not same_game_groups:
        return {"has_same_game": False, "same_game_count": 0, "same_game_teams": []}

    max_count = max(len(blks) for blks in same_game_groups.values())
    teams = [gid.replace("game_", "") for gid in same_game_groups.keys() if gid.startswith("game_")]

    return {
        "has_same_game": True,
        "same_game_count": max_count,
        "same_game_teams": teams,
    }


# =============================================================================
# Per-Leg Market Detection (Ticket 14)
# =============================================================================


def _detect_leg_markets(bet_text: str) -> list[dict]:
    """
    Split input into legs and detect the market type for each leg.

    Returns a list of dicts: [{"text": raw_leg, "bet_type": BetType, "base_fragility": float}, ...]
    """
    text_lower = bet_text.lower()

    # Split on common leg delimiters
    import re
    parts = re.split(r'\s*\+\s*|\s*,\s*|\s+and\s+', text_lower)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        parts = [text_lower]

    legs = []
    for part in parts:
        is_prop = any(w in part for w in [
            'yards', 'points', 'rebounds', 'assists', 'touchdowns', 'td',
            'tds', 'threes', '3pt', 'steals', 'blocks', 'strikeouts',
            'home run', 'hr', 'rbi', 'hits', 'receptions', 'rec',
        ])
        is_total = any(w in part for w in ['over', 'under', 'o/', 'u/'])
        is_spread = bool(re.search(r'[+-]\d+\.?\d*', part)) and not is_total

        if is_prop:
            legs.append({"text": part, "bet_type": BetType.PLAYER_PROP, "base_fragility": 0.20})
        elif is_total:
            legs.append({"text": part, "bet_type": BetType.TOTAL, "base_fragility": 0.12})
        elif is_spread:
            legs.append({"text": part, "bet_type": BetType.SPREAD, "base_fragility": 0.10})
        else:
            legs.append({"text": part, "bet_type": BetType.ML, "base_fragility": 0.08})

    return legs


# =============================================================================
# Text Parsing (moved from leading_light.py)
# =============================================================================


def _parse_bet_text(bet_text: str) -> list[BetBlock]:
    """
    Parse bet_text into BetBlock objects.

    Uses per-leg market detection so mixed slips (spread + prop + ML)
    produce blocks with distinct bet types and fragility values.
    Does NOT implement scoring logic - just format conversion.
    """
    import re as _re

    detected_legs = _detect_leg_markets(bet_text)
    leg_count = min(len(detected_legs), 6)

    # Entity recognition for game_id inference
    entities = recognize_entities(bet_text)
    sport = entities["sport_guess"] if entities["sport_guess"] != "unknown" else "generic"
    teams = entities["teams_mentioned"]

    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    modifiers = ContextModifiers(
        weather=default_mod,
        injury=default_mod,
        trade=default_mod,
        role=default_mod,
    )

    blocks = []
    for i in range(leg_count):
        leg = detected_legs[i]
        # Assign game_id: legs mentioning the same team share a game_id
        game_id = f"game_{i+1}"
        leg_text = leg["text"]
        for t_key, t_abbr in _NBA_TEAMS.items():
            if t_key in leg_text and t_abbr in teams:
                game_id = f"game_{t_abbr}"
                break
        else:
            for t_key, t_abbr in _NFL_TEAMS.items():
                if t_key in leg_text:
                    game_id = f"game_{t_abbr}"
                    break

        block = BetBlock(
            block_id=uuid4(),
            sport=sport,
            game_id=game_id,
            bet_type=leg["bet_type"],
            selection=leg["text"][:80] or f"Leg {i+1}",
            base_fragility=leg["base_fragility"],
            context_modifiers=modifiers,
            correlation_tags=(),
            effective_fragility=leg["base_fragility"],
            player_id=None,
            team_id=None,
        )
        blocks.append(block)

    # Fallback: if no legs were parsed, create one generic block
    if not blocks:
        blocks.append(BetBlock(
            block_id=uuid4(),
            sport=sport,
            game_id="game_1",
            bet_type=BetType.ML,
            selection=bet_text[:80],
            base_fragility=0.08,
            context_modifiers=modifiers,
            correlation_tags=(),
            effective_fragility=0.08,
            player_id=None,
            team_id=None,
        ))

    return blocks


# =============================================================================
# Summary Generation (moved from leading_light.py)
# =============================================================================


def _generate_summary(response: EvaluationResponse, leg_count: int) -> list[str]:
    """Generate plain-English summary bullets from evaluation response."""
    summary = [
        f"Detected {leg_count} leg(s) in this bet",
        f"Risk level: {response.inductor.level.value.upper()}",
        f"Final fragility: {response.metrics.final_fragility:.2f}",
    ]

    if response.metrics.correlation_penalty > 0:
        summary.append(f"Correlation penalty applied: +{response.metrics.correlation_penalty:.2f}")

    if len(response.correlations) > 0:
        summary.append(f"Found {len(response.correlations)} correlation(s) between legs")

    return summary


def _generate_alerts(response: EvaluationResponse) -> list[str]:
    """Generate alerts from evaluation response."""
    alerts = []

    # Check for DNA violations
    if response.dna.violations:
        for violation in response.dna.violations:
            alerts.append(violation)

    # Check for high correlation
    if response.metrics.correlation_multiplier >= 1.5:
        alerts.append("High correlation detected between selections")

    # Check for critical risk
    if response.inductor.level.value == "critical":
        alerts.append("Critical risk level - structure exceeds safe thresholds")

    return alerts


def _interpret_fragility(final_fragility: float) -> dict:
    """
    Generate user-friendly interpretation of fragility score.

    Maps 0-100 scale to buckets with plain-English meaning and actionable advice.
    Does NOT modify engine metrics - interpretation layer only.
    """
    # Clamp for display (engine can produce values outside 0-100)
    display_value = max(0.0, min(100.0, final_fragility))

    # Determine bucket
    if final_fragility <= 15:
        bucket = "low"
        meaning = "Few dependencies; most paths lead to success."
        what_to_do = "Structure is solid; proceed with confidence."
    elif final_fragility <= 35:
        bucket = "medium"
        meaning = "Moderate complexity; several things must align."
        what_to_do = "Review each leg independently before committing."
    elif final_fragility <= 60:
        bucket = "high"
        meaning = "Many things must go right; one miss breaks the ticket."
        what_to_do = "Reduce legs or remove correlated/prop legs to lower failure points."
    else:  # > 60
        bucket = "critical"
        meaning = "Extreme fragility; compounding failure paths."
        what_to_do = "Simplify significantly or avoid this structure entirely."

    return {
        "scale": "0-100",
        "value": final_fragility,
        "display_value": display_value,
        "bucket": bucket,
        "meaning": meaning,
        "what_to_do": what_to_do,
    }


# =============================================================================
# Tier Filtering (moved from leading_light.py)
# =============================================================================


def _apply_tier_filtering(tier: Tier, explain: dict, evaluation=None, blocks=None, primary_failure=None) -> dict:
    """
    Apply tier-based filtering to explain content.

    Tier rules:
    - GOOD: Structured output (signal, grade, contributors, warnings, tips, removals)
    - BETTER: summary only
    - BEST: summary + alerts + recommended_next_step
    """
    if tier == Tier.GOOD:
        return _build_good_tier_output(evaluation, blocks, primary_failure) if evaluation else {}
    elif tier == Tier.BETTER:
        return {"summary": explain.get("summary", [])}
    else:  # BEST
        return explain


def _build_good_tier_output(evaluation, blocks, primary_failure=None) -> dict:
    """
    Build structured GOOD tier output from evaluation response.

    Derives signal, grade, contributors, warnings, tips, and removal
    suggestions from existing evaluation metrics. Does NOT modify engine math.
    """
    metrics = evaluation.metrics
    final_fragility = metrics.final_fragility

    # Use single source of truth (red rarity enforced)
    signal = _fragility_to_signal(final_fragility, evaluation)

    # Grade: A=blue, B=green, C=yellow, D=red
    grade_map = {"blue": "A", "green": "B", "yellow": "C", "red": "D"}
    grade = grade_map[signal]

    # Contributors: factors that materially affect risk
    contributors = []

    if metrics.correlation_penalty > 0:
        impact = "high" if metrics.correlation_penalty > 5 else ("medium" if metrics.correlation_penalty > 2 else "low")
        contributors.append({"type": "correlation", "impact": impact})

    if metrics.leg_penalty > 0:
        impact = "high" if metrics.leg_penalty > 20 else ("medium" if metrics.leg_penalty > 10 else "low")
        contributors.append({"type": "leg_count", "impact": impact})

    if len(evaluation.correlations) > 0:
        impact = "high" if len(evaluation.correlations) > 2 else ("medium" if len(evaluation.correlations) > 1 else "low")
        contributors.append({"type": "dependency", "impact": impact})

    # Check for prop-type volatility from blocks
    if blocks:
        prop_count = sum(1 for b in blocks if b.base_fragility >= 0.20)
        if prop_count > 0:
            impact = "high" if prop_count > 2 else ("medium" if prop_count > 1 else "low")
            contributors.append({"type": "volatility", "impact": impact})

    # Warnings: specific risk statements referencing primary failure
    warnings = []
    pf_type = primary_failure.get("type") if primary_failure else None
    pf_action = primary_failure.get("fastestFix", {}).get("action") if primary_failure else None

    if pf_type == "correlation" and metrics.correlation_multiplier >= 1.5:
        warnings.append(f"Correlation penalty: +{metrics.correlation_penalty:.1f}pt from shared outcomes")
    elif pf_type == "correlation" and metrics.correlation_penalty > 0:
        warnings.append(f"Correlated selections add +{metrics.correlation_penalty:.1f}pt penalty")
    if pf_type == "leg_count" and metrics.leg_penalty > 10:
        warnings.append(f"Leg penalty: +{metrics.leg_penalty:.1f}pt from {len(blocks or [])} selections")
    if pf_type == "volatility":
        vol_prop_count = sum(1 for b in (blocks or []) if b.base_fragility >= 0.20)
        warnings.append(f"{vol_prop_count} prop-type bet{'s' if vol_prop_count != 1 else ''} with elevated base fragility")
    if pf_type == "dependency" and len(evaluation.correlations) > 1:
        warnings.append(f"{len(evaluation.correlations)} outcome pairs share dependent variables")
    # Ticket 14: new failure type warnings
    if pf_type == "prop_density":
        pd_prop_count = sum(1 for b in (blocks or []) if b.bet_type == BetType.PLAYER_PROP)
        warnings.append(f"{pd_prop_count} of {len(blocks or [])} legs are player props — high variance concentration")
    if pf_type == "same_game_dependency":
        game_counts: dict[str, int] = {}
        for b in (blocks or []):
            game_counts[b.game_id] = game_counts.get(b.game_id, 0) + 1
        max_sg = max(game_counts.values(), default=0)
        if max_sg >= 2:
            warnings.append(f"{max_sg} legs from the same game — outcomes are not independent")
    if pf_type == "market_conflict":
        warnings.append("Overlapping market types (e.g. total + spread on same game) amplify correlation")
    if pf_type == "weak_clarity":
        warnings.append("Limited entity recognition — evaluation is based on structure only")
    # Secondary warnings (only if they reference a real factor)
    if metrics.correlation_multiplier >= 1.5 and pf_type != "correlation":
        warnings.append(f"Correlation multiplier at {metrics.correlation_multiplier:.1f}x")
    if metrics.leg_penalty > 20 and pf_type != "leg_count":
        warnings.append(f"{len(blocks or [])} legs add +{metrics.leg_penalty:.1f}pt structural penalty")

    # Tips: actionable, referencing primary failure fix path
    tips = []
    if pf_action == "remove_leg" and metrics.leg_penalty > 10:
        tips.append(f"Remove 1 leg to reduce penalty by ~{metrics.leg_penalty * 0.3:.0f}pt")
    if pf_action == "split_parlay":
        tips.append("Split correlated legs into separate tickets")
    if pf_action in ("reduce_props", "swap_leg") and pf_type != "market_conflict":
        tips.append("Replace prop bets with totals or spreads")
    if pf_action == "swap_leg" and pf_type == "market_conflict":
        tips.append("Replace one of the conflicting markets with a moneyline or player prop")
    if pf_action == "reduce_same_game":
        tips.append("Move same-game legs to separate tickets")
    if pf_action == "clarify_input":
        tips.append("Include team names, player names, and bet types for better analysis")
    if pf_action == "reduce_props" and pf_type == "prop_density":
        tips.append("Swap 1-2 props for spread or moneyline bets to diversify")
    # Secondary tips (only if specific)
    if len(blocks or []) >= 4 and pf_action != "remove_leg":
        tips.append(f"Reduce from {len(blocks)} to {max(2, len(blocks) - 2)} legs")
    if metrics.correlation_penalty > 0 and pf_action != "split_parlay":
        tips.append("Separate correlated selections into distinct tickets")

    # Removal suggestions: blocks involved in most correlations
    removal_suggestions = []
    if evaluation.correlations:
        block_corr_count = {}
        for corr in evaluation.correlations:
            block_corr_count[str(corr.block_a)] = block_corr_count.get(str(corr.block_a), 0) + 1
            block_corr_count[str(corr.block_b)] = block_corr_count.get(str(corr.block_b), 0) + 1
        # Sort by frequency, suggest top offenders
        sorted_blocks = sorted(block_corr_count.items(), key=lambda x: x[1], reverse=True)
        for block_id, count in sorted_blocks[:2]:
            if count > 0:
                removal_suggestions.append(block_id)

    return {
        "overallSignal": signal,
        "grade": grade,
        "fragilityScore": final_fragility,
        "contributors": contributors,
        "warnings": warnings,
        "tips": tips,
        "removalSuggestions": removal_suggestions,
    }


def _fragility_to_signal(fragility: float, evaluation=None) -> str:
    """
    Map fragility score to signal color.

    Red rarity enforcement: red ONLY when fragility bucket is critical
    (>60) AND inductor level is critical. Otherwise caps at yellow.
    """
    if fragility <= 15:
        return "blue"
    elif fragility <= 35:
        return "green"
    elif fragility <= 60:
        return "yellow"
    else:
        # Red rarity: only if inductor is also critical
        if evaluation and evaluation.inductor.level.value == "critical":
            return "red"
        # Inductor not critical — cap at yellow
        return "yellow"


def _signal_to_grade(signal: str) -> str:
    """Map signal to grade letter."""
    return {"blue": "A", "green": "B", "yellow": "C", "red": "D"}[signal]


def _build_signal_info(evaluation, primary_failure, delta_preview) -> dict:
    """
    Build signal info with label and why-one-liner.

    Uses SIGNAL_MAP as single source of truth.
    """
    fragility = evaluation.metrics.final_fragility
    signal = _fragility_to_signal(fragility, evaluation)
    label = SIGNAL_MAP[signal]["label"]

    # Build why-one-liner from primaryFailure
    pf_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    pf_severity = primary_failure.get("severity", "low") if primary_failure else "low"

    signal_line = f"Main risk: {pf_type.replace('_', ' ')} ({pf_severity})"

    # Append fix hint if deltaPreview shows improvement
    if delta_preview and delta_preview.get("change") and delta_preview["change"].get("fragility") == "down":
        signal_line += " — fix lowers fragility"

    return {
        "signal": signal,
        "label": label,
        "grade": _signal_to_grade(signal),
        "fragilityScore": fragility,
        "signalLine": signal_line,
    }


def _build_primary_failure(evaluation, blocks, entities=None) -> dict:
    """
    Identify the single biggest cause of fragility.

    Returns exactly one primaryFailure object with:
    - type, severity, description, affectedLegIds, fastestFix

    Extended failure types (Ticket 14):
    - prop_density: too many props / high variance markets
    - same_game_dependency: multiple legs from same game
    - market_conflict: correlated market types (e.g. total + multiple overs)
    - weak_clarity: input too vague / ambiguous
    - correlation, leg_count, volatility, dependency (original)
    """
    metrics = evaluation.metrics
    correlations = evaluation.correlations
    leg_count = len(blocks) if blocks else 0
    entities = entities or {}

    # --- Compute extended failure scores ---

    # Original scores
    scores = {
        "correlation": metrics.correlation_penalty * (metrics.correlation_multiplier or 1.0),
        "leg_count": metrics.leg_penalty,
        "volatility": sum(1 for b in (blocks or []) if b.base_fragility >= 0.20) * 5.0,
        "dependency": len(correlations) * 3.0,
    }

    # Ticket 14: prop_density — penalise when >50% of legs are props
    # Score is aggressive because props inflate leg_penalty via base_fragility;
    # prop_density must outrank leg_count when the *reason* is the props.
    prop_blocks = [b for b in (blocks or []) if b.bet_type == BetType.PLAYER_PROP]
    prop_count = len(prop_blocks)
    if leg_count > 0 and prop_count >= 2:
        prop_ratio = prop_count / leg_count
        scores["prop_density"] = (
            prop_count * 8.0
            + (15.0 if prop_ratio > 0.5 else 0.0)
            + (10.0 if prop_ratio >= 1.0 else 0.0)
        )
    else:
        scores["prop_density"] = 0.0

    # Ticket 14: same_game_dependency — multiple legs sharing a game_id
    game_id_counts: dict[str, list] = {}
    for b in (blocks or []):
        gid = b.game_id
        game_id_counts.setdefault(gid, []).append(b)
    same_game_groups = {gid: blks for gid, blks in game_id_counts.items() if len(blks) > 1}
    max_same_game = max((len(blks) for blks in same_game_groups.values()), default=0)
    total_same_game_legs = sum(len(blks) for blks in same_game_groups.values())
    # Score is aggressive: same-game legs compound risk beyond raw leg count
    scores["same_game_dependency"] = (
        max_same_game * 15.0 + total_same_game_legs * 5.0
    ) if max_same_game >= 2 else 0.0

    # Ticket 14: market_conflict — multiple totals or correlated market types
    market_types = [b.bet_type for b in (blocks or [])]
    total_count = market_types.count(BetType.TOTAL)
    spread_count = market_types.count(BetType.SPREAD)
    # Totals + spreads on same game = conflict; multiple totals = conflict
    conflict_score = 0.0
    if total_count >= 2:
        conflict_score += total_count * 4.0
    if total_count >= 1 and spread_count >= 1:
        # Check if same game
        total_games = {b.game_id for b in (blocks or []) if b.bet_type == BetType.TOTAL}
        spread_games = {b.game_id for b in (blocks or []) if b.bet_type == BetType.SPREAD}
        if total_games & spread_games:
            conflict_score += 8.0
    scores["market_conflict"] = conflict_score

    # Ticket 14: weak_clarity — input too short, no entities recognized
    # Score must be high enough to outrank leg_count when the engine has
    # almost nothing to work with (no teams, no players, unknown sport).
    teams_count = len(entities.get("teams_mentioned", []))
    players_count = len(entities.get("players_mentioned", []))
    markets_count = len(entities.get("markets_detected", []))
    clarity_score = 0.0
    if teams_count == 0 and players_count == 0:
        clarity_score += 12.0
    if markets_count == 0:
        clarity_score += 5.0
    if entities.get("sport_guess") == "unknown":
        clarity_score += 6.0
    if len(entities.get("_raw_text", "")) < 15:
        clarity_score += 3.0
    # When *nothing* is recognized, this is clearly the dominant failure
    if teams_count == 0 and players_count == 0 and entities.get("sport_guess") == "unknown":
        clarity_score += 10.0
    scores["weak_clarity"] = clarity_score

    # Primary = highest scoring factor
    primary_type = max(scores, key=lambda k: scores[k])

    # If all scores are 0, default to leg_count for single legs
    if all(v == 0 for v in scores.values()):
        primary_type = "leg_count"

    # Severity from the primary factor's magnitude
    primary_score = scores[primary_type]
    if primary_score >= 15:
        severity = "high"
    elif primary_score >= 5:
        severity = "medium"
    else:
        severity = "low"

    # Build specific description (no banned phrases)
    affected_leg_ids: list[str] = []
    candidate_leg_ids: list[str] = []

    if primary_type == "correlation":
        if correlations:
            top_corr = max(correlations, key=lambda c: c.penalty)
            affected_leg_ids = [str(top_corr.block_a), str(top_corr.block_b)]
            candidate_leg_ids = [str(top_corr.block_b)]
            corr_type = top_corr.type
            description = f"{corr_type.replace('_', ' ').title()} correlation between 2 legs adds +{top_corr.penalty:.1f}pt penalty"
        else:
            description = f"Correlation penalty of +{metrics.correlation_penalty:.1f}pt detected across selections"

    elif primary_type == "leg_count":
        description = f"{leg_count} leg{'s' if leg_count != 1 else ''} produce{'s' if leg_count == 1 else ''} +{metrics.leg_penalty:.1f}pt structural penalty"
        if blocks and leg_count > 2:
            candidate_leg_ids = [str(blocks[-1].block_id)]

    elif primary_type == "volatility":
        vol_blocks = [b for b in (blocks or []) if b.base_fragility >= 0.20]
        vol_count = len(vol_blocks)
        description = f"{vol_count} high-variance selection{'s' if vol_count != 1 else ''} with base fragility >= 20pt"
        affected_leg_ids = [str(b.block_id) for b in vol_blocks[:3]]
        candidate_leg_ids = [str(vol_blocks[0].block_id)] if vol_blocks else []

    elif primary_type == "dependency":
        dep_count = len(correlations)
        description = f"{dep_count} dependent outcome pair{'s' if dep_count != 1 else ''} share variables"
        if correlations:
            block_freq: dict[str, int] = {}
            for c in correlations:
                block_freq[str(c.block_a)] = block_freq.get(str(c.block_a), 0) + 1
                block_freq[str(c.block_b)] = block_freq.get(str(c.block_b), 0) + 1
            top_block = max(block_freq, key=lambda k: block_freq[k])
            affected_leg_ids = [top_block]
            candidate_leg_ids = [top_block]

    elif primary_type == "prop_density":
        description = f"{prop_count} of {leg_count} legs are player props ({prop_count}/{leg_count} = {prop_count*100//leg_count}% prop density)"
        affected_leg_ids = [str(b.block_id) for b in prop_blocks[:3]]
        candidate_leg_ids = [str(prop_blocks[0].block_id)] if prop_blocks else []

    elif primary_type == "same_game_dependency":
        # Find the game with most legs
        worst_gid = max(same_game_groups, key=lambda g: len(same_game_groups[g]))
        sg_blocks = same_game_groups[worst_gid]
        description = f"{len(sg_blocks)} legs reference the same game ({worst_gid.replace('game_', '')}), creating outcome dependency"
        affected_leg_ids = [str(b.block_id) for b in sg_blocks[:3]]
        candidate_leg_ids = [str(sg_blocks[-1].block_id)] if sg_blocks else []

    elif primary_type == "market_conflict":
        conflict_parts = []
        if total_count >= 2:
            conflict_parts.append(f"{total_count} total/over-under legs")
        if total_count >= 1 and spread_count >= 1:
            conflict_parts.append("total + spread on overlapping games")
        description = f"Market conflict: {', '.join(conflict_parts)} creates correlated outcomes"
        total_blocks = [b for b in (blocks or []) if b.bet_type == BetType.TOTAL]
        affected_leg_ids = [str(b.block_id) for b in total_blocks[:3]]
        candidate_leg_ids = [str(total_blocks[-1].block_id)] if total_blocks else []

    else:  # weak_clarity
        missing = []
        if teams_count == 0 and players_count == 0:
            missing.append("no teams or players recognized")
        if markets_count == 0:
            missing.append("no market types detected")
        if entities.get("sport_guess") == "unknown":
            missing.append("sport not identified")
        description = f"Input clarity is limited: {'; '.join(missing)}"

    # Determine fastestFix action
    action_map = {
        "correlation": "split_parlay" if len(correlations) > 1 else "remove_leg",
        "leg_count": "remove_leg",
        "volatility": "reduce_props" if prop_count > 1 else "swap_leg",
        "dependency": "split_parlay",
        "prop_density": "reduce_props",
        "same_game_dependency": "reduce_same_game",
        "market_conflict": "swap_leg",
        "weak_clarity": "clarify_input",
    }
    action = action_map.get(primary_type, "remove_leg")

    # Build fix description
    fix_descriptions = {
        "remove_leg": f"Remove the most penalized leg to reduce fragility by ~{primary_score * 0.5:.0f}pt",
        "split_parlay": "Split into 2 uncorrelated tickets to eliminate dependency penalty",
        "swap_leg": "Replace the conflicting market with an uncorrelated bet type",
        "reduce_props": f"Replace {min(prop_count, 2)} prop bet{'s' if prop_count > 1 else ''} with game-level bets (spread/total)",
        "reduce_same_game": f"Move {max_same_game - 1} same-game leg{'s' if max_same_game > 2 else ''} to a separate ticket",
        "clarify_input": "Add team names, player names, or market types for a more accurate evaluation",
    }

    return {
        "type": primary_type,
        "severity": severity,
        "description": description,
        "affectedLegIds": affected_leg_ids,
        "fastestFix": {
            "action": action,
            "description": fix_descriptions.get(action, "Simplify parlay structure"),
            "candidateLegIds": candidate_leg_ids,
        },
    }


def _build_delta_preview(evaluation, blocks, primary_failure) -> dict:
    """
    Compute a deterministic 'what if you apply fastestFix' preview.

    Uses existing evaluate_parlay() — no new math.
    If candidate leg exists and action is remove_leg, re-evaluates without it.
    Otherwise returns null after/change.
    """
    fastest_fix = primary_failure.get("fastestFix", {})
    candidate_ids = fastest_fix.get("candidateLegIds", [])
    action = fastest_fix.get("action", "")

    # Before state (current)
    before_fragility = evaluation.metrics.final_fragility
    before_signal = _fragility_to_signal(before_fragility, evaluation)
    before_state = {
        "signal": before_signal,
        "grade": _signal_to_grade(before_signal),
        "fragilityScore": before_fragility,
    }

    # Can only simulate remove_leg with a known candidate and >1 blocks
    if action == "remove_leg" and candidate_ids and blocks and len(blocks) > 1:
        remove_id = candidate_ids[0]
        remaining_blocks = [b for b in blocks if str(b.block_id) != remove_id]

        if remaining_blocks:
            after_eval = evaluate_parlay(
                blocks=remaining_blocks,
                dna_profile=None,
                bankroll=None,
                candidates=None,
                max_suggestions=0,
            )
            after_fragility = after_eval.metrics.final_fragility
            after_signal = _fragility_to_signal(after_fragility, after_eval)
            after_state = {
                "signal": after_signal,
                "grade": _signal_to_grade(after_signal),
                "fragilityScore": after_fragility,
            }

            # Determine direction of change
            signal_order = {"blue": 0, "green": 1, "yellow": 2, "red": 3}
            before_idx = signal_order[before_signal]
            after_idx = signal_order[after_signal]
            if after_idx < before_idx:
                signal_change = "up"
            elif after_idx > before_idx:
                signal_change = "down"
            else:
                signal_change = "same"

            if after_fragility < before_fragility:
                fragility_change = "down"
            elif after_fragility > before_fragility:
                fragility_change = "up"
            else:
                fragility_change = "same"

            return {
                "before": before_state,
                "after": after_state,
                "change": {"signal": signal_change, "fragility": fragility_change},
            }

    # No simulation possible
    return {
        "before": before_state,
        "after": None,
        "change": None,
    }


def _build_secondary_factors(evaluation, blocks, entities, primary_type: str) -> list[dict]:
    """
    Build ranked secondary factors (runners-up from the same scoring logic).

    Sprint 2: Expose factors that contributed but weren't primary.
    Each factor has: type, impact (low/med/high), explanation.
    """
    metrics = evaluation.metrics
    correlations = evaluation.correlations
    leg_count = len(blocks) if blocks else 0
    entities = entities or {}

    # Recompute all scores (same logic as _build_primary_failure)
    scores = {
        "correlation": metrics.correlation_penalty * (metrics.correlation_multiplier or 1.0),
        "leg_count": metrics.leg_penalty,
        "volatility": sum(1 for b in (blocks or []) if b.base_fragility >= 0.20) * 5.0,
        "dependency": len(correlations) * 3.0,
    }

    # Prop density
    prop_blocks = [b for b in (blocks or []) if b.bet_type == BetType.PLAYER_PROP]
    prop_count = len(prop_blocks)
    if leg_count > 0 and prop_count >= 2:
        prop_ratio = prop_count / leg_count
        scores["prop_density"] = prop_count * 8.0 + (15.0 if prop_ratio > 0.5 else 0.0) + (10.0 if prop_ratio >= 1.0 else 0.0)
    else:
        scores["prop_density"] = 0.0

    # Same-game dependency
    game_id_counts: dict[str, list] = {}
    for b in (blocks or []):
        game_id_counts.setdefault(b.game_id, []).append(b)
    same_game_groups = {gid: blks for gid, blks in game_id_counts.items() if len(blks) > 1}
    max_same_game = max((len(blks) for blks in same_game_groups.values()), default=0)
    total_same_game_legs = sum(len(blks) for blks in same_game_groups.values())
    scores["same_game_dependency"] = (max_same_game * 15.0 + total_same_game_legs * 5.0) if max_same_game >= 2 else 0.0

    # Market conflict
    market_types = [b.bet_type for b in (blocks or [])]
    total_count = market_types.count(BetType.TOTAL)
    spread_count = market_types.count(BetType.SPREAD)
    conflict_score = 0.0
    if total_count >= 2:
        conflict_score += total_count * 4.0
    if total_count >= 1 and spread_count >= 1:
        total_games = {b.game_id for b in (blocks or []) if b.bet_type == BetType.TOTAL}
        spread_games = {b.game_id for b in (blocks or []) if b.bet_type == BetType.SPREAD}
        if total_games & spread_games:
            conflict_score += 8.0
    scores["market_conflict"] = conflict_score

    # Weak clarity
    teams_count = len(entities.get("teams_mentioned", []))
    players_count = len(entities.get("players_mentioned", []))
    markets_count = len(entities.get("markets_detected", []))
    clarity_score = 0.0
    if teams_count == 0 and players_count == 0:
        clarity_score += 12.0
    if markets_count == 0:
        clarity_score += 5.0
    if entities.get("sport_guess") == "unknown":
        clarity_score += 6.0
    if teams_count == 0 and players_count == 0 and entities.get("sport_guess") == "unknown":
        clarity_score += 10.0
    scores["weak_clarity"] = clarity_score

    # Get runners-up (exclude primary, score > 0)
    sorted_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    runners_up = [(t, s) for t, s in sorted_factors if t != primary_type and s > 0][:3]

    # Build factor objects
    explanations = {
        "correlation": f"+{metrics.correlation_penalty:.1f}pt from correlated outcomes",
        "leg_count": f"+{metrics.leg_penalty:.1f}pt from {leg_count} legs",
        "volatility": f"{sum(1 for b in (blocks or []) if b.base_fragility >= 0.20)} high-variance selections",
        "dependency": f"{len(correlations)} outcome pair(s) share variables",
        "prop_density": f"{prop_count}/{leg_count} legs are props",
        "same_game_dependency": f"{max_same_game} legs from same game",
        "market_conflict": "overlapping market types amplify correlation",
        "weak_clarity": "limited entity recognition",
    }

    result = []
    for factor_type, score in runners_up:
        if score >= 15:
            impact = "high"
        elif score >= 5:
            impact = "medium"
        else:
            impact = "low"

        result.append({
            "type": factor_type,
            "impact": impact,
            "explanation": explanations.get(factor_type, "contributes to fragility"),
        })

    return result


def _build_human_summary(evaluation, blocks, entities, primary_failure) -> str:
    """
    Generate a 2-3 sentence human-readable summary.

    Sprint 2: Always included, references recognized entities.
    No generic warnings. Opinionated and specific.
    """
    metrics = evaluation.metrics
    fragility = metrics.final_fragility
    leg_count = len(blocks) if blocks else 0
    entities = entities or {}

    # Extract recognized entities for reference
    sport = entities.get("sport_guess", "unknown")
    teams = entities.get("teams_mentioned", [])
    players = entities.get("players_mentioned", [])
    markets = entities.get("markets_detected", [])

    pf_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    pf_severity = primary_failure.get("severity", "low") if primary_failure else "low"

    # Build first sentence: what we see
    if teams and players:
        subject = f"{teams[0]} with {players[0]}"
    elif teams:
        subject = teams[0]
    elif players:
        subject = players[0]
    elif sport != "unknown":
        subject = f"This {sport.upper()} parlay"
    else:
        subject = f"This {leg_count}-leg parlay"

    # Build assessment based on fragility bucket
    if fragility <= 15:
        assessment = "looks structurally sound"
        outlook = "Most paths lead to success here."
    elif fragility <= 35:
        assessment = "has moderate complexity"
        outlook = "A few things need to align, but it's workable."
    elif fragility <= 60:
        assessment = "carries elevated risk"
        outlook = "One miss could break the ticket."
    else:
        assessment = "is highly fragile"
        outlook = "Multiple failure points compound against you."

    # Build specific insight from primary failure
    pf_insights = {
        "correlation": "Correlated legs inflate the penalty—consider splitting.",
        "leg_count": f"{leg_count} legs add structural penalty; fewer is safer.",
        "volatility": "High-variance props drive fragility.",
        "dependency": "Shared outcomes create hidden dependencies.",
        "prop_density": "Prop-heavy slips have elevated variance.",
        "same_game_dependency": "Same-game legs aren't independent—risk compounds.",
        "market_conflict": "Overlapping markets amplify correlation.",
        "weak_clarity": "Better input yields better analysis.",
    }
    insight = pf_insights.get(pf_type, "")

    # Compose summary (2-3 sentences)
    summary = f"{subject} {assessment}. {outlook}"
    if insight and pf_severity in ("medium", "high"):
        summary += f" {insight}"

    return summary


# Main Pipeline Function
# =============================================================================


def _extract_entities_from_text(text: str) -> tuple[list[str], list[str]]:
    """
    Extract player names and team names from bet text.

    Sprint 3 scope: Simple extraction for NBA.
    Returns (player_names, team_names).
    """
    text_lower = text.lower()

    # NBA team abbreviations/names to look for
    nba_teams = {
        "lakers": "LAL", "lal": "LAL", "los angeles lakers": "LAL",
        "celtics": "BOS", "bos": "BOS", "boston": "BOS",
        "nuggets": "DEN", "den": "DEN", "denver": "DEN",
        "bucks": "MIL", "mil": "MIL", "milwaukee": "MIL",
        "warriors": "GSW", "gsw": "GSW", "golden state": "GSW",
        "suns": "PHX", "phx": "PHX", "phoenix": "PHX",
        "76ers": "PHI", "phi": "PHI", "sixers": "PHI", "philadelphia": "PHI",
        "mavericks": "DAL", "dal": "DAL", "dallas": "DAL", "mavs": "DAL",
        "heat": "MIA", "mia": "MIA", "miami": "MIA",
        "nets": "BKN", "bkn": "BKN", "brooklyn": "BKN",
        "knicks": "NYK", "nyk": "NYK", "new york": "NYK",
        "bulls": "CHI", "chi": "CHI", "chicago": "CHI",
        "clippers": "LAC", "lac": "LAC",
        "thunder": "OKC", "okc": "OKC", "oklahoma": "OKC",
        "timberwolves": "MIN", "min": "MIN", "minnesota": "MIN", "wolves": "MIN",
        "kings": "SAC", "sac": "SAC", "sacramento": "SAC",
        "pelicans": "NOP", "nop": "NOP", "new orleans": "NOP",
        "grizzlies": "MEM", "mem": "MEM", "memphis": "MEM",
        "cavaliers": "CLE", "cle": "CLE", "cleveland": "CLE", "cavs": "CLE",
        "hawks": "ATL", "atl": "ATL", "atlanta": "ATL",
        "raptors": "TOR", "tor": "TOR", "toronto": "TOR",
        "pacers": "IND", "ind": "IND", "indiana": "IND",
        "hornets": "CHA", "cha": "CHA", "charlotte": "CHA",
        "wizards": "WAS", "was": "WAS", "washington": "WAS",
        "magic": "ORL", "orl": "ORL", "orlando": "ORL",
        "pistons": "DET", "det": "DET", "detroit": "DET",
        "jazz": "UTA", "uta": "UTA", "utah": "UTA",
        "rockets": "HOU", "hou": "HOU", "houston": "HOU",
        "spurs": "SAS", "sas": "SAS", "san antonio": "SAS",
        "trail blazers": "POR", "por": "POR", "portland": "POR", "blazers": "POR",
    }

    # Common NBA player names to look for (from sample data)
    known_players = [
        "lebron james", "lebron", "anthony davis", "ad",
        "jaylen brown", "jayson tatum", "tatum",
        "nikola jokic", "jokic", "jamal murray",
        "giannis", "giannis antetokounmpo", "damian lillard", "lillard", "dame",
        "stephen curry", "curry", "steph", "klay thompson",
        "kevin durant", "durant", "kd", "devin booker", "booker",
        "joel embiid", "embiid", "tyrese maxey", "maxey",
        "luka doncic", "luka", "doncic", "kyrie irving", "kyrie",
    ]

    found_teams = []
    for team_key, team_abbr in nba_teams.items():
        if team_key in text_lower:
            if team_abbr not in found_teams:
                found_teams.append(team_abbr)

    found_players = []
    for player in known_players:
        if player in text_lower:
            # Map to full name for context lookup
            player_map = {
                "lebron": "LeBron James", "ad": "Anthony Davis",
                "tatum": "Jayson Tatum", "jokic": "Nikola Jokic",
                "giannis": "Giannis Antetokounmpo", "lillard": "Damian Lillard",
                "dame": "Damian Lillard", "curry": "Stephen Curry",
                "steph": "Stephen Curry", "durant": "Kevin Durant",
                "kd": "Kevin Durant", "booker": "Devin Booker",
                "embiid": "Joel Embiid", "maxey": "Tyrese Maxey",
                "luka": "Luka Doncic", "doncic": "Luka Doncic",
                "kyrie": "Kyrie Irving",
            }
            full_name = player_map.get(player, player.title())
            if full_name not in found_players:
                found_players.append(full_name)

    return found_players, found_teams


def _fetch_context_for_bet(text: str, correlation_id: Optional[str] = None) -> Optional[dict]:
    """
    Fetch context data relevant to the bet.

    Sprint 3 scope: NBA availability only.
    Sprint 4: Also triggers alert generation for availability changes.

    Returns context dict or None if not applicable.
    """
    try:
        # Extract entities from bet text
        player_names, team_names = _extract_entities_from_text(text)

        # Check if this looks like an NBA bet
        text_lower = text.lower()
        is_nba = (
            "nba" in text_lower
            or len(player_names) > 0
            or len(team_names) > 0
            or any(word in text_lower for word in ["basketball", "points", "rebounds", "assists"])
        )

        if not is_nba:
            return None

        # Fetch NBA context
        snapshot = get_context("NBA")

        # Sprint 4: Check for alerts (stores any new alerts)
        new_alerts = check_for_alerts(
            snapshot=snapshot,
            player_names=player_names if player_names else None,
            team_names=team_names if team_names else None,
            correlation_id=correlation_id,
        )
        if new_alerts:
            _logger.info(f"Generated {len(new_alerts)} alert(s) for bet evaluation")

        # Apply context to get impact
        impact = apply_context(
            snapshot=snapshot,
            player_names=player_names if player_names else None,
            team_names=team_names if team_names else None,
        )

        # Convert to dict for response
        return {
            "sport": snapshot.sport,
            "source": snapshot.source,
            "as_of": snapshot.as_of.isoformat(),
            "impact": {
                "adjustment": impact.total_adjustment,
                "summary": impact.summary,
                "modifiers": [
                    {
                        "adjustment": m.adjustment,
                        "reason": m.reason,
                        "affected_players": list(m.affected_players),
                    }
                    for m in impact.modifiers
                ],
            },
            "missing_data": list(impact.missing_data),
            "player_count": snapshot.player_count,
            "entities_found": {
                "players": player_names,
                "teams": team_names,
            },
            "alerts_generated": len(new_alerts),
        }

    except Exception as e:
        _logger.warning(f"Failed to fetch context: {e}")
        return None


def run_evaluation(normalized: NormalizedInput) -> PipelineResponse:
    """
    Run the canonical evaluation pipeline.

    This is the ONLY entry point for evaluation. All routes call this.

    Args:
        normalized: Validated input from Airlock

    Returns:
        PipelineResponse with evaluation, interpretation, context, and explain

    Flow:
        1. Parse text → BetBlocks
        2. Call evaluate_parlay() (the canonical core function)
        3. Fetch external context (Sprint 3)
        4. Generate plain-English interpretation
        5. Apply tier filtering to explain
        6. Return unified response
    """
    # Step 1: Entity recognition (Ticket 14 — cheap, deterministic)
    entities = recognize_entities(normalized.input_text)
    entities["_raw_text"] = normalized.input_text  # kept for weak_clarity scoring

    # Step 2: Parse text into BetBlocks (now uses per-leg market detection)
    blocks = _parse_bet_text(normalized.input_text)
    leg_count = len(blocks)

    # Step 3: Call canonical evaluation engine
    evaluation = evaluate_parlay(
        blocks=blocks,
        dna_profile=None,
        bankroll=None,
        candidates=None,
        max_suggestions=0,
    )

    # Step 4: Fetch external context (Sprint 3 - additive only)
    # Sprint 4: Pass parlay_id as correlation_id for alert tracking
    context_data = _fetch_context_for_bet(
        normalized.input_text,
        correlation_id=str(evaluation.parlay_id),
    )

    # Step 5: Generate plain-English interpretation
    interpretation = {
        "fragility": _interpret_fragility(evaluation.metrics.final_fragility),
    }

    # Step 6: Build full explain wrapper
    explain_full = {
        "summary": _generate_summary(evaluation, leg_count),
        "alerts": _generate_alerts(evaluation),
        "recommended_next_step": evaluation.recommendation.reason,
    }

    # Step 7: Build primary failure + delta preview (Ticket 4 + Ticket 14)
    primary_failure = _build_primary_failure(evaluation, blocks, entities)
    delta_preview = _build_delta_preview(evaluation, blocks, primary_failure)

    # Step 8: Build signal info (Ticket 5)
    signal_info = _build_signal_info(evaluation, primary_failure, delta_preview)

    # Step 9: Apply tier filtering (uses primary_failure for specific warnings/tips)
    explain_filtered = _apply_tier_filtering(normalized.tier, explain_full, evaluation, blocks, primary_failure)

    # Step 10: Sprint 2 — Compute same-game indicator + volatility flag
    same_game_info = _detect_same_game_indicator(blocks)
    volatility_flag = _compute_volatility_flag(
        entities.get("markets_detected", []),
        leg_count,
        same_game_info["same_game_count"]
    )

    # Step 11: Sprint 2 — Build secondary factors (runners-up from scoring logic)
    primary_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    secondary_factors = _build_secondary_factors(evaluation, blocks, entities, primary_type)

    # Step 12: Sprint 2 — Build human summary (always included)
    human_summary = _build_human_summary(evaluation, blocks, entities, primary_failure)

    # Step 13: Ticket 17 — Run Sherlock hook (if enabled)
    sherlock_result = None
    if _config.sherlock_enabled:
        hook_result = run_sherlock_hook(
            sherlock_enabled=_config.sherlock_enabled,
            dna_recording_enabled=_config.dna_recording_enabled,
            evaluation_metrics={
                "final_fragility": evaluation.metrics.final_fragility,
                "correlation_penalty": evaluation.metrics.correlation_penalty,
                "leg_penalty": evaluation.metrics.leg_penalty,
            },
            signal=signal_info.get("signal", "yellow") if signal_info else "yellow",
            primary_failure_type=primary_type,
            leg_count=leg_count,
        )
        if hook_result:
            sherlock_result = hook_result.to_dict()

    # Build public entity output (strip internal _raw_text, add Sprint 2 fields)
    entities_public = {k: v for k, v in entities.items() if not k.startswith("_")}
    entities_public["volatility_flag"] = volatility_flag
    entities_public["same_game_indicator"] = same_game_info

    return PipelineResponse(
        evaluation=evaluation,
        interpretation=interpretation,
        explain=explain_filtered,
        context=context_data,
        primary_failure=primary_failure,
        delta_preview=delta_preview,
        signal_info=signal_info,
        entities=entities_public,
        secondary_factors=secondary_factors,
        human_summary=human_summary,
        sherlock_result=sherlock_result,
        leg_count=leg_count,
        tier=normalized.tier.value,
    )
