# app/routers/web.py
"""
Web UI Router - Minimal browser interface for evaluation.

This is a strict system boundary:
- Browser never calls internal APIs directly
- All evaluation proxied through /app/evaluate
- Server remains source of truth for tier enforcement
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.config import load_config


router = APIRouter(tags=["Web UI"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class WebEvaluateRequest(BaseModel):
    """Request schema for web evaluation proxy."""
    input: str = Field(..., min_length=1, description="Bet text input")
    tier: str = Field(..., description="Plan tier: GOOD, BETTER, or BEST")

    @field_validator("input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        """Validate input is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("input cannot be empty or whitespace")
        return v.strip()

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """Validate tier is one of GOOD/BETTER/BEST."""
        valid_tiers = {"good", "better", "best"}
        if v.lower() not in valid_tiers:
            raise ValueError(f"tier must be one of: GOOD, BETTER, BEST")
        return v.lower()


# =============================================================================
# HTML Templates
# =============================================================================


def _get_landing_page_html() -> str:
    """Generate landing page HTML."""
    config = load_config()
    git_sha_display = config.git_sha or "not set"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Matrix - Leading Light</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }}
        .container {{
            max-width: 600px;
            text-align: center;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #fff;
        }}
        .subtitle {{
            color: #888;
            margin-bottom: 2rem;
        }}
        .links {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-bottom: 2rem;
        }}
        a {{
            color: #4a9eff;
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border: 1px solid #4a9eff;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        a:hover {{
            background: #4a9eff;
            color: #000;
        }}
        .info {{
            font-size: 0.875rem;
            color: #666;
            margin-top: 2rem;
        }}
        .sha {{
            font-family: monospace;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DNA Matrix</h1>
        <p class="subtitle">Leading Light Evaluation Engine</p>
        <div class="links">
            <a href="/app">Launch App</a>
            <a href="/health">Health Check</a>
        </div>
        <p class="info">
            Version: {config.service_version} |
            Git SHA: <span class="sha">{git_sha_display[:8] if len(git_sha_display) > 8 else git_sha_display}</span>
        </p>
    </div>
</body>
</html>"""


def _get_app_page_html() -> str:
    """Generate app page HTML with evaluation form."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leading Light - Evaluate</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #333;
        }
        h1 { font-size: 1.5rem; color: #fff; }
        header a {
            color: #4a9eff;
            text-decoration: none;
            font-size: 0.875rem;
        }
        .form-section {
            background: #111;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        textarea {
            width: 100%;
            min-height: 120px;
            padding: 1rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-family: inherit;
            font-size: 1rem;
            resize: vertical;
        }
        textarea:focus {
            outline: none;
            border-color: #4a9eff;
        }
        .tier-selector {
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }
        .tier-option {
            flex: 1;
            position: relative;
        }
        .tier-option input {
            position: absolute;
            opacity: 0;
        }
        .tier-option label {
            display: block;
            padding: 1rem;
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 4px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tier-option input:checked + label {
            border-color: #4a9eff;
            background: #1a2a3a;
        }
        .tier-option label:hover {
            border-color: #555;
        }
        .tier-name {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .tier-desc {
            font-size: 0.75rem;
            color: #888;
        }
        button {
            width: 100%;
            padding: 1rem;
            background: #4a9eff;
            border: none;
            border-radius: 4px;
            color: #000;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #3a8eef; }
        button:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
        }
        .output-section {
            display: none;
        }
        .output-section.visible {
            display: block;
        }
        .panel {
            background: #111;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .panel h2 {
            font-size: 1rem;
            margin-bottom: 1rem;
            color: #fff;
        }
        .panel-content {
            font-family: monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
            word-break: break-word;
            background: #0a0a0a;
            padding: 1rem;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
        }
        .error-panel {
            border: 1px solid #ff4a4a;
        }
        .error-panel h2 {
            color: #ff4a4a;
        }
        .tier-notice {
            background: #2a2a1a;
            border: 1px solid #665500;
            padding: 0.75rem 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
            font-size: 0.875rem;
            color: #ccaa00;
        }
        .tier-notice.hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Leading Light</h1>
            <a href="/">Back to Home</a>
        </header>

        <div class="form-section">
            <label for="bet-input">Bet Description</label>
            <textarea id="bet-input" placeholder="Enter your bet description...&#10;Example: Lakers -5.5 + Celtics ML parlay"></textarea>

            <label style="margin-top: 1rem;">Select Tier</label>
            <div class="tier-selector">
                <div class="tier-option">
                    <input type="radio" name="tier" id="tier-good" value="good" checked>
                    <label for="tier-good">
                        <div class="tier-name">GOOD</div>
                        <div class="tier-desc">Basic evaluation</div>
                    </label>
                </div>
                <div class="tier-option">
                    <input type="radio" name="tier" id="tier-better" value="better">
                    <label for="tier-better">
                        <div class="tier-name">BETTER</div>
                        <div class="tier-desc">+ Summary</div>
                    </label>
                </div>
                <div class="tier-option">
                    <input type="radio" name="tier" id="tier-best" value="best">
                    <label for="tier-best">
                        <div class="tier-name">BEST</div>
                        <div class="tier-desc">+ Full explain</div>
                    </label>
                </div>
            </div>

            <button id="submit-btn" type="button">Evaluate</button>
        </div>

        <div class="output-section" id="output-section">
            <div class="tier-notice hidden" id="tier-notice">
                Explain details withheld based on tier. Upgrade to BETTER or BEST for more insights.
            </div>

            <div class="panel" id="eval-panel">
                <h2>Evaluation</h2>
                <div class="panel-content" id="eval-content"></div>
            </div>

            <div class="panel" id="explain-panel">
                <h2>Explain</h2>
                <div class="panel-content" id="explain-content"></div>
            </div>

            <div class="panel error-panel hidden" id="error-panel">
                <h2>Error</h2>
                <div class="panel-content" id="error-content"></div>
            </div>
        </div>
    </div>

    <script>
        (function() {
            const betInput = document.getElementById('bet-input');
            const submitBtn = document.getElementById('submit-btn');
            const outputSection = document.getElementById('output-section');
            const tierNotice = document.getElementById('tier-notice');
            const evalContent = document.getElementById('eval-content');
            const explainContent = document.getElementById('explain-content');
            const errorPanel = document.getElementById('error-panel');
            const errorContent = document.getElementById('error-content');
            const evalPanel = document.getElementById('eval-panel');
            const explainPanel = document.getElementById('explain-panel');

            function getSelectedTier() {
                const selected = document.querySelector('input[name="tier"]:checked');
                return selected ? selected.value : 'good';
            }

            function showError(message) {
                outputSection.classList.add('visible');
                errorPanel.classList.remove('hidden');
                evalPanel.style.display = 'none';
                explainPanel.style.display = 'none';
                tierNotice.classList.add('hidden');
                // Use textContent for security
                errorContent.textContent = typeof message === 'string'
                    ? message
                    : JSON.stringify(message, null, 2);
            }

            function showResult(data) {
                outputSection.classList.add('visible');
                errorPanel.classList.add('hidden');
                evalPanel.style.display = 'block';
                explainPanel.style.display = 'block';

                // Display evaluation (always present)
                const evalData = {
                    input: data.input,
                    evaluation: data.evaluation,
                    interpretation: data.interpretation
                };
                // Use textContent for security - display as pretty JSON
                evalContent.textContent = JSON.stringify(evalData, null, 2);

                // Display explain (may be empty based on tier)
                const explain = data.explain || {};
                const explainIsEmpty = Object.keys(explain).length === 0;

                // Use textContent for security
                explainContent.textContent = explainIsEmpty
                    ? '(No explain data for this tier)'
                    : JSON.stringify(explain, null, 2);

                // Show tier notice if explain is empty and tier is GOOD
                const tier = getSelectedTier();
                if (explainIsEmpty && tier === 'good') {
                    tierNotice.classList.remove('hidden');
                } else {
                    tierNotice.classList.add('hidden');
                }
            }

            async function submitEvaluation() {
                const input = betInput.value.trim();
                const tier = getSelectedTier();

                if (!input) {
                    showError('Please enter a bet description');
                    return;
                }

                submitBtn.disabled = true;
                submitBtn.textContent = 'Evaluating...';

                try {
                    const response = await fetch('/app/evaluate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ input, tier })
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        showError(data.detail || data);
                        return;
                    }

                    showResult(data);
                } catch (err) {
                    showError('Network error: ' + err.message);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Evaluate';
                }
            }

            submitBtn.addEventListener('click', submitEvaluation);

            // Allow Ctrl+Enter to submit
            betInput.addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    submitEvaluation();
                }
            });
        })();
    </script>
</body>
</html>"""


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    """
    Landing page with service info and navigation.

    Returns HTML with:
    - Service name
    - Link to /app
    - Link to /health
    - Current git_sha
    """
    return _get_landing_page_html()


@router.get("/app", response_class=HTMLResponse)
async def app_page():
    """
    Main application page with evaluation form.

    Returns HTML with:
    - Bet text textarea
    - Tier selector (GOOD, BETTER, BEST)
    - Submit button
    - Output panels for evaluation, explain, and errors
    """
    return _get_app_page_html()


@router.post("/app/evaluate")
async def evaluate_proxy(request: WebEvaluateRequest):
    """
    Server-side proxy for evaluation requests.

    This endpoint exists to:
    1. Validate input before hitting internal APIs
    2. Ensure browser cannot bypass tier enforcement
    3. Provide a single boundary for future auth/rate limiting

    Calls /leading-light/evaluate/text internally and returns the response.
    """
    from app.routers.leading_light import (
        is_leading_light_enabled,
        _parse_bet_text,
        _generate_summary,
        _generate_alerts,
        _interpret_fragility,
        _apply_tier_to_explain_wrapper,
    )
    from core.evaluation import evaluate_parlay

    # Check feature flag
    if not is_leading_light_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Leading Light disabled",
                "detail": "The Leading Light feature is currently disabled.",
                "code": "SERVICE_DISABLED",
            },
        )

    try:
        # Parse bet text into blocks
        blocks = _parse_bet_text(request.input)

        # Call the canonical evaluation engine
        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=None,
            bankroll=None,
            candidates=None,
            max_suggestions=0,
        )

        # Build plain-English explain wrapper
        summary = _generate_summary(response, len(blocks))
        alerts = _generate_alerts(response)
        recommended_step = response.recommendation.reason

        # Build fragility interpretation
        fragility_interpretation = _interpret_fragility(response.metrics.final_fragility)

        # Build explain wrapper (before tier filtering)
        explain_full = {
            "summary": summary,
            "alerts": alerts,
            "recommended_next_step": recommended_step,
        }

        # Apply tier filtering to explain wrapper
        explain_filtered = _apply_tier_to_explain_wrapper(request.tier, explain_full)

        # Build response
        return {
            "input": {
                "bet_text": request.input,
                "tier": request.tier,
            },
            "evaluation": {
                "parlay_id": str(response.parlay_id),
                "inductor": {
                    "level": response.inductor.level.value,
                    "explanation": response.inductor.explanation,
                },
                "metrics": {
                    "raw_fragility": response.metrics.raw_fragility,
                    "final_fragility": response.metrics.final_fragility,
                    "leg_penalty": response.metrics.leg_penalty,
                    "correlation_penalty": response.metrics.correlation_penalty,
                    "correlation_multiplier": response.metrics.correlation_multiplier,
                },
                "correlations": [
                    {
                        "block_a": str(c.block_a),
                        "block_b": str(c.block_b),
                        "type": c.type,
                        "penalty": c.penalty,
                    }
                    for c in response.correlations
                ],
                "recommendation": {
                    "action": response.recommendation.action.value,
                    "reason": response.recommendation.reason,
                },
            },
            "interpretation": {
                "fragility": fragility_interpretation,
            },
            "explain": explain_filtered,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid input",
                "detail": str(e),
                "code": "VALIDATION_ERROR",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal error",
                "detail": str(e),
                "code": "INTERNAL_ERROR",
            },
        )
