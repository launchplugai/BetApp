# app/routers/panel.py
"""
Developer Panel UI Router.

Provides a guided core-loop experience for testing Leading Light endpoints.
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
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }

        .container {
            max-width: 420px;
            margin: 0 auto;
        }

        .header {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #333;
        }

        .header-title {
            font-size: 22px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 4px;
        }

        .header-subtitle {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .status-pills {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }

        .status-pill {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .status-enabled {
            background: rgba(52, 211, 153, 0.2);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.3);
        }

        .status-disabled {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #2a2a2a;
        }

        .slip-editor {
            background: #0f0f0f;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 12px;
        }

        .slip-line {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid #1a1a1a;
        }

        .slip-line:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }

        .slip-line-number {
            font-size: 11px;
            color: #555;
            margin-right: 12px;
            min-width: 20px;
            font-family: 'Courier New', monospace;
        }

        .slip-line input {
            flex: 1;
            background: transparent;
            border: none;
            color: #e0e0e0;
            font-size: 14px;
            font-family: 'Courier New', monospace;
            outline: none;
        }

        .slip-line input::placeholder {
            color: #555;
        }

        .slip-helper {
            font-size: 11px;
            color: #666;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .legs-count {
            color: #888;
            font-weight: 600;
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        select {
            width: 100%;
            padding: 10px;
            background: #0f0f0f;
            border: 1px solid #333;
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
        }

        select:focus {
            outline: none;
            border-color: #4a9eff;
        }

        .btn-primary {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(74, 158, 255, 0.3);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .verdict-card {
            background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
            border: 1px solid #3a3a3a;
            padding: 24px;
            margin-bottom: 16px;
            border-radius: 8px;
        }

        .verdict-title {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }

        .verdict-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .verdict-item {
            text-align: center;
        }

        .verdict-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .verdict-value {
            font-size: 24px;
            font-weight: 700;
            color: #fff;
        }

        .verdict-footer {
            padding-top: 20px;
            border-top: 1px solid #2a2a2a;
        }

        .verdict-bucket {
            margin-bottom: 12px;
        }

        .verdict-recommendation {
            font-size: 13px;
            color: #aaa;
            line-height: 1.6;
        }

        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-low {
            background: rgba(52, 211, 153, 0.2);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.3);
        }

        .badge-medium {
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.3);
        }

        .badge-high {
            background: rgba(251, 146, 60, 0.2);
            color: #fb923c;
            border: 1px solid rgba(251, 146, 60, 0.3);
        }

        .badge-critical {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-stable { background: rgba(52, 211, 153, 0.2); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
        .badge-loaded { background: rgba(251, 191, 36, 0.2); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }
        .badge-tense { background: rgba(251, 146, 60, 0.2); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.3); }

        .card-content {
            color: #aaa;
            font-size: 14px;
            line-height: 1.7;
        }

        .card-content p {
            margin-bottom: 12px;
        }

        .card-content strong {
            color: #e0e0e0;
        }

        ul {
            margin-left: 20px;
            margin-top: 8px;
        }

        li {
            margin-bottom: 8px;
            color: #aaa;
            line-height: 1.6;
        }

        details {
            background: #0f0f0f;
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 12px;
            margin-top: 12px;
        }

        summary {
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            user-select: none;
            padding: 4px 0;
        }

        summary:hover {
            color: #aaa;
        }

        details[open] summary {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1a1a1a;
        }

        pre {
            background: #000;
            color: #34d399;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 11px;
            line-height: 1.5;
            font-family: 'Courier New', monospace;
            margin-top: 8px;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 8px;
        }

        .metric-item {
            padding: 8px;
            background: #1a1a1a;
            border-radius: 4px;
        }

        .metric-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 14px;
            color: #e0e0e0;
            font-weight: 600;
        }

        .error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            padding: 16px;
            border-radius: 6px;
            margin-top: 12px;
            font-size: 13px;
        }

        .loading {
            text-align: center;
            padding: 40px 20px;
            color: #666;
            font-size: 13px;
        }

        .loading::after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        .bottom-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #1a1a1a;
            border-top: 1px solid #2a2a2a;
            padding: 12px 16px;
            display: flex;
            gap: 8px;
            justify-content: center;
        }

        .bottom-bar button {
            flex: 1;
            max-width: 120px;
            padding: 12px;
            background: #2a2a2a;
            color: #e0e0e0;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .bottom-bar button:hover {
            background: #3a3a3a;
            border-color: #4a4a4a;
        }

        .bottom-bar button.primary {
            background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
            border: none;
            color: white;
        }

        .bottom-bar button.primary:hover {
            transform: translateY(-1px);
        }

        audio {
            width: 100%;
            margin-top: 12px;
        }

        .learn-more-section {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 2px solid #2a2a2a;
        }

        .subsection {
            background: #0f0f0f;
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .subsection-title {
            font-size: 12px;
            font-weight: 700;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        .btn-secondary {
            width: 100%;
            padding: 10px;
            background: #2a2a2a;
            color: #e0e0e0;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-secondary:hover {
            background: #3a3a3a;
        }

        .demo-content {
            margin-top: 12px;
        }

        .demo-title {
            font-size: 14px;
            font-weight: 600;
            color: #e0e0e0;
            margin-bottom: 12px;
        }

        .context-item {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1a1a1a;
        }

        .context-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }

        .context-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .context-value {
            font-size: 13px;
            color: #aaa;
        }

        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header with Status -->
        <div class="header">
            <div class="header-title">Leading Light</div>
            <div class="header-subtitle">Live Test Panel</div>
            <div class="status-pills">
                <span id="voice-status" class="status-pill">Voice: Loading...</span>
                <span id="leading-light-status" class="status-pill">Leading Light: Loading...</span>
            </div>
        </div>

        <!-- Bet Slip Card -->
        <div class="card">
            <div class="card-title">Bet Slip</div>
            <div class="slip-editor">
                <div class="slip-line">
                    <span class="slip-line-number">1.</span>
                    <input type="text" id="leg1" placeholder="Chiefs -3.5" value="Chiefs -3.5">
                </div>
                <div class="slip-line">
                    <span class="slip-line-number">2.</span>
                    <input type="text" id="leg2" placeholder="Lakers ML">
                </div>
                <div class="slip-line">
                    <span class="slip-line-number">3.</span>
                    <input type="text" id="leg3" placeholder="Over 220.5">
                </div>
                <div class="slip-line">
                    <span class="slip-line-number">4.</span>
                    <input type="text" id="leg4" placeholder="Mahomes 250+ yards">
                </div>
            </div>
            <div class="slip-helper">
                <span>Tip: one line per leg</span>
                <span class="legs-count"><span id="leg-count">1</span> legs detected</span>
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
            <button class="btn-primary" onclick="evaluateSlip()">Evaluate Slip</button>
        </div>

        <!-- Results Area -->
        <div id="results-area"></div>

        <!-- Learn More Section (collapsed by default) -->
        <details class="learn-more-section" id="learn-more">
            <summary>Learn More</summary>

            <!-- Voice Narration Subsection -->
            <div class="subsection">
                <div class="subsection-title">Voice Narration</div>
                <div class="form-group">
                    <label>Demo Case</label>
                    <select id="voice-case">
                        <option value="stable">Stable</option>
                        <option value="loaded">Loaded</option>
                        <option value="tense">Tense</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
                <button class="btn-secondary" onclick="playNarration()">Play Narration</button>
                <div id="narration-player"></div>
            </div>

            <!-- Demo Notes Subsection -->
            <div class="subsection">
                <div class="subsection-title">Demo Notes</div>
                <div class="form-group">
                    <label>Demo Case</label>
                    <select id="demo-case">
                        <option value="stable">Stable</option>
                        <option value="loaded">Loaded</option>
                        <option value="tense">Tense</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
                <button class="btn-secondary" onclick="loadDemo()">Load Demo Notes</button>
                <div id="demo-content"></div>
            </div>
        </details>
    </div>

    <!-- Bottom Sticky Bar -->
    <div class="bottom-bar">
        <button class="primary" onclick="evaluateSlip()">Evaluate</button>
        <button onclick="clearResults()">Clear</button>
        <button onclick="toggleLearnMore()">Learn More</button>
    </div>

    <script>
        // Load status on page load
        window.addEventListener('DOMContentLoaded', async function() {
            await loadStatus();
            updateLegCount();

            // Add input listeners for leg count
            for (let i = 1; i <= 4; i++) {
                document.getElementById(`leg${i}`).addEventListener('input', updateLegCount);
            }
        });

        async function loadStatus() {
            // Check Voice status
            try {
                const voiceResponse = await fetch('/voice/status');
                const voiceData = await voiceResponse.json();
                const voiceStatus = document.getElementById('voice-status');
                if (voiceData.enabled) {
                    voiceStatus.textContent = 'Voice: Enabled';
                    voiceStatus.className = 'status-pill status-enabled';
                } else {
                    voiceStatus.textContent = 'Voice: Disabled';
                    voiceStatus.className = 'status-pill status-disabled';
                }
            } catch (e) {
                document.getElementById('voice-status').textContent = 'Voice: Error';
                document.getElementById('voice-status').className = 'status-pill status-disabled';
            }

            // Check Leading Light status
            try {
                const llResponse = await fetch('/leading-light/status');
                const llData = await llResponse.json();
                const llStatus = document.getElementById('leading-light-status');
                if (llData.enabled) {
                    llStatus.textContent = 'Leading Light: Enabled';
                    llStatus.className = 'status-pill status-enabled';
                } else {
                    llStatus.textContent = 'Leading Light: Disabled';
                    llStatus.className = 'status-pill status-disabled';
                }
            } catch (e) {
                document.getElementById('leading-light-status').textContent = 'Leading Light: Error';
                document.getElementById('leading-light-status').className = 'status-pill status-disabled';
            }
        }

        function updateLegCount() {
            let count = 0;
            for (let i = 1; i <= 4; i++) {
                const value = document.getElementById(`leg${i}`).value.trim();
                if (value) count++;
            }
            document.getElementById('leg-count').textContent = count;
        }

        function collectSlipLegs() {
            const legs = [];
            for (let i = 1; i <= 4; i++) {
                const value = document.getElementById(`leg${i}`).value.trim();
                if (value) legs.push(value);
            }
            return legs;
        }

        async function evaluateSlip() {
            const legs = collectSlipLegs();
            if (legs.length === 0) {
                alert('Please enter at least one leg');
                return;
            }

            const betText = legs.join(' + ');
            const plan = document.getElementById('plan').value;
            const resultsArea = document.getElementById('results-area');

            resultsArea.innerHTML = '<div class="loading">Evaluating slip</div>';

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

                renderResults(data);
            } catch (error) {
                resultsArea.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }

        function renderResults(data) {
            const interpretation = data.interpretation.fragility;
            const evaluation = data.evaluation;
            const explain = data.explain;

            const bucketClass = `badge-${interpretation.bucket}`;
            const levelClass = `badge-${evaluation.inductor.level}`;

            let html = `
                <!-- Verdict Card -->
                <div class="verdict-card">
                    <div class="verdict-title">Verdict</div>
                    <div class="verdict-grid">
                        <div class="verdict-item">
                            <div class="verdict-label">Risk Level</div>
                            <div class="verdict-value">${evaluation.inductor.level.toUpperCase()}</div>
                        </div>
                        <div class="verdict-item">
                            <div class="verdict-label">Fragility</div>
                            <div class="verdict-value">${evaluation.metrics.final_fragility.toFixed(1)}</div>
                        </div>
                    </div>
                    <div class="verdict-footer">
                        <div class="verdict-bucket">
                            <div class="verdict-label">Bucket</div>
                            <div style="margin-top: 8px;">
                                <span class="badge ${bucketClass}">${interpretation.bucket}</span>
                            </div>
                        </div>
                        <div class="verdict-recommendation">
                            <strong>Recommendation:</strong> ${evaluation.recommendation.action.toUpperCase()}<br>
                            ${evaluation.recommendation.reason}
                        </div>
                    </div>
                </div>

                <!-- Explanation Card -->
                <div class="card">
                    <div class="card-title">Explanation</div>
                    <div class="card-content">
                        <p><strong>${interpretation.meaning}</strong></p>
                        <ul>
                            ${explain.summary.map(text => `<li>${text}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <!-- Next Steps Card -->
                <div class="card">
                    <div class="card-title">Next Steps</div>
                    <div class="card-content">
                        <p><strong>${interpretation.what_to_do}</strong></p>
                        ${explain.recommended_next_step ? `<p>${explain.recommended_next_step}</p>` : ''}
                    </div>
                </div>

                <!-- Details Drawer -->
                <details>
                    <summary>Metrics</summary>
                    <div class="metric-grid">
                        <div class="metric-item">
                            <div class="metric-label">Raw Fragility</div>
                            <div class="metric-value">${evaluation.metrics.raw_fragility.toFixed(1)}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Leg Penalty</div>
                            <div class="metric-value">${evaluation.metrics.leg_penalty.toFixed(1)}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Correlation Penalty</div>
                            <div class="metric-value">${evaluation.metrics.correlation_penalty.toFixed(1)}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Multiplier</div>
                            <div class="metric-value">${evaluation.metrics.multiplier.toFixed(2)}x</div>
                        </div>
                    </div>
                </details>

                <details>
                    <summary>Correlations</summary>
                    ${evaluation.correlations.length > 0
                        ? `<ul style="margin-top: 8px;">${evaluation.correlations.map(c =>
                            `<li><strong>${c.tag}:</strong> ${c.description} (Weight: ${c.weight.toFixed(2)})</li>`
                        ).join('')}</ul>`
                        : '<p style="margin-top: 8px; color: #666;">No correlations detected</p>'
                    }
                </details>

                <details>
                    <summary>Raw JSON</summary>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                </details>
            `;

            document.getElementById('results-area').innerHTML = html;
        }

        function clearResults() {
            document.getElementById('results-area').innerHTML = '';
            // Optionally clear slip
            // for (let i = 1; i <= 4; i++) {
            //     document.getElementById(`leg${i}`).value = '';
            // }
            // updateLegCount();
        }

        function toggleLearnMore() {
            const learnMore = document.getElementById('learn-more');
            if (learnMore.open) {
                learnMore.open = false;
            } else {
                learnMore.open = true;
                learnMore.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }

        async function playNarration() {
            const caseName = document.getElementById('voice-case').value;
            const playerDiv = document.getElementById('narration-player');

            playerDiv.innerHTML = '<div class="loading">Loading narration</div>';

            try {
                // Fetch narration text
                const textResponse = await fetch(`/leading-light/demo/${caseName}/narration-text`);
                const textData = await textResponse.json();

                if (!textResponse.ok) {
                    throw new Error(textData.detail?.detail || 'Failed to load narration');
                }

                const audioUrl = `/leading-light/demo/${caseName}/narration?plan=best`;

                playerDiv.innerHTML = `
                    <div class="demo-content">
                        <p style="font-style: italic; color: #aaa; margin-bottom: 12px;">"${textData.narration}"</p>
                        <audio controls src="${audioUrl}">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                `;
            } catch (error) {
                playerDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }

        async function loadDemo() {
            const caseName = document.getElementById('demo-case').value;
            const contentDiv = document.getElementById('demo-content');

            contentDiv.innerHTML = '<div class="loading">Loading demo notes</div>';

            try {
                const response = await fetch(`/demo/onboarding-bundle?case_name=${caseName}`);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail?.detail || 'Failed to load demo');
                }

                const selected = data.selected;

                contentDiv.innerHTML = `
                    <div class="demo-content">
                        <div class="demo-title">Example: ${selected.title}</div>

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

                        <div style="margin-top: 16px;">
                            <div class="subsection-title" style="margin-bottom: 8px;">Key Points</div>
                            <ul>
                                ${selected.plain_english.map(text => `<li>${text}</li>`).join('')}
                            </ul>
                        </div>

                        <details style="margin-top: 12px;">
                            <summary>Raw JSON</summary>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        </details>
                    </div>
                `;
            } catch (error) {
                contentDiv.innerHTML = `<div class="error">${error.message}</div>`;
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
