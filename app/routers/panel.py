# app/routers/panel.py
"""
Developer Panel UI Router.

Provides a phone-simulated interface for testing Leading Light endpoints.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Panel"])


@router.get("/panel", response_class=HTMLResponse)
async def dev_panel():
    """Render developer testing panel UI."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leading Light - Dev Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .phone-frame {
            background: white;
            max-width: 420px;
            width: 100%;
            min-height: 700px;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 24px;
            font-weight: 600;
        }

        .tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
        }

        .tab {
            flex: 1;
            padding: 16px;
            text-align: center;
            cursor: pointer;
            background: transparent;
            border: none;
            font-size: 15px;
            color: #666;
            transition: all 0.2s;
        }

        .tab.active {
            background: white;
            color: #667eea;
            font-weight: 600;
            border-bottom: 3px solid #667eea;
        }

        .content {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }

        .tab-panel {
            display: none;
        }

        .tab-panel.active {
            display: block;
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }

        select, textarea, input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }

        textarea {
            min-height: 100px;
            resize: vertical;
        }

        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .results {
            margin-top: 20px;
        }

        .result-card {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .result-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            font-size: 15px;
        }

        .result-value {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }

        .risk-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .risk-low { background: #d4edda; color: #155724; }
        .risk-medium { background: #fff3cd; color: #856404; }
        .risk-high { background: #f8d7da; color: #721c24; }
        .risk-critical { background: #f5c6cb; color: #491217; }

        details {
            margin-top: 16px;
            background: #f5f5f5;
            border-radius: 8px;
            padding: 12px;
        }

        summary {
            cursor: pointer;
            font-weight: 600;
            color: #667eea;
            user-select: none;
        }

        pre {
            margin-top: 12px;
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin-top: 12px;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #667eea;
        }

        ul {
            margin-left: 20px;
            margin-top: 8px;
        }

        li {
            margin-bottom: 6px;
            line-height: 1.5;
        }

        audio {
            width: 100%;
            margin-top: 12px;
        }

        .context-grid {
            display: grid;
            gap: 12px;
            margin-top: 12px;
        }

        .context-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid #667eea;
        }

        .context-label {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .context-value {
            font-size: 14px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="phone-frame">
        <div class="header">Leading Light</div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('demo')">Demo</button>
            <button class="tab" onclick="switchTab('evaluate')">Evaluate</button>
            <button class="tab" onclick="switchTab('voice')">Voice</button>
        </div>

        <div class="content">
            <!-- Demo Tab -->
            <div id="demo-panel" class="tab-panel active">
                <div class="form-group">
                    <label>Demo Case</label>
                    <select id="demo-case">
                        <option value="stable">Stable</option>
                        <option value="loaded">Loaded</option>
                        <option value="tense">Tense</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
                <button onclick="loadDemo()">Load Demo Bundle</button>
                <div id="demo-results"></div>
            </div>

            <!-- Evaluate Tab -->
            <div id="evaluate-panel" class="tab-panel">
                <div class="form-group">
                    <label>Bet Text</label>
                    <textarea id="bet-text" placeholder="Enter bet text (e.g., Chiefs -3.5)">Chiefs -3.5</textarea>
                </div>
                <div class="form-group">
                    <label>Plan Tier</label>
                    <select id="plan">
                        <option value="free">Free</option>
                        <option value="good">Good</option>
                        <option value="better">Better</option>
                        <option value="best">Best</option>
                    </select>
                </div>
                <button onclick="evaluateBet()">Evaluate</button>
                <div id="evaluate-results"></div>
            </div>

            <!-- Voice Tab -->
            <div id="voice-panel" class="tab-panel">
                <div class="form-group">
                    <label>Demo Case</label>
                    <select id="voice-case">
                        <option value="stable">Stable</option>
                        <option value="loaded">Loaded</option>
                        <option value="tense">Tense</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
                <button onclick="playVoice()">Play Voice Narration</button>
                <div id="voice-results"></div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');

            // Update panels
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.getElementById(tabName + '-panel').classList.add('active');
        }

        async function loadDemo() {
            const caseName = document.getElementById('demo-case').value;
            const resultsDiv = document.getElementById('demo-results');

            resultsDiv.innerHTML = '<div class="loading">Loading...</div>';

            try {
                const response = await fetch(`/demo/onboarding-bundle?case_name=${caseName}`);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail?.detail || 'Failed to load demo');
                }

                const selected = data.selected;

                resultsDiv.innerHTML = `
                    <div class="results">
                        <div class="result-card">
                            <div class="result-title">${selected.title}</div>
                            <div class="result-value">${selected.narration}</div>
                        </div>

                        <div class="result-card">
                            <div class="result-title">Context</div>
                            <div class="context-grid">
                                <div class="context-item">
                                    <div class="context-label">Who it's for</div>
                                    <div class="context-value">${selected.context.who_its_for}</div>
                                </div>
                                <div class="context-item">
                                    <div class="context-label">Why this case</div>
                                    <div class="context-value">${selected.context.why_this_case}</div>
                                </div>
                                <div class="context-item">
                                    <div class="context-label">What to notice</div>
                                    <div class="context-value">${selected.context.what_to_notice}</div>
                                </div>
                            </div>
                        </div>

                        <div class="result-card">
                            <div class="result-title">Plain English</div>
                            <ul>
                                ${selected.plain_english.map(text => `<li>${text}</li>`).join('')}
                            </ul>
                        </div>

                        <details>
                            <summary>View Full JSON</summary>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        </details>
                    </div>
                `;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }

        async function evaluateBet() {
            const betText = document.getElementById('bet-text').value;
            const plan = document.getElementById('plan').value;
            const resultsDiv = document.getElementById('evaluate-results');

            resultsDiv.innerHTML = '<div class="loading">Evaluating...</div>';

            try {
                const response = await fetch('/leading-light/evaluate/text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bet_text: betText, plan: plan })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail?.detail || 'Evaluation failed');
                }

                const riskClass = `risk-${data.evaluation.inductor.level}`;
                const interpretation = data.interpretation.fragility;

                resultsDiv.innerHTML = `
                    <div class="results">
                        <div class="result-card">
                            <div class="result-title">Risk Level</div>
                            <div class="result-value">
                                <span class="risk-badge ${riskClass}">${data.evaluation.inductor.level}</span>
                                <p style="margin-top: 8px;">${data.evaluation.inductor.explanation}</p>
                            </div>
                        </div>

                        <div class="result-card">
                            <div class="result-title">Fragility Score</div>
                            <div class="result-value">
                                ${data.evaluation.metrics.final_fragility.toFixed(2)} / 100
                                <p style="margin-top: 8px;"><strong>${interpretation.bucket.toUpperCase()}:</strong> ${interpretation.meaning}</p>
                                <p style="margin-top: 4px; font-style: italic;">${interpretation.what_to_do}</p>
                            </div>
                        </div>

                        <div class="result-card">
                            <div class="result-title">Recommendation</div>
                            <div class="result-value">
                                <strong>${data.evaluation.recommendation.action.toUpperCase()}</strong>
                                <p style="margin-top: 8px;">${data.evaluation.recommendation.reason}</p>
                            </div>
                        </div>

                        <div class="result-card">
                            <div class="result-title">Summary</div>
                            <ul>
                                ${data.explain.summary.map(text => `<li>${text}</li>`).join('')}
                            </ul>
                        </div>

                        <details>
                            <summary>View Full JSON</summary>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        </details>
                    </div>
                `;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }

        async function playVoice() {
            const caseName = document.getElementById('voice-case').value;
            const resultsDiv = document.getElementById('voice-results');

            resultsDiv.innerHTML = '<div class="loading">Loading audio...</div>';

            try {
                const audioUrl = `/leading-light/demo/${caseName}/narration?plan=best`;

                resultsDiv.innerHTML = `
                    <div class="results">
                        <div class="result-card">
                            <div class="result-title">${caseName.charAt(0).toUpperCase() + caseName.slice(1)} Demo Narration</div>
                            <audio controls src="${audioUrl}">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                        <div class="result-card">
                            <div class="result-title">Direct Link</div>
                            <div class="result-value">
                                <a href="${audioUrl}" target="_blank" style="color: #667eea;">Open in new tab</a>
                            </div>
                        </div>
                    </div>
                `;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
