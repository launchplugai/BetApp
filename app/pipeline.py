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

# Explainability adapter (Ticket 18)
from app.explainability_adapter import transform_sherlock_to_explainability

# Proof summary (Ticket 18B)
from app.proof_summary import derive_proof_summary

# DNA Contract Validator (Ticket 19)
from app.dna.contract_validator import validate_dna_artifacts, get_contract_version

# DNA Artifact Emitter (Ticket 20)
from app.dna.artifact_emitter import emit_artifacts_from_evaluation, get_artifact_counts

# UI Artifact Contract (Ticket 21)
from app.dna.ui_contract_v1 import validate_for_ui, get_ui_contract_version

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

    # Ticket 25: Evaluated Parlay Receipt (what was evaluated)
    evaluated_parlay: Optional[dict] = None

    # Ticket 25: Notable Legs (leg-aware context)
    notable_legs: Optional[list] = None

    # Ticket 25: Final Verdict (conclusive 2-4 sentence summary)
    final_verdict: Optional[dict] = None

    # Ticket 26: Gentle Guidance (optional adjustment hints)
    gentle_guidance: Optional[dict] = None

    # Ticket 27: Grounding Warnings (soft warnings for unrecognized entities)
    grounding_warnings: Optional[list] = None

    # Ticket 17: Sherlock integration result (None if disabled)
    sherlock_result: Optional[dict] = None

    # Ticket 18: Explainability blocks (None if Sherlock disabled)
    debug_explainability: Optional[dict] = None

    # Ticket 18B: Proof summary (always present, shows flag status)
    proof_summary: Optional[dict] = None

    # Metadata
    leg_count: int = 0
    tier: str = "good"


# =============================================================================
# Evaluation Context (Ticket 28 — Single Source of Truth)
# =============================================================================


@dataclass(frozen=True)
class EvaluationContext:
    """
    Ticket 28: Single authoritative context for all evaluation outputs.

    INVARIANT: No function may compute leg_count independently.
    All output builders MUST use this context.

    Fields:
    - leg_count: Authoritative leg count (from canonical legs if present, else parsed)
    - bet_term: "bet" for single leg, "parlay" for multiple
    - is_canonical: True if leg_count came from canonical legs (builder mode)
    - analysis_depth: "structural_only" (no live data) or "contextual" (with live data)
    """
    leg_count: int
    bet_term: str  # "bet" or "parlay"
    is_canonical: bool
    analysis_depth: str = "structural_only"

    @classmethod
    def create(cls, blocks: list, canonical_legs: Optional[list] = None) -> "EvaluationContext":
        """
        Create evaluation context from available data.

        Priority:
        1. canonical_legs (from builder) if present
        2. parsed blocks (from text input) as fallback
        """
        if canonical_legs:
            leg_count = len(canonical_legs)
            is_canonical = True
        else:
            leg_count = len(blocks) if blocks else 0
            is_canonical = False

        # Ticket 28: Language consistency - enforced at context creation
        bet_term = "bet" if leg_count == 1 else "parlay"

        return cls(
            leg_count=leg_count,
            bet_term=bet_term,
            is_canonical=is_canonical,
            analysis_depth="structural_only",  # Ticket 29: No live data yet
        )


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


def _generate_summary(response: EvaluationResponse, eval_ctx: Optional[EvaluationContext] = None, leg_count: int = 0) -> list[str]:
    """
    Generate plain-English summary bullets from evaluation response.

    Ticket 28: Uses EvaluationContext for authoritative leg_count.
    """
    # Ticket 28: Use eval_ctx for authoritative leg_count
    lc = eval_ctx.leg_count if eval_ctx else leg_count
    bet_term = eval_ctx.bet_term if eval_ctx else ("bet" if lc == 1 else "parlay")
    summary = [
        f"Detected {lc} leg(s) in this {bet_term}",
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


def _build_primary_failure(evaluation, blocks, entities=None, eval_ctx: Optional[EvaluationContext] = None) -> dict:
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

    Ticket 28: Uses EvaluationContext for authoritative leg_count.
    """
    metrics = evaluation.metrics
    correlations = evaluation.correlations
    # Ticket 28: Use eval_ctx for authoritative leg_count
    leg_count = eval_ctx.leg_count if eval_ctx else (len(blocks) if blocks else 0)
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


def _build_secondary_factors(evaluation, blocks, entities, primary_type: str, eval_ctx: Optional[EvaluationContext] = None) -> list[dict]:
    """
    Build ranked secondary factors (runners-up from the same scoring logic).

    Sprint 2: Expose factors that contributed but weren't primary.
    Each factor has: type, impact (low/med/high), explanation.

    Ticket 28: Uses EvaluationContext for authoritative leg_count.
    """
    metrics = evaluation.metrics
    correlations = evaluation.correlations
    # Ticket 28: Use eval_ctx for authoritative leg_count
    leg_count = eval_ctx.leg_count if eval_ctx else (len(blocks) if blocks else 0)
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


def _build_human_summary(evaluation, blocks, entities, primary_failure, eval_ctx: Optional[EvaluationContext] = None) -> str:
    """
    Generate a 2-3 sentence human-readable summary.

    Sprint 2: Always included, references recognized entities.
    Ticket 28: Uses EvaluationContext for authoritative leg_count and bet_term.
    No generic warnings. Opinionated and specific.
    """
    metrics = evaluation.metrics
    fragility = metrics.final_fragility
    # Ticket 28: Use eval_ctx for authoritative leg_count
    leg_count = eval_ctx.leg_count if eval_ctx else (len(blocks) if blocks else 0)
    bet_term = eval_ctx.bet_term if eval_ctx else ("bet" if leg_count == 1 else "parlay")
    entities = entities or {}

    # Extract recognized entities for reference
    sport = entities.get("sport_guess", "unknown")
    teams = entities.get("teams_mentioned", [])
    players = entities.get("players_mentioned", [])
    markets = entities.get("markets_detected", [])

    pf_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    pf_severity = primary_failure.get("severity", "low") if primary_failure else "low"

    # Ticket 28: Language consistency - use bet_term from eval_ctx
    # Format as "bet" or "X-leg parlay"
    if leg_count == 1:
        bet_term_display = "bet"
    else:
        bet_term_display = f"{leg_count}-leg parlay"

    # Build first sentence: what we see
    if teams and players:
        subject = f"{teams[0]} with {players[0]}"
    elif teams:
        subject = teams[0]
    elif players:
        subject = players[0]
    elif sport != "unknown":
        subject = f"This {sport.upper()} {bet_term}"
    else:
        subject = f"This {bet_term_display}"

    # Ticket 29: Detect leg composition for varied summaries
    ml_count = markets.count("ml") + markets.count("moneyline")
    spread_count = markets.count("spread")
    total_count = markets.count("total") + markets.count("over") + markets.count("under")
    prop_count = markets.count("prop") + markets.count("player_prop")

    # Ticket 29: Vary assessment based on composition + fragility
    if fragility <= 15:
        assessment = "looks structurally sound"
        # Vary outlook based on what's in the slip
        if ml_count > 0 and spread_count == 0 and prop_count == 0:
            outlook = "Moneyline-only structure keeps variance low."
        elif prop_count == 0:
            outlook = "Most paths lead to success here."
        else:
            outlook = "Structure is solid despite prop inclusion."
    elif fragility <= 35:
        assessment = "has moderate complexity"
        if prop_count > ml_count:
            outlook = "Props add variance but the structure is manageable."
        elif spread_count > 0 and total_count > 0:
            outlook = "Spreads and totals on the same slip can interact."
        else:
            outlook = "A few things need to align, but it's workable."
    elif fragility <= 60:
        assessment = "carries elevated risk"
        if prop_count >= 2:
            outlook = "Heavy prop concentration drives the fragility score."
        elif spread_count >= 3:
            outlook = "Multiple spreads multiply margin-of-error sensitivity."
        else:
            outlook = "One miss could break the ticket."
    else:
        assessment = "is highly fragile"
        if prop_count >= 3:
            outlook = "Prop-heavy structure is inherently volatile."
        else:
            outlook = "Multiple failure points compound against you."

    # Build specific insight from primary failure — Ticket 29: explain WHY
    pf_insights = {
        "correlation": "Correlated legs inflate the penalty—when one fails, linked legs often follow.",
        "leg_count": f"{leg_count} legs add structural penalty; each additional leg multiplies failure risk.",
        "volatility": "High-variance props drive fragility—player stats fluctuate more than team outcomes.",
        "dependency": "Shared outcomes create hidden dependencies—teams appearing twice tie results together.",
        "prop_density": "Prop-heavy slips have elevated variance—player performance depends on minutes and game flow.",
        "same_game_dependency": "Same-game legs aren't independent—if the game script changes, multiple legs flip.",
        "market_conflict": "Overlapping markets amplify correlation—totals and spreads in the same game aren't separate.",
        "weak_clarity": "Better input yields better analysis—more specific selections improve confidence.",
    }
    insight = pf_insights.get(pf_type, "")

    # Compose summary (2-3 sentences)
    summary = f"{subject} {assessment}. {outlook}"
    if insight and pf_severity in ("medium", "high"):
        summary += f" {insight}"

    return summary


# =============================================================================
# Ticket 25: Evaluated Parlay Receipt + Notable Legs + Final Verdict
# =============================================================================


def _get_leg_interpretation(bet_type: str) -> str:
    """
    Return a short interpretation template for a given bet type.

    Ticket 26 Part A: Muted sentence explaining what kind of risk a leg introduces.
    """
    interpretations = {
        "spread": "Spread bet — outcome depends on final margin.",
        "moneyline": "Moneyline bet — lower variance than spreads or totals.",
        "total": "Total depends on game pace and scoring environment.",
        "player_prop": "Player props tend to add variance relative to team outcomes.",
        "unknown": "",
    }
    # Handle pick'em spreads (typically -1, +1, or similar)
    if bet_type == "spread":
        return interpretations["spread"]
    return interpretations.get(bet_type, "")


def _build_evaluated_parlay(blocks: list, input_text: str, canonical_legs: Optional[tuple] = None) -> dict:
    """
    Build the evaluated parlay receipt showing exactly what was evaluated.

    Ticket 25 Part A: User should never wonder what was evaluated.
    Ticket 26 Part A: Adds interpretation field with micro-context per leg.
    Ticket 27 Part C: Uses canonical legs as source of truth when present.

    Returns structured dict with leg_count and ordered leg list.
    """
    # Ticket 27: If canonical legs are present, use them as source of truth
    if canonical_legs and len(canonical_legs) > 0:
        legs = []
        for i, cleg in enumerate(canonical_legs):
            bet_type = cleg.market if hasattr(cleg, 'market') else "unknown"
            interpretation = _get_leg_interpretation(bet_type)

            legs.append({
                "position": i + 1,
                "text": cleg.raw if hasattr(cleg, 'raw') else f"Leg {i+1}",
                "bet_type": bet_type,
                "entity": cleg.entity if hasattr(cleg, 'entity') else None,
                "value": cleg.value if hasattr(cleg, 'value') else None,
                "base_fragility": 0.0,  # Will be enriched by engine if available
                "interpretation": interpretation,
                "source": "builder",  # Indicates canonical source
            })

        leg_count = len(legs)
        display_label = f"{leg_count}-leg parlay" if leg_count != 1 else "Single bet"

        return {
            "leg_count": leg_count,
            "legs": legs,
            "display_label": display_label,
            "raw_input": input_text[:200],
            "canonical": True,  # Indicates legs came from builder
            "analysis_depth": "structural_only",  # Ticket 29: No live data integration yet
        }

    # Fallback: Use parsed blocks (legacy/text mode)
    if not blocks:
        return {
            "leg_count": 0,
            "legs": [],
            "display_label": "No legs detected",
            "analysis_depth": "structural_only",  # Ticket 29
        }

    legs = []
    for i, block in enumerate(blocks):
        # Use the selection (parsed leg text) as the display
        leg_text = block.selection if hasattr(block, 'selection') else f"Leg {i+1}"
        bet_type = block.bet_type.value if hasattr(block, 'bet_type') else "unknown"

        # Ticket 26 Part A: Add interpretation based on bet type
        interpretation = _get_leg_interpretation(bet_type)

        legs.append({
            "position": i + 1,
            "text": leg_text,
            "bet_type": bet_type,
            "base_fragility": block.base_fragility if hasattr(block, 'base_fragility') else 0.0,
            "interpretation": interpretation,
            "source": "parsed",  # Indicates text parsing source
        })

    leg_count = len(legs)
    display_label = f"{leg_count}-leg parlay" if leg_count != 1 else "Single bet"

    return {
        "leg_count": leg_count,
        "legs": legs,
        "display_label": display_label,
        "raw_input": input_text[:200],  # Truncate for safety
        "canonical": False,  # Indicates legs came from text parsing
        "analysis_depth": "structural_only",  # Ticket 29: No live data integration yet
    }


def _build_notable_legs(blocks: list, evaluation, primary_failure: dict) -> list:
    """
    Build notable legs section with leg-aware context.

    Ticket 25 Part B: Select 1-3 legs that matter most with plain-English why.
    Ticket 26 Part B: Expanded to 2-3 sentence cadence.

    Selection criteria (deterministic):
    - Player props (high variance)
    - Totals (dependency on game pace)
    - Legs with highest base_fragility
    - Legs implicated in correlations

    Returns list of dicts: [{"leg": str, "reason": str}, ...]
    """
    if not blocks:
        return []

    notable = []
    correlations = evaluation.correlations if evaluation else ()

    # Build correlation involvement map
    corr_block_ids = set()
    for corr in correlations:
        corr_block_ids.add(str(corr.block_a))
        corr_block_ids.add(str(corr.block_b))

    # Ticket 26 Part B: Expanded explanation templates (2-3 sentences)
    # Cadence: [What it is]. [Why it matters]. [What you might see.]
    expanded_reasons = {
        "player_prop": (
            "Props depend on individual performance. "
            "A player might rest late, exit early, or simply miss shots. "
            "That makes it harder to predict outcomes cleanly."
        ),
        "total": (
            "Totals depend on combined scoring. "
            "Game pace, foul trouble, and late-game situations all affect this. "
            "A slow-paced blowout can easily miss a total."
        ),
        "correlation": (
            "These legs share the same underlying game or outcome. "
            "If one fails due to game flow, the other is more likely to fail too. "
            "Consider whether you want both riding on the same conditions."
        ),
        "fragility": (
            "This leg carries higher base volatility than others. "
            "Small swings in the game could tip this outcome either way. "
            "It contributes disproportionately to overall parlay risk."
        ),
    }

    # Score each leg for notability
    leg_scores = []
    for i, block in enumerate(blocks):
        score = 0
        reason_key = None
        bet_type = block.bet_type.value if hasattr(block, 'bet_type') else "unknown"
        leg_text = block.selection if hasattr(block, 'selection') else f"Leg {i+1}"

        # Player props add variance (highest priority)
        if bet_type == "player_prop":
            score += 3
            reason_key = "player_prop"

        # Totals depend on game pace
        if bet_type == "total":
            score += 2
            if reason_key is None:
                reason_key = "total"

        # Involved in correlations
        block_id_str = str(block.block_id) if hasattr(block, 'block_id') else ""
        if block_id_str in corr_block_ids:
            score += 2
            if reason_key is None:
                reason_key = "correlation"

        # High base fragility
        if hasattr(block, 'base_fragility') and block.base_fragility >= 0.15:
            score += 2
            if reason_key is None:
                reason_key = "fragility"

        if score > 0 and reason_key:
            leg_scores.append({
                "position": i + 1,
                "leg": leg_text,
                "reason": expanded_reasons[reason_key],
                "score": score,
            })

    # Sort by score descending, take top 3
    leg_scores.sort(key=lambda x: x["score"], reverse=True)
    notable = [
        {"leg": item["leg"], "reason": item["reason"]}
        for item in leg_scores[:3]
    ]

    return notable


def _build_final_verdict(evaluation, blocks, entities, primary_failure, signal_info, eval_ctx: Optional[EvaluationContext] = None) -> dict:
    """
    Build the final verdict block: 2-4 sentence conclusive summary.

    Ticket 25 Part C: Ties together grade, risks, artifacts, and context.
    Ticket 28: Uses EvaluationContext for authoritative leg_count and bet_term.
    Tone: calm, direct, plain English, no jargon, no hedging.

    Returns dict with verdict_text, tone, and grade reference.
    """
    if not evaluation:
        return {
            "verdict_text": "Unable to evaluate this bet. Please check your input.",
            "tone": "neutral",
            "grade": "unknown",
        }

    metrics = evaluation.metrics
    fragility = metrics.final_fragility
    # Ticket 28: Use eval_ctx for authoritative leg_count
    leg_count = eval_ctx.leg_count if eval_ctx else (len(blocks) if blocks else 0)
    bet_term = eval_ctx.bet_term if eval_ctx else ("bet" if leg_count == 1 else "parlay")
    signal = signal_info.get("signal", "yellow") if signal_info else "yellow"
    grade = signal_info.get("grade", "C") if signal_info else "C"

    pf_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    entities = entities or {}

    # Determine tone and template based on signal
    if signal in ("blue", "green"):
        tone = "positive"
        opener = f"This {bet_term} is structurally sound"
        if leg_count == 1:
            core = "with straightforward risk profile."
            driver = "Single-bet structures avoid compounding leg failures."
        else:
            core = "with limited dependency between legs."
            driver = "Risk is primarily driven by leg count rather than correlation or volatility."
        closer = "No major red flags were detected."
    elif signal == "yellow":
        tone = "mixed"
        opener = f"This {bet_term} has a workable structure"
        # Tailor core based on primary failure
        if pf_type in ("prop_density", "volatility"):
            core = "but includes elements that increase variance."
            driver = "Reducing high-variance components would improve overall stability."
            closer = "The structure is fixable without significantly reducing payout potential."
        elif pf_type in ("correlation", "dependency", "same_game_dependency"):
            core = "but has elements that share outcome dependencies."
            driver = "Consider whether correlated selections are intentional."
            closer = "Splitting dependent selections into separate tickets would reduce compounding risk."
        elif pf_type == "leg_count":
            core = f"but {leg_count} legs add meaningful structural penalty."
            driver = "Fewer legs would lower the compounding failure rate."
            closer = "Consider trimming 1-2 legs you feel least confident about."
        else:
            core = "but carries some elevated risk factors."
            driver = "Review the key risks section for specific concerns."
            closer = "Minor adjustments could improve your chances."
    else:  # red
        tone = "cautious"
        if leg_count == 1:
            opener = "This bet carries elevated risk"
            core = "due to the nature of the selection."
        else:
            opener = f"This {bet_term} relies on multiple high-variance legs"
            core = "that compound failure risk."
        driver = "Correlation and dependency significantly reduce reliability."
        closer = "Simplifying the structure would materially improve hit rate."

    verdict_text = f"{opener} {core} {driver} {closer}"

    return {
        "verdict_text": verdict_text,
        "tone": tone,
        "grade": grade,
        "signal": signal,
    }


def _build_gentle_guidance(primary_failure: dict, signal_info: dict) -> Optional[dict]:
    """
    Build optional gentle guidance section with neutral adjustment hints.

    Ticket 26 Part C: "If you wanted to adjust this:" section.
    Rules:
    - Only show when signal is yellow or red
    - Based on primary failure type, offer 1-2 neutral suggestions
    - Never say "you should" — say "you could" or "one option would be"

    Returns dict with suggestions list, or None if not applicable.
    """
    if not signal_info:
        return None

    signal = signal_info.get("signal", "yellow")

    # Only show guidance for yellow/red signals
    if signal in ("blue", "green"):
        return None

    pf_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"

    # Guidance templates mapped to primary failure types
    guidance_map = {
        "prop_density": [
            "If you wanted to tighten this up, you could remove the prop legs.",
            "One option would be to replace a prop with a side or total.",
        ],
        "volatility": [
            "You could reduce volatility by swapping high-variance legs for sides.",
            "One option would be to split this into two smaller parlays.",
        ],
        "correlation": [
            "You could split correlated legs into separate tickets.",
            "One option would be to keep just one leg from each correlated pair.",
        ],
        "dependency": [
            "You could split dependent legs into separate tickets.",
            "One option would be to remove same-game parlays that share outcomes.",
        ],
        "same_game_dependency": [
            "Same-game legs often move together. You could move one to a separate ticket.",
            "One option would be to pair the same-game legs with independent legs instead.",
        ],
        "leg_count": [
            "Reducing by one or two legs would shift the math more in your favor.",
            "You could trim the legs you feel least confident about.",
        ],
        "fragility": [
            "You could replace the highest-fragility leg with a lower-variance pick.",
            "One option would be to reduce overall leg count to offset the fragile pick.",
        ],
    }

    # Default guidance if primary failure type not mapped
    default_guidance = [
        "You could simplify the structure by removing one or two legs.",
        "One option would be to split this into smaller parlays.",
    ]

    suggestions = guidance_map.get(pf_type, default_guidance)

    return {
        "header": "If you wanted to adjust this:",
        "suggestions": suggestions,
    }


def _build_grounding_warnings(
    evaluated_parlay: dict,
    entities: dict,
    canonical_legs: Optional[tuple] = None
) -> list:
    """
    Build soft warnings for unrecognized entities.

    Ticket 27 Part D: Grounding guardrails that acknowledge uncertainty.
    Rules:
    - Never block evaluation
    - Never guess corrections
    - Display as muted info banners

    Returns list of warning strings (empty if all entities recognized).
    """
    warnings = []

    # All major sport teams (NBA, NFL, MLB, NHL) - lowercase for matching
    known_teams = {
        # === NBA (30 teams) ===
        "lakers", "lal", "los angeles lakers",
        "celtics", "bos", "boston celtics", "boston",
        "nuggets", "den", "denver nuggets", "denver",
        "bucks", "mil", "milwaukee bucks", "milwaukee",
        "warriors", "gsw", "golden state warriors", "golden state",
        "suns", "phx", "phoenix suns", "phoenix",
        "76ers", "phi", "sixers", "philadelphia 76ers", "philadelphia",
        "mavericks", "dal", "mavs", "dallas mavericks", "dallas",
        "heat", "mia", "miami heat", "miami",
        "nets", "bkn", "brooklyn nets", "brooklyn",
        "knicks", "nyk", "new york knicks",
        "bulls", "chi", "chicago bulls", "chicago",
        "clippers", "lac", "la clippers",
        "thunder", "okc", "oklahoma city thunder", "oklahoma city", "oklahoma",
        "timberwolves", "min", "wolves", "minnesota timberwolves", "minnesota",
        "kings", "sac", "sacramento kings", "sacramento",
        "pelicans", "nop", "new orleans pelicans", "new orleans",
        "raptors", "tor", "toronto raptors", "toronto",
        "jazz", "uta", "utah jazz", "utah",
        "grizzlies", "mem", "memphis grizzlies", "memphis",
        "hawks", "atl", "atlanta hawks", "atlanta",
        "hornets", "cha", "charlotte hornets", "charlotte",
        "magic", "orl", "orlando magic", "orlando",
        "pacers", "ind", "indiana pacers", "indiana",
        "pistons", "det", "detroit pistons", "detroit",
        "spurs", "sas", "san antonio spurs", "san antonio",
        "wizards", "was", "wsh", "washington wizards", "washington",
        "cavaliers", "cle", "cavs", "cleveland cavaliers", "cleveland",
        "blazers", "por", "trail blazers", "portland trail blazers", "portland",
        "rockets", "hou", "houston rockets", "houston",

        # === NFL (32 teams) ===
        "chiefs", "kc", "kansas city chiefs", "kansas city",
        "eagles", "phi", "philadelphia eagles",
        "bills", "buf", "buffalo bills", "buffalo",
        "cowboys", "dal", "dallas cowboys",
        "49ers", "sf", "niners", "san francisco 49ers", "san francisco",
        "ravens", "bal", "baltimore ravens", "baltimore",
        "bengals", "cin", "cincinnati bengals", "cincinnati",
        "lions", "det", "detroit lions",
        "packers", "gb", "green bay packers", "green bay",
        "dolphins", "mia", "miami dolphins",
        "jets", "nyj", "new york jets",
        "giants", "nyg", "new york giants",
        "raiders", "lv", "las vegas raiders", "las vegas",
        "chargers", "lac", "la chargers", "los angeles chargers",
        "rams", "lar", "la rams", "los angeles rams",
        "patriots", "ne", "new england patriots", "new england",
        "steelers", "pit", "pittsburgh steelers", "pittsburgh",
        "browns", "cle", "cleveland browns",
        "broncos", "den", "denver broncos",
        "texans", "hou", "houston texans",
        "colts", "ind", "indianapolis colts", "indianapolis",
        "jaguars", "jax", "jags", "jacksonville jaguars", "jacksonville",
        "titans", "ten", "tennessee titans", "tennessee",
        "commanders", "was", "wsh", "washington commanders",
        "bears", "chi", "chicago bears",
        "vikings", "min", "minnesota vikings",
        "saints", "no", "new orleans saints",
        "falcons", "atl", "atlanta falcons",
        "panthers", "car", "carolina panthers", "carolina",
        "buccaneers", "tb", "bucs", "tampa bay buccaneers", "tampa bay", "tampa",
        "cardinals", "ari", "arizona cardinals", "arizona",
        "seahawks", "sea", "seattle seahawks", "seattle",

        # === MLB (30 teams) ===
        "yankees", "nyy", "new york yankees",
        "dodgers", "lad", "los angeles dodgers",
        "red sox", "bos", "boston red sox",
        "cubs", "chc", "chicago cubs",
        "astros", "hou", "houston astros",
        "braves", "atl", "atlanta braves",
        "mets", "nym", "new york mets",
        "phillies", "phi", "philadelphia phillies",
        "padres", "sd", "san diego padres", "san diego",
        "blue jays", "tor", "toronto blue jays",
        "mariners", "sea", "seattle mariners",
        "guardians", "cle", "cleveland guardians",
        "twins", "min", "minnesota twins",
        "orioles", "bal", "baltimore orioles",
        "rays", "tb", "tampa bay rays",
        "brewers", "mil", "milwaukee brewers",
        "reds", "cin", "cincinnati reds",
        "pirates", "pit", "pittsburgh pirates",
        "white sox", "chw", "chicago white sox",
        "royals", "kc", "kansas city royals",
        "tigers", "det", "detroit tigers",
        "angels", "laa", "los angeles angels", "anaheim",
        "athletics", "oak", "a's", "oakland athletics", "oakland",
        "rangers", "tex", "texas rangers", "texas",
        "giants", "sf", "san francisco giants",
        "rockies", "col", "colorado rockies", "colorado",
        "diamondbacks", "ari", "dbacks", "arizona diamondbacks",
        "marlins", "mia", "miami marlins",
        "nationals", "was", "wsh", "washington nationals",

        # === NHL (32 teams) ===
        "bruins", "bos", "boston bruins",
        "sabres", "buf", "buffalo sabres",
        "red wings", "det", "detroit red wings",
        "panthers", "fla", "florida panthers", "florida",
        "canadiens", "mtl", "habs", "montreal canadiens", "montreal",
        "senators", "ott", "ottawa senators", "ottawa",
        "lightning", "tb", "tampa bay lightning",
        "maple leafs", "tor", "leafs", "toronto maple leafs",
        "hurricanes", "car", "carolina hurricanes",
        "blue jackets", "cbj", "columbus blue jackets", "columbus",
        "devils", "njd", "new jersey devils", "new jersey",
        "islanders", "nyi", "new york islanders",
        "rangers", "nyr", "new york rangers",
        "flyers", "phi", "philadelphia flyers",
        "penguins", "pit", "pens", "pittsburgh penguins",
        "capitals", "was", "wsh", "caps", "washington capitals",
        "blackhawks", "chi", "chicago blackhawks",
        "avalanche", "col", "avs", "colorado avalanche",
        "stars", "dal", "dallas stars",
        "wild", "min", "minnesota wild",
        "predators", "nsh", "preds", "nashville predators", "nashville",
        "blues", "stl", "st louis blues", "st. louis blues", "st louis",
        "jets", "wpg", "winnipeg jets", "winnipeg",
        "ducks", "ana", "anaheim ducks",
        "coyotes", "ari", "utah hockey club", "arizona coyotes",
        "flames", "cgy", "calgary flames", "calgary",
        "oilers", "edm", "edmonton oilers", "edmonton",
        "kings", "lak", "la kings", "los angeles kings",
        "sharks", "sj", "san jose sharks", "san jose",
        "kraken", "sea", "seattle kraken",
        "canucks", "van", "vancouver canucks", "vancouver",
        "golden knights", "vgk", "vegas golden knights", "vegas",
    }

    # Extract entities from canonical legs or evaluated parlay
    entities_to_check = []

    if canonical_legs:
        for cleg in canonical_legs:
            if hasattr(cleg, 'entity') and cleg.entity:
                entities_to_check.append(cleg.entity)
    elif evaluated_parlay and evaluated_parlay.get("legs"):
        for leg in evaluated_parlay["legs"]:
            # Try to extract entity from leg text
            leg_text = leg.get("text", "")
            # Simple heuristic: first word before market keywords
            words = leg_text.lower().split()
            if words:
                entities_to_check.append(words[0])

    # Check for unrecognized entities
    unrecognized = []
    for entity in entities_to_check:
        entity_lower = entity.lower().strip()
        if entity_lower and entity_lower not in known_teams:
            # Check if it's a partial match
            matched = any(entity_lower in kt or kt in entity_lower for kt in known_teams)
            if not matched:
                unrecognized.append(entity)

    # Generate appropriate warnings
    if unrecognized:
        if len(unrecognized) == 1:
            warnings.append(f"'{unrecognized[0]}' could not be matched to a known team.")
        else:
            warnings.append("Some team names could not be recognized.")

        warnings.append("Analysis is structural only without live team data.")

    # Check if we're operating without context
    recognized_teams = entities.get("teams", []) if entities else []
    if not recognized_teams and evaluated_parlay and evaluated_parlay.get("leg_count", 0) > 0:
        if not any("could not" in w for w in warnings):
            warnings.append("This bet includes entities that may not correspond to real teams.")

    return warnings


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

    # Ticket 28: Create authoritative EvaluationContext ONCE
    # This is the ONLY place leg_count should be determined
    canonical_legs = None
    if hasattr(normalized, 'canonical_legs') and normalized.canonical_legs:
        canonical_legs = normalized.canonical_legs

    eval_ctx = EvaluationContext.create(blocks=blocks, canonical_legs=canonical_legs)
    leg_count = eval_ctx.leg_count  # For backwards compatibility with existing code

    # Ticket 27B HOTFIX: Use canonical leg count when present (builder mode)
    # This ensures ALL downstream outputs use the same leg_count
    canonical_leg_count = None
    if hasattr(normalized, 'canonical_legs') and normalized.canonical_legs:
        canonical_leg_count = len(normalized.canonical_legs)
        leg_count = canonical_leg_count  # Override with canonical count

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
    # Ticket 28: Pass eval_ctx for authoritative context
    explain_full = {
        "summary": _generate_summary(evaluation, eval_ctx=eval_ctx),
        "alerts": _generate_alerts(evaluation),
        "recommended_next_step": evaluation.recommendation.reason,
    }

    # Step 7: Build primary failure + delta preview (Ticket 4 + Ticket 14)
    # Ticket 28: Pass eval_ctx for authoritative leg_count
    primary_failure = _build_primary_failure(evaluation, blocks, entities, eval_ctx=eval_ctx)
    delta_preview = _build_delta_preview(evaluation, blocks, primary_failure)

    # Step 8: Build signal info (Ticket 5)
    signal_info = _build_signal_info(evaluation, primary_failure, delta_preview)

    # Step 9: Apply tier filtering (uses primary_failure for specific warnings/tips)
    explain_filtered = _apply_tier_filtering(normalized.tier, explain_full, evaluation, blocks, primary_failure)

    # Step 10: Sprint 2 — Compute same-game indicator + volatility flag
    same_game_info = _detect_same_game_indicator(blocks)
    volatility_flag = _compute_volatility_flag(
        entities.get("markets_detected", []),
        eval_ctx.leg_count,  # Ticket 28: Use eval_ctx
        same_game_info["same_game_count"]
    )

    # Step 11: Sprint 2 — Build secondary factors (runners-up from scoring logic)
    # Ticket 28: Pass eval_ctx for authoritative leg_count
    primary_type = primary_failure.get("type", "unknown") if primary_failure else "unknown"
    secondary_factors = _build_secondary_factors(evaluation, blocks, entities, primary_type, eval_ctx=eval_ctx)

    # Step 12: Sprint 2 — Build human summary (always included)
    # Ticket 28: Pass eval_ctx for authoritative context
    human_summary = _build_human_summary(evaluation, blocks, entities, primary_failure, eval_ctx=eval_ctx)

    # Step 13: Ticket 17 — Run Sherlock hook (if enabled)
    # Ticket 28: Use eval_ctx.leg_count for consistency
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
            leg_count=eval_ctx.leg_count,
        )
        if hook_result:
            sherlock_result = hook_result.to_dict()

    # Step 14: Ticket 18 — Transform Sherlock output to explainability blocks
    debug_explainability = None
    explainability_output = transform_sherlock_to_explainability(sherlock_result)
    if explainability_output:
        debug_explainability = explainability_output.to_dict()

    # Step 15: Ticket 20 — Emit real DNA artifacts from evaluation data
    # Artifacts are deterministic, derived, and never persisted.
    # Ticket 28: Use eval_ctx.leg_count for consistency
    dna_artifacts = emit_artifacts_from_evaluation(
        evaluation_metrics={
            "final_fragility": evaluation.metrics.final_fragility,
            "correlation_penalty": evaluation.metrics.correlation_penalty,
            "leg_penalty": evaluation.metrics.leg_penalty,
        },
        signal=signal_info.get("signal", "yellow") if signal_info else "yellow",
        leg_count=eval_ctx.leg_count,
        primary_failure_type=primary_type,
        request_id=str(evaluation.parlay_id),
    )
    dna_artifact_counts = get_artifact_counts(dna_artifacts)

    # Step 16: Ticket 19 — Validate DNA artifacts against contract
    contract_validation = None
    if dna_artifacts:
        validation_result = validate_dna_artifacts(dna_artifacts)
        contract_validation = validation_result.to_dict()
        if not validation_result.ok:
            _logger.warning(
                f"DNA contract validation FAILED: {len(validation_result.errors)} errors. "
                f"Artifacts quarantined."
            )
    else:
        # No artifacts to validate - still get contract version for proof summary
        contract_validation = {
            "ok": True,
            "errors": [],
            "contract_version": get_contract_version(),
            "artifact_count": 0,
            "quarantined": False,
        }

    # Step 17: Ticket 21 — Validate and normalize artifacts for UI via UI contract
    # This is the final safety layer before artifacts reach the proof panel.
    ui_validation = validate_for_ui(dna_artifacts)
    ui_artifacts = ui_validation.normalized_artifacts  # Safe for UI
    ui_contract_status = ui_validation.ui_contract_status
    ui_contract_version = ui_validation.ui_contract_version

    if not ui_validation.ok:
        _logger.warning(
            f"UI contract validation FAILED: {len(ui_validation.errors)} errors. "
            f"Using fallback artifact for display."
        )

    # Step 18: Ticket 18B — Derive proof summary for UI display (with UI-safe artifacts)
    proof_summary = derive_proof_summary(
        sherlock_enabled=_config.sherlock_enabled,
        dna_recording_enabled=_config.dna_recording_enabled,
        explainability_output=debug_explainability,
        contract_validation=contract_validation,
        dna_artifacts=ui_artifacts,  # Use UI-validated artifacts
        dna_artifact_counts=dna_artifact_counts,
        ui_contract_status=ui_contract_status,
        ui_contract_version=ui_contract_version,
    ).to_dict()

    # Build public entity output (strip internal _raw_text, add Sprint 2 fields)
    entities_public = {k: v for k, v in entities.items() if not k.startswith("_")}
    entities_public["volatility_flag"] = volatility_flag
    entities_public["same_game_indicator"] = same_game_info

    # Step 19: Ticket 25 — Build evaluated parlay receipt (what was evaluated)
    # Ticket 27: Pass canonical legs if present (builder mode)
    evaluated_parlay = _build_evaluated_parlay(
        blocks,
        normalized.input_text,
        canonical_legs=normalized.canonical_legs if hasattr(normalized, 'canonical_legs') else None
    )

    # Step 20: Ticket 25 — Build notable legs (leg-aware context)
    notable_legs = _build_notable_legs(blocks, evaluation, primary_failure)

    # Step 21: Ticket 25 — Build final verdict (conclusive summary)
    # Ticket 28: Pass eval_ctx for authoritative context
    final_verdict = _build_final_verdict(evaluation, blocks, entities, primary_failure, signal_info, eval_ctx=eval_ctx)

    # Step 22: Ticket 26 — Build gentle guidance (optional adjustment hints)
    gentle_guidance = _build_gentle_guidance(primary_failure, signal_info)

    # Step 23: Ticket 27 — Build grounding warnings (soft warnings for unrecognized entities)
    grounding_warnings = _build_grounding_warnings(
        evaluated_parlay,
        entities_public,
        canonical_legs=normalized.canonical_legs if hasattr(normalized, 'canonical_legs') else None
    )

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
        evaluated_parlay=evaluated_parlay,
        notable_legs=notable_legs,
        final_verdict=final_verdict,
        gentle_guidance=gentle_guidance,
        grounding_warnings=grounding_warnings if grounding_warnings else None,
        sherlock_result=sherlock_result,
        debug_explainability=debug_explainability,
        proof_summary=proof_summary,
        leg_count=eval_ctx.leg_count,  # Ticket 28: Use authoritative context
        tier=normalized.tier.value,
    )
