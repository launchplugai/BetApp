"""
v1 UI Router - Server-rendered, no-JS-required UI.

All routes return full HTML pages.
All navigation uses <a href>.
All form submission uses <form method="POST">.
JavaScript is optional enhancement only.

Reference: docs/UI_SPEC.md
"""
import logging
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from typing import Optional, List
import json

from app.data.leagues import LEAGUES, BET_TYPES, get_team_name, format_leg

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["v1-ui"])


# =============================================================================
# Base Template
# =============================================================================

def _base_template(title: str, content: str, active_nav: str = "") -> str:
    """
    Server-rendered base template.

    Mobile-first, no JS required for core functionality.
    Reference device: iPhone Safari.
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - DNA Bet Engine</title>
    <style>
        /* Reset */
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        /* Base */
        html {{
            font-size: 16px;
            -webkit-text-size-adjust: 100%;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.5;
            color: #1a1a1a;
            background: #f5f5f5;
            min-height: 100vh;
        }}

        /* Header */
        .header {{
            background: #1a1a1a;
            color: #fff;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #fff;
            text-decoration: none;
        }}

        .header-link {{
            color: #a0a0a0;
            text-decoration: none;
            font-size: 0.875rem;
            padding: 0.5rem 1rem;
            min-height: 44px;
            display: flex;
            align-items: center;
        }}

        .header-link:hover {{
            color: #fff;
        }}

        /* Navigation */
        .nav {{
            background: #262626;
            padding: 0.5rem 1rem;
            display: flex;
            gap: 0.5rem;
        }}

        .nav-link {{
            color: #a0a0a0;
            text-decoration: none;
            padding: 0.75rem 1rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
            min-height: 44px;
            display: flex;
            align-items: center;
        }}

        .nav-link:hover {{
            color: #fff;
            background: #333;
        }}

        .nav-link.active {{
            color: #fff;
            background: #404040;
        }}

        /* Main Content */
        .main {{
            padding: 1rem;
            max-width: 600px;
            margin: 0 auto;
        }}

        /* Cards */
        .card {{
            background: #fff;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .card-title {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #666;
            margin-bottom: 0.75rem;
        }}

        /* Forms */
        label {{
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #333;
        }}

        select, input[type="text"], input[type="number"] {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            font-size: 1rem;
            font-family: inherit;
            background: #fff;
            min-height: 44px;
        }}

        select:focus, input:focus {{
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }}

        fieldset {{
            border: none;
            margin: 1rem 0;
        }}

        legend {{
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            color: #333;
        }}

        .radio-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .radio-label {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            cursor: pointer;
            min-height: 44px;
            flex: 1;
            min-width: 45%;
        }}

        .radio-label:has(input:checked) {{
            border-color: #2563eb;
            background: #eff6ff;
        }}

        input[type="radio"] {{
            width: 1.25rem;
            height: 1.25rem;
            accent-color: #2563eb;
        }}

        .form-row {{
            margin-bottom: 1rem;
        }}

        .form-row-inline {{
            display: flex;
            gap: 0.75rem;
        }}

        .form-row-inline > * {{
            flex: 1;
        }}

        /* Buttons */
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 500;
            border-radius: 0.375rem;
            text-decoration: none;
            cursor: pointer;
            min-height: 44px;
            border: none;
        }}

        .btn-primary {{
            background: #2563eb;
            color: #fff;
        }}

        .btn-primary:hover {{
            background: #1d4ed8;
        }}

        .btn-secondary {{
            background: #e5e5e5;
            color: #333;
        }}

        .btn-secondary:hover {{
            background: #d4d4d4;
        }}

        .btn-success {{
            background: #16a34a;
            color: #fff;
        }}

        .btn-success:hover {{
            background: #15803d;
        }}

        .btn-danger {{
            background: #dc2626;
            color: #fff;
            padding: 0.5rem 0.75rem;
            font-size: 0.875rem;
        }}

        .btn-full {{
            width: 100%;
        }}

        /* Actions row */
        .actions {{
            display: flex;
            gap: 0.75rem;
            margin-top: 1rem;
        }}

        .actions .btn {{
            flex: 1;
        }}

        /* Back link */
        .back-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            color: #2563eb;
            text-decoration: none;
            font-size: 0.875rem;
            padding: 0.5rem 0;
            min-height: 44px;
        }}

        .back-link:hover {{
            text-decoration: underline;
        }}

        /* Parlay legs list */
        .leg-list {{
            list-style: none;
        }}

        .leg-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            border-bottom: 1px solid #eee;
            gap: 0.5rem;
        }}

        .leg-item:last-child {{
            border-bottom: none;
        }}

        .leg-text {{
            flex: 1;
            font-size: 0.9375rem;
        }}

        .leg-number {{
            background: #e5e5e5;
            color: #666;
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
            flex-shrink: 0;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-green {{
            background: #dcfce7;
            color: #166534;
        }}

        .badge-yellow {{
            background: #fef9c3;
            color: #854d0e;
        }}

        .badge-red {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .badge-gray {{
            background: #f3f4f6;
            color: #374151;
        }}

        /* Errors box */
        .errors-box {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.375rem;
            padding: 1rem;
            color: #991b1b;
        }}

        /* Metrics */
        .metrics-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }}

        .metrics-row:last-child {{
            border-bottom: none;
        }}

        .metrics-label {{
            color: #666;
        }}

        .metrics-value {{
            font-weight: 600;
            font-family: ui-monospace, monospace;
        }}

        /* Tier badge in header */
        .tier-badge {{
            font-size: 0.625rem;
            padding: 0.125rem 0.5rem;
            margin-left: 0.5rem;
            vertical-align: middle;
        }}

        /* Empty state */
        .empty-state {{
            text-align: center;
            padding: 2rem 1rem;
            color: #666;
        }}

        .empty-state p {{
            margin-bottom: 1rem;
        }}

        /* Parlay summary */
        .parlay-summary {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 0.375rem;
            padding: 0.75rem;
            margin-bottom: 1rem;
            font-size: 0.875rem;
            color: #0369a1;
        }}

        /* Optgroup styling */
        optgroup {{
            font-weight: 600;
            color: #333;
        }}

        option {{
            font-weight: normal;
            padding: 0.5rem;
        }}
    </style>
</head>
<body>
    <header class="header">
        <a href="/v1" class="header-title">DNA BET ENGINE</a>
        <a href="/v1/account" class="header-link">Account</a>
    </header>

    <nav class="nav">
        <a href="/v1/build" class="nav-link {"active" if active_nav == "build" else ""}">Builder</a>
        <a href="/v1/history" class="nav-link {"active" if active_nav == "history" else ""}">History</a>
    </nav>

    <main class="main">
        {content}
    </main>
</body>
</html>'''


# =============================================================================
# Team Options Generator
# =============================================================================

def _build_team_options(selected_league: str = "", selected_team: str = "") -> str:
    """Build team <option> tags grouped by league."""
    options = ['<option value="">-- Select Team --</option>']

    for league_code, league_data in LEAGUES.items():
        options.append(f'<optgroup label="{league_data["name"]}">')
        for team_abbrev, team_name in sorted(league_data["teams"].items(), key=lambda x: x[1]):
            value = f"{league_code}:{team_abbrev}"
            selected = "selected" if value == f"{selected_league}:{selected_team}" else ""
            options.append(f'<option value="{value}" {selected}>{team_name}</option>')
        options.append('</optgroup>')

    return "\n".join(options)


def _build_evaluate_section(legs_json: str) -> str:
    """Build the evaluate form section."""
    return f'''
        <form method="POST" action="/v1/evaluate">
            <input type="hidden" name="legs" value='{legs_json}'>

            <fieldset>
                <legend>Select Tier</legend>
                <div class="radio-group">
                    <label class="radio-label">
                        <input type="radio" name="tier" value="GOOD" checked>
                        <span>GOOD</span>
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="tier" value="BETTER">
                        <span>BETTER</span>
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="tier" value="BEST">
                        <span>BEST</span>
                    </label>
                </div>
            </fieldset>

            <button type="submit" class="btn btn-success btn-full">
                Evaluate Parlay
            </button>
        </form>
    '''


def _build_clear_button() -> str:
    """Build the clear parlay button."""
    return '''
        <div style="margin-top: 1rem;">
            <a href="/v1/build" class="btn btn-secondary btn-full">Clear Parlay</a>
        </div>
    '''


def _build_needs_more_legs_message() -> str:
    """Build the message shown when parlay has only 1 leg."""
    return '''
        <div class="card" style="background: #fefce8; border: 1px solid #fef08a;">
            <p style="color: #854d0e; margin: 0; text-align: center;">
                Add at least one more leg to evaluate your parlay.
            </p>
        </div>
    '''


def _build_parlay_legs_html(legs: List[dict]) -> str:
    """Build HTML for current parlay legs."""
    if not legs:
        return '<p class="empty-state">No legs added yet. Add your first leg above.</p>'

    items = []
    for i, leg in enumerate(legs):
        leg_text = leg.get("display", "Unknown leg")
        items.append(f'''
            <li class="leg-item">
                <span class="leg-number">{i + 1}</span>
                <span class="leg-text">{leg_text}</span>
            </li>
        ''')

    return f'<ul class="leg-list">{"".join(items)}</ul>'


# =============================================================================
# Routes
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def v1_home():
    """Landing page with links to Builder and History."""
    content = '''
        <div class="card">
            <h1 style="font-size: 1.5rem; margin-bottom: 0.5rem;">Welcome to DNA Bet Engine</h1>
            <p style="color: #666; margin-bottom: 1.5rem;">
                Evaluate your parlays with our tier-gated analysis engine.
            </p>
            <div class="actions">
                <a href="/v1/build" class="btn btn-primary">Build a Parlay</a>
                <a href="/v1/history" class="btn btn-secondary">View History</a>
            </div>
        </div>

        <div class="card">
            <div class="card-title">How It Works</div>
            <ol style="padding-left: 1.25rem; color: #666;">
                <li style="margin-bottom: 0.5rem;">Select a team from any major league</li>
                <li style="margin-bottom: 0.5rem;">Choose your bet type (spread, ML, total)</li>
                <li style="margin-bottom: 0.5rem;">Add legs to build your parlay</li>
                <li style="margin-bottom: 0.5rem;">Get your evaluation debrief</li>
            </ol>
        </div>
    '''
    return HTMLResponse(content=_base_template("Home", content, active_nav=""))


@router.get("/build", response_class=HTMLResponse)
async def v1_build(legs: str = ""):
    """Parlay builder form with structured selection."""
    # Parse existing legs from query param (JSON encoded)
    current_legs = []
    if legs:
        try:
            current_legs = json.loads(legs)
        except:
            pass

    legs_json = json.dumps(current_legs)
    legs_html = _build_parlay_legs_html(current_legs)
    team_options = _build_team_options()

    leg_count = len(current_legs)
    can_evaluate = leg_count >= 2
    needs_more_legs = leg_count == 1

    content = f'''
        <div class="card">
            <div class="card-title">Add a Leg</div>

            <form method="POST" action="/v1/build/add">
                <input type="hidden" name="legs" value='{legs_json}'>

                <div class="form-row">
                    <label for="team">Team</label>
                    <select id="team" name="team" required>
                        {team_options}
                    </select>
                </div>

                <fieldset>
                    <legend>Bet Type</legend>
                    <div class="radio-group">
                        <label class="radio-label">
                            <input type="radio" name="bet_type" value="spread" checked>
                            <span>Spread</span>
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="bet_type" value="ml">
                            <span>Moneyline</span>
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="bet_type" value="total">
                            <span>Total O/U</span>
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="bet_type" value="team_total">
                            <span>Team Total</span>
                        </label>
                    </div>
                </fieldset>

                <div class="form-row form-row-inline">
                    <div>
                        <label for="line">Line</label>
                        <input type="text" id="line" name="line" placeholder="5.5" inputmode="decimal">
                    </div>
                    <div>
                        <label for="direction">Direction</label>
                        <select id="direction" name="direction">
                            <option value="minus">Minus (-) / Under</option>
                            <option value="plus">Plus (+) / Over</option>
                        </select>
                    </div>
                </div>

                <button type="submit" class="btn btn-secondary btn-full">
                    + Add Leg to Parlay
                </button>
            </form>
        </div>

        <div class="card">
            <div class="card-title">Your Parlay ({leg_count} leg{"s" if leg_count != 1 else ""})</div>
            {legs_html}
        </div>

        {_build_evaluate_section(legs_json) if can_evaluate else ""}

        {_build_needs_more_legs_message() if needs_more_legs else ""}

        {_build_clear_button() if leg_count > 0 else ""}
    '''

    return HTMLResponse(content=_base_template("Build", content, active_nav="build"))


@router.post("/build/add", response_class=HTMLResponse)
async def v1_build_add(
    team: str = Form(""),
    bet_type: str = Form("spread"),
    line: str = Form(""),
    direction: str = Form("minus"),
    legs: str = Form("[]"),
):
    """Add a leg to the parlay and redirect back to builder."""
    from fastapi.responses import RedirectResponse
    import urllib.parse

    # Parse current legs
    current_legs = []
    try:
        current_legs = json.loads(legs)
    except:
        pass

    # Parse team (format: "LEAGUE:TEAM")
    if ":" in team:
        league, team_abbrev = team.split(":", 1)
    else:
        # Redirect back with error
        return RedirectResponse(
            url=f"/v1/build?legs={urllib.parse.quote(json.dumps(current_legs))}",
            status_code=303
        )

    # Build display text
    team_name = get_team_name(league, team_abbrev)

    if bet_type == "spread":
        sign = "+" if direction == "plus" else "-"
        display = f"{team_name} {sign}{line}" if line else f"{team_name} {sign}0"
    elif bet_type == "ml":
        display = f"{team_name} ML"
    elif bet_type == "total":
        ou = "o" if direction == "plus" else "u"
        display = f"{team_name} {ou}{line}" if line else f"{team_name} {ou}0"
    elif bet_type == "team_total":
        ou = "o" if direction == "plus" else "u"
        display = f"{team_name} TT {ou}{line}" if line else f"{team_name} TT {ou}0"
    else:
        display = f"{team_name} {bet_type}"

    # Add new leg
    new_leg = {
        "league": league,
        "team": team_abbrev,
        "bet_type": bet_type,
        "line": line,
        "direction": direction,
        "display": display,
    }
    current_legs.append(new_leg)

    # Debug logging (no secrets, no PII)
    _logger.info(f"v1_build_add: legs_count={len(current_legs)}")

    # Redirect back to builder with updated legs
    legs_param = urllib.parse.quote(json.dumps(current_legs))
    return RedirectResponse(url=f"/v1/build?legs={legs_param}", status_code=303)


@router.get("/history", response_class=HTMLResponse)
async def v1_history():
    """History page - placeholder for v1."""
    content = '''
        <div class="card">
            <div class="card-title">Evaluation History</div>
            <div class="empty-state">
                <p>History tracking coming soon.</p>
                <a href="/v1/build" class="btn btn-primary">Build a Parlay</a>
            </div>
        </div>
    '''
    return HTMLResponse(content=_base_template("History", content, active_nav="history"))


@router.get("/account", response_class=HTMLResponse)
async def v1_account():
    """Account page - placeholder for v1."""
    content = '''
        <div class="card">
            <div class="card-title">Account</div>
            <div class="empty-state">
                <p>Login not enabled in v1.</p>
                <a href="/v1/build" class="btn btn-secondary">Back to Builder</a>
            </div>
        </div>
    '''
    return HTMLResponse(content=_base_template("Account", content, active_nav=""))


@router.post("/evaluate", response_class=HTMLResponse)
async def v1_evaluate(
    legs: str = Form("[]"),
    tier: str = Form("GOOD"),
):
    """
    Evaluate parlay and return server-rendered debrief page.

    This endpoint:
    1. Accepts form POST (no JSON, no JS required)
    2. Converts structured legs to text format for engine
    3. Passes through Airlock for validation
    4. Runs evaluation via Pipeline
    5. Returns full HTML debrief page
    """
    from app.airlock import airlock_ingest, AirlockError
    from app.pipeline import run_evaluation

    # Parse legs
    try:
        leg_list = json.loads(legs)
    except:
        leg_list = []

    # Debug logging (no secrets, no PII)
    _logger.info(f"v1_evaluate: legs_count={len(leg_list)}, tier={tier}")

    if not leg_list:
        return _render_debrief_error(
            legs=[],
            tier=tier,
            error="No legs in parlay. Please add at least two legs."
        )

    # Enforce minimum 2 legs
    if len(leg_list) < 2:
        return _render_debrief_error(
            legs=leg_list,
            tier=tier,
            error="Parlay requires at least 2 legs. Please add another leg."
        )

    # Convert structured legs to text format for engine
    leg_displays = [leg.get("display", "") for leg in leg_list]
    input_text = "\n".join(leg_displays)

    try:
        # Airlock validation
        normalized = airlock_ingest(
            input_text=input_text,
            tier=tier,
        )

        # Run evaluation
        result = run_evaluation(normalized)

        # Render debrief
        return _render_debrief_success(
            legs=leg_list,
            tier=result.tier,
            evaluation=result.evaluation,
        )

    except AirlockError as e:
        return _render_debrief_error(
            legs=leg_list,
            tier=tier,
            error=f"Validation Error: {e.message}"
        )
    except Exception as e:
        return _render_debrief_error(
            legs=leg_list,
            tier=tier,
            error=f"Evaluation Error: {str(e)}"
        )


# =============================================================================
# Debrief Renderers
# =============================================================================

def _render_debrief_success(legs: list, tier: str, evaluation) -> HTMLResponse:
    """Render successful evaluation debrief."""

    # Inductor level badge color
    level = evaluation.inductor.level.value
    badge_class = {
        "GREEN": "badge-green",
        "YELLOW": "badge-yellow",
        "RED": "badge-red",
    }.get(level, "badge-gray")

    # Build legs HTML
    legs_html = _build_parlay_legs_html(legs)

    # Build metrics HTML
    metrics = evaluation.metrics
    metrics_html = f'''
        <div class="metrics-row">
            <span class="metrics-label">Raw Fragility</span>
            <span class="metrics-value">{metrics.raw_fragility:.2f}</span>
        </div>
        <div class="metrics-row">
            <span class="metrics-label">Final Fragility</span>
            <span class="metrics-value">{metrics.final_fragility:.2f}</span>
        </div>
        <div class="metrics-row">
            <span class="metrics-label">Leg Penalty</span>
            <span class="metrics-value">{metrics.leg_penalty:.2f}</span>
        </div>
        <div class="metrics-row">
            <span class="metrics-label">Correlation Penalty</span>
            <span class="metrics-value">{metrics.correlation_penalty:.2f}</span>
        </div>
    '''

    content = f'''
        <a href="/v1/build" class="back-link">&larr; Back to Builder</a>

        <div class="card">
            <div class="card-title">Your Parlay</div>
            {legs_html}
        </div>

        <div class="card">
            <div class="card-title">Verdict</div>
            <span class="badge {badge_class}">{level}</span>
        </div>

        <div class="card">
            <div class="card-title">Explanation</div>
            <p style="color: #333;">{evaluation.inductor.explanation}</p>
        </div>

        <div class="card">
            <div class="card-title">
                Metrics
                <span class="badge badge-gray tier-badge">{tier}</span>
            </div>
            {metrics_html}
        </div>

        <div class="actions">
            <a href="/v1/build" class="btn btn-primary">Build Another</a>
            <a href="/v1/history" class="btn btn-secondary">View History</a>
        </div>
    '''

    return HTMLResponse(content=_base_template("Debrief", content, active_nav=""))


def _render_debrief_error(legs: list, tier: str, error: str) -> HTMLResponse:
    """Render debrief page with error."""

    legs_html = _build_parlay_legs_html(legs)

    content = f'''
        <a href="/v1/build" class="back-link">&larr; Back to Builder</a>

        <div class="card">
            <div class="card-title">Your Parlay</div>
            {legs_html}
        </div>

        <div class="card">
            <div class="card-title">Verdict</div>
            <span class="badge badge-gray">UNKNOWN</span>
        </div>

        <div class="card">
            <div class="card-title">Explanation</div>
            <p style="color: #666;">Unable to evaluate parlay.</p>
        </div>

        <div class="card">
            <div class="card-title">
                Metrics
                <span class="badge badge-gray tier-badge">{tier}</span>
            </div>
            <p style="color: #666;">No metrics available.</p>
        </div>

        <div class="card" style="padding: 0; background: transparent; box-shadow: none;">
            <div class="errors-box">
                <strong>Error:</strong> {error}
            </div>
        </div>

        <div class="actions">
            <a href="/v1/build" class="btn btn-primary">Try Again</a>
            <a href="/v1/history" class="btn btn-secondary">View History</a>
        </div>
    '''

    return HTMLResponse(content=_base_template("Debrief - Error", content, active_nav=""))
