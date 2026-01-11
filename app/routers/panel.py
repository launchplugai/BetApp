# app/routers/panel.py
"""
Developer Panel UI Router.

Provides a clean prototype interface for testing Leading Light endpoints.
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
    <title>Leading Light - Test Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 16px;
        }

        .container {
            max-width: 640px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .header {
            background: #1a1a1a;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-title {
            font-size: 20px;
            font-weight: 600;
        }

        .header-subtitle {
            font-size: 12px;
            color: #999;
            margin-top: 2px;
        }

        .copy-link-btn {
            background: #333;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
        }

        .copy-link-btn:hover {
            background: #444;
        }

        .tabs {
            display: flex;
            background: #fafafa;
            border-bottom: 1px solid #e0e0e0;
        }

        .tab {
            flex: 1;
            padding: 14px;
            text-align: center;
            cursor: pointer;
            background: transparent;
            border: none;
            font-size: 14px;
            color: #666;
            font-weight: 500;
            border-bottom: 2px solid transparent;
        }

        .tab.active {
            color: #1a1a1a;
            border-bottom-color: #1a1a1a;
            background: white;
        }

        .content {
            padding: 20px;
        }

        .tab-panel {
            display: none;
        }

        .tab-panel.active {
            display: block;
        }

        .card {
            background: #fafafa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
        }

        .card-title {
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 12px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .card-content {
            color: #333;
            font-size: 14px;
            line-height: 1.6;
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-weight: 500;
            font-size: 13px;
        }

        select, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
            background: white;
        }

        textarea {
            min-height: 80px;
            resize: vertical;
        }

        button {
            width: 100%;
            padding: 12px;
            background: #1a1a1a;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }

        button:hover {
            background: #333;
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .preset-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }

        .chip {
            background: white;
            border: 1px solid #ddd;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            cursor: pointer;
            color: #666;
        }

        .chip:hover {
            border-color: #1a1a1a;
            color: #1a1a1a;
        }

        .verdict-card {
            background: #1a1a1a;
            color: white;
            border: none;
        }

        .verdict-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 12px;
        }

        .verdict-item {
            text-align: center;
        }

        .verdict-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #999;
            margin-bottom: 4px;
        }

        .verdict-value {
            font-size: 18px;
            font-weight: 600;
        }

        .risk-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .risk-low { background: #d4edda; color: #155724; }
        .risk-medium { background: #fff3cd; color: #856404; }
        .risk-high { background: #f8d7da; color: #721c24; }
        .risk-critical { background: #f5c6cb; color: #491217; }
        .risk-stable { background: #d4edda; color: #155724; }
        .risk-loaded { background: #fff3cd; color: #856404; }
        .risk-tense { background: #f8d7da; color: #721c24; }

        ul {
            margin-left: 20px;
            margin-top: 8px;
        }

        li {
            margin-bottom: 8px;
            line-height: 1.5;
        }

        details {
            margin-top: 16px;
            background: #fafafa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 12px;
        }

        summary {
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            color: #666;
            user-select: none;
        }

        pre {
            margin-top: 12px;
            background: #1a1a1a;
            color: #f8f8f2;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 11px;
            line-height: 1.5;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-top: 12px;
            font-size: 14px;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
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
            padding-bottom: 12px;
            border-bottom: 1px solid #e0e0e0;
        }

        .context-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }

        .context-label {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .context-value {
            font-size: 13px;
            color: #333;
        }

        .link-copied {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1a1a1a;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            font-size: 13px;
            opacity: 0;
            transition: opacity 0.3s;
        }

        .link-copied.show {
            opacity: 1;
        }

        .narration-text {
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            font-style: italic;
        }

        .action-link {
            color: #1a1a1a;
            text-decoration: none;
            font-weight: 500;
            font-size: 13px;
        }

        .action-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div class="header-title">Leading Light</div>
                <div class="header-subtitle">Test Panel</div>
            </div>
            <button class="copy-link-btn" onclick="copyLink()">Copy Link</button>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('evaluate')">Evaluate</button>
            <button class="tab" onclick="switchTab('demo')">Demo</button>
            <button class="tab" onclick="switchTab('voice')">Voice</button>
        </div>

        <div class="content">
            <!-- Evaluate Tab -->
            <div id="evaluate-panel" class="tab-panel active">
                <div class="card">
                    <div class="card-title">Input</div>
                    <div class="preset-chips">
                        <span class="chip" onclick="fillBet('Chiefs -3.5')">Chiefs -3.5</span>
                        <span class="chip" onclick="fillBet('Lakers ML + Under 220.5 + Mahomes over 250 yards')">3-leg parlay</span>
                        <span class="chip" onclick="fillBet('Kelce TD + Chiefs -3.5 + Mahomes 250+ + Under 48.5')">4-leg complex</span>
                    </div>
                    <div class="form-group">
                        <label>Bet Text</label>
                        <textarea id="bet-text" placeholder="Enter bet text">Chiefs -3.5</textarea>
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
                </div>
                <div id="evaluate-results"></div>
            </div>

            <!-- Demo Tab -->
            <div id="demo-panel" class="tab-panel">
                <div class="card">
                    <div class="form-group">
                        <label>Demo Case</label>
                        <select id="demo-case">
                            <option value="stable">Stable</option>
                            <option value="loaded">Loaded</option>
                            <option value="tense">Tense</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                    <button onclick="loadDemo()">Load Demo</button>
                </div>
                <div id="demo-results"></div>
            </div>

            <!-- Voice Tab -->
            <div id="voice-panel" class="tab-panel">
                <div class="card">
                    <div class="form-group">
                        <label>Demo Case</label>
                        <select id="voice-case">
                            <option value="stable">Stable</option>
                            <option value="loaded">Loaded</option>
                            <option value="tense">Tense</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                    <button onclick="loadVoice()">Load Voice</button>
                </div>
                <div id="voice-results"></div>
            </div>
        </div>
    </div>

    <div id="link-copied-toast" class="link-copied">Link copied!</div>

    <script>
        // Parse URL params on load
        window.addEventListener('DOMContentLoaded', function() {
            const params = new URLSearchParams(window.location.search);

            if (params.has('tab')) {
                switchTab(params.get('tab'), false);
            }

            if (params.has('bet_text')) {
                document.getElementById('bet-text').value = decodeURIComponent(params.get('bet_text'));
            }

            if (params.has('plan')) {
                document.getElementById('plan').value = params.get('plan');
            }

            if (params.has('case')) {
                const caseName = params.get('case');
                const activeTab = params.get('tab');
                if (activeTab === 'demo') {
                    document.getElementById('demo-case').value = caseName;
                } else if (activeTab === 'voice') {
                    document.getElementById('voice-case').value = caseName;
                }
            }
        });

        function switchTab(tabName, updateUrl = true) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event?.target?.classList.add('active') || document.querySelector(`button[onclick*="${tabName}"]`).classList.add('active');

            // Update panels
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.getElementById(tabName + '-panel').classList.add('active');

            // Update URL
            if (updateUrl) {
                const url = new URL(window.location);
                url.searchParams.set('tab', tabName);
                window.history.pushState({}, '', url);
            }
        }

        function fillBet(text) {
            document.getElementById('bet-text').value = text;
        }

        function copyLink() {
            const activeTab = document.querySelector('.tab.active').textContent.toLowerCase();
            const url = new URL(window.location.origin + '/panel');
            url.searchParams.set('tab', activeTab);

            if (activeTab === 'evaluate') {
                const betText = document.getElementById('bet-text').value;
                const plan = document.getElementById('plan').value;
                if (betText) url.searchParams.set('bet_text', betText);
                if (plan) url.searchParams.set('plan', plan);
            } else if (activeTab === 'demo') {
                const caseName = document.getElementById('demo-case').value;
                url.searchParams.set('case', caseName);
            } else if (activeTab === 'voice') {
                const caseName = document.getElementById('voice-case').value;
                url.searchParams.set('case', caseName);
            }

            navigator.clipboard.writeText(url.toString()).then(() => {
                const toast = document.getElementById('link-copied-toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            });
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
                const bucketClass = `risk-${data.interpretation.fragility.bucket}`;
                const interpretation = data.interpretation.fragility;

                resultsDiv.innerHTML = `
                    <div class="card verdict-card">
                        <div class="card-title" style="color: white;">Verdict</div>
                        <div class="verdict-grid">
                            <div class="verdict-item">
                                <div class="verdict-label">Risk Level</div>
                                <div class="verdict-value">${data.evaluation.inductor.level.toUpperCase()}</div>
                            </div>
                            <div class="verdict-item">
                                <div class="verdict-label">Fragility</div>
                                <div class="verdict-value">${data.evaluation.metrics.final_fragility.toFixed(1)}</div>
                            </div>
                        </div>
                        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #333;">
                            <div class="verdict-label">Bucket</div>
                            <div style="margin-top: 8px;">
                                <span class="${bucketClass} risk-badge">${interpretation.bucket}</span>
                            </div>
                            <div style="margin-top: 12px; font-size: 13px; color: #ccc;">
                                <strong>Recommendation:</strong> ${data.evaluation.recommendation.action.toUpperCase()}
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Why</div>
                        <div class="card-content">
                            <p><strong>${interpretation.meaning}</strong></p>
                            <ul>
                                ${data.explain.summary.map(text => `<li>${text}</li>`).join('')}
                            </ul>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">What To Do</div>
                        <div class="card-content">
                            <p><strong>${interpretation.what_to_do}</strong></p>
                            <p style="margin-top: 8px;">${data.evaluation.recommendation.reason}</p>
                        </div>
                    </div>

                    <details>
                        <summary>Raw JSON</summary>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </details>
                `;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
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
                    <div class="card">
                        <div class="card-title">${selected.title}</div>
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

                    <div class="card">
                        <div class="card-title">Plain English</div>
                        <div class="card-content">
                            <ul>
                                ${selected.plain_english.map(text => `<li>${text}</li>`).join('')}
                            </ul>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Glossary</div>
                        <div class="card-content">
                            ${selected.glossary.map(item =>
                                `<div style="margin-bottom: 12px;">
                                    <strong>${item.term}:</strong> ${item.meaning}
                                </div>`
                            ).join('')}
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Progression</div>
                        <div class="card-content">
                            <p style="font-size: 12px; color: #666; margin-bottom: 8px;">${data.progression.overview}</p>
                            ${data.progression.order.map(key =>
                                `<div style="margin-bottom: 6px; font-size: 13px;">
                                    <strong>${key}:</strong> ${data.progression.steps[key]}
                                </div>`
                            ).join('')}
                        </div>
                    </div>

                    <details>
                        <summary>Raw JSON</summary>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </details>
                `;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }

        async function loadVoice() {
            const caseName = document.getElementById('voice-case').value;
            const resultsDiv = document.getElementById('voice-results');

            resultsDiv.innerHTML = '<div class="loading">Loading...</div>';

            try {
                // Fetch narration text
                const textResponse = await fetch(`/leading-light/demo/${caseName}/narration-text`);
                const textData = await textResponse.json();

                if (!textResponse.ok) {
                    throw new Error(textData.detail?.detail || 'Failed to load narration');
                }

                const audioUrl = `/leading-light/demo/${caseName}/narration?plan=best`;

                resultsDiv.innerHTML = `
                    <div class="card">
                        <div class="card-title">${textData.title} - Narration</div>
                        <div class="card-content">
                            <p class="narration-text">"${textData.narration}"</p>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Audio Player</div>
                        <audio controls src="${audioUrl}">
                            Your browser does not support the audio element.
                        </audio>
                        <div style="margin-top: 12px;">
                            <a href="${audioUrl}" target="_blank" class="action-link">Open in new tab →</a>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Context</div>
                        <div class="card-content">
                            <p style="font-size: 13px; margin-bottom: 8px;"><strong>Meaning:</strong> ${textData.plain_english.join(' ')}</p>
                        </div>
                    </div>

                    <details>
                        <summary>Raw JSON</summary>
                        <pre>${JSON.stringify(textData, null, 2)}</pre>
                    </details>
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
