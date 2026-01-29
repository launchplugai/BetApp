# app/routers/panel.py
"""
Developer Panel UI Router.

Provides a guided core-loop experience with image import for testing Leading Light endpoints.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.build_info import get_short_commit_sha, get_environment, get_build_time_utc, is_commit_unknown

router = APIRouter(tags=["Panel"])


@router.get("/panel", response_class=HTMLResponse)
async def dev_panel():
    """Render developer testing panel UI with image import and glassmorphism."""
    # Build info for footer stamp
    build_commit = get_short_commit_sha()
    build_env = get_environment()
    build_time = get_build_time_utc()
    build_unknown = is_commit_unknown()
    stale_class = " stale" if build_unknown else ""
    footer_text = "Build unknown. Hard refresh (Ctrl+Shift+R)." if build_unknown else f"Build: {build_commit} &bull; {build_env} &bull; {build_time}"

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
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }

        .container {
            max-width: 420px;
            margin: 0 auto;
        }

        /* Glassmorphism Styles */
        .glass {
            background: rgba(20, 20, 24, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        .header {
            background: linear-gradient(135deg, rgba(26, 26, 26, 0.65), rgba(42, 42, 42, 0.65));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .header-title {
            font-size: 24px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }

        .header-subtitle {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }

        .status-pills {
            display: flex;
            gap: 8px;
            margin-top: 14px;
        }

        .status-pill {
            padding: 5px 11px;
            border-radius: 14px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-weight: 600;
            background: rgba(0, 0, 0, 0.3);
        }

        .status-enabled {
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.4);
        }

        .status-disabled {
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .card {
            background: rgba(20, 20, 24, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .card-title {
            font-size: 13px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .import-section {
            text-align: center;
            padding: 24px 16px;
        }

        .import-title {
            font-size: 15px;
            font-weight: 600;
            color: #aaa;
            margin-bottom: 16px;
        }

        .import-buttons {
            display: flex;
            gap: 12px;
            justify-content: center;
        }

        .btn-import {
            flex: 1;
            padding: 14px 20px;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.8) 0%, rgba(79, 70, 229, 0.8) 100%);
            color: white;
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-import:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
        }

        .slip-editor {
            background: rgba(10, 10, 10, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
        }

        .slip-line {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
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
            letter-spacing: 0.6px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        select {
            width: 100%;
            padding: 10px;
            background: rgba(10, 10, 10, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
        }

        select:focus {
            outline: none;
            border-color: rgba(99, 102, 241, 0.5);
        }

        .btn-primary {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, rgba(74, 158, 255, 0.9) 0%, rgba(53, 122, 189, 0.9) 100%);
            color: white;
            border: 1px solid rgba(74, 158, 255, 0.3);
            border-radius: 8px;
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(74, 158, 255, 0.4);
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
            background: linear-gradient(135deg, rgba(42, 42, 42, 0.7) 0%, rgba(26, 26, 26, 0.7) 100%);
            border: 1px solid rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(12px);
            padding: 24px;
            margin-bottom: 16px;
            border-radius: 12px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        }

        .verdict-title {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 2px;
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
            font-size: 26px;
            font-weight: 700;
            color: #fff;
        }

        .verdict-footer {
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .verdict-bucket {
            margin-bottom: 14px;
        }

        .verdict-recommendation {
            font-size: 13px;
            color: #aaa;
            line-height: 1.7;
        }

        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        .badge-low {
            background: rgba(52, 211, 153, 0.25);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.4);
        }

        .badge-medium {
            background: rgba(251, 191, 36, 0.25);
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.4);
        }

        .badge-high {
            background: rgba(251, 146, 60, 0.25);
            color: #fb923c;
            border: 1px solid rgba(251, 146, 60, 0.4);
        }

        .badge-critical {
            background: rgba(239, 68, 68, 0.25);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .badge-stable { background: rgba(52, 211, 153, 0.25); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.4); }
        .badge-loaded { background: rgba(251, 191, 36, 0.25); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.4); }
        .badge-tense { background: rgba(251, 146, 60, 0.25); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.4); }

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
            background: rgba(10, 10, 10, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            margin-top: 12px;
        }

        summary {
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            user-select: none;
            padding: 4px 0;
        }

        summary:hover {
            color: #aaa;
        }

        details[open] summary {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        pre {
            background: rgba(0, 0, 0, 0.6);
            color: #34d399;
            padding: 12px;
            border-radius: 6px;
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
            padding: 10px;
            background: rgba(20, 20, 20, 0.5);
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .metric-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 15px;
            color: #e0e0e0;
            font-weight: 600;
        }

        .error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #ef4444;
            padding: 16px;
            border-radius: 8px;
            margin-top: 12px;
            font-size: 13px;
        }

        .locked {
            background: rgba(120, 120, 120, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-left: 3px solid rgba(251, 191, 36, 0.6);
            padding: 16px;
            border-radius: 6px;
            font-size: 13px;
            color: #999;
        }

        .locked-icon {
            display: inline-block;
            margin-right: 8px;
            font-size: 14px;
        }

        .locked-title {
            font-weight: 600;
            color: #aaa;
            margin-bottom: 6px;
        }

        .locked-upgrade {
            font-size: 12px;
            color: #fbbf24;
            margin-top: 8px;
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
            background: rgba(20, 20, 24, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 16px;
            display: flex;
            gap: 8px;
            justify-content: center;
            box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.3);
        }

        .bottom-bar button {
            flex: 1;
            max-width: 120px;
            padding: 12px;
            background: rgba(42, 42, 42, 0.8);
            color: #e0e0e0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .bottom-bar button:hover {
            background: rgba(60, 60, 60, 0.9);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .bottom-bar button.primary {
            background: linear-gradient(135deg, rgba(74, 158, 255, 0.9) 0%, rgba(53, 122, 189, 0.9) 100%);
            border: 1px solid rgba(74, 158, 255, 0.3);
            color: white;
        }

        .bottom-bar button.primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(74, 158, 255, 0.4);
        }

        audio {
            width: 100%;
            margin-top: 12px;
        }

        .learn-more-section {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 2px solid rgba(255, 255, 255, 0.1);
        }

        .subsection {
            background: rgba(10, 10, 10, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
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
            background: rgba(42, 42, 42, 0.8);
            color: #e0e0e0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-secondary:hover {
            background: rgba(60, 60, 60, 0.9);
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
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
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

        .extracted-text {
            background: rgba(10, 10, 10, 0.4);
            border: 1px solid rgba(52, 211, 153, 0.3);
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 12px;
            color: #34d399;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
        }

        .file-info {
            background: rgba(30, 30, 30, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 10px 12px;
            margin-top: 12px;
            font-size: 12px;
            color: #999;
            font-family: 'Courier New', monospace;
        }

        .file-info.selected {
            border-color: rgba(59, 130, 246, 0.4);
            color: #60a5fa;
        }

        .file-info.error {
            border-color: rgba(239, 68, 68, 0.4);
            color: #ef4444;
        }

        .request-status {
            background: rgba(20, 20, 20, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            font-size: 13px;
        }

        .request-status.idle {
            border-color: rgba(100, 100, 100, 0.3);
            color: #888;
        }

        .request-status.loading {
            border-color: rgba(59, 130, 246, 0.4);
            color: #60a5fa;
        }

        .request-status.success {
            border-color: rgba(52, 211, 153, 0.4);
            color: #34d399;
        }

        .request-status.error {
            border-color: rgba(239, 68, 68, 0.4);
            color: #ef4444;
        }

        .status-header {
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(59, 130, 246, 0.3);
            border-top-color: #60a5fa;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .status-details {
            font-size: 11px;
            color: #666;
            margin-top: 6px;
            font-family: 'Courier New', monospace;
        }

        .error-detail {
            background: rgba(239, 68, 68, 0.1);
            border-left: 3px solid #ef4444;
            padding: 8px 12px;
            margin-top: 8px;
            border-radius: 4px;
            font-size: 12px;
            line-height: 1.5;
        }

        .inline-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #ef4444;
            padding: 10px 12px;
            border-radius: 6px;
            margin-top: 8px;
            font-size: 12px;
        }

        /* Build Footer Stamp */
        .build-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(10, 10, 10, 0.95);
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding: 8px 16px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            color: #666;
            text-align: center;
            z-index: 200;
        }
        .build-footer a {
            color: #666;
            text-decoration: none;
        }
        .build-footer a:hover {
            color: #888;
        }
        .build-footer.stale {
            color: #fbbf24;
        }
        .build-footer.stale a {
            color: #fbbf24;
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
                <span class="status-pill" style="background: rgba(100, 100, 100, 0.2); border-color: rgba(150, 150, 150, 0.3); cursor: default;">Build: {{BUILD_COMMIT}}</span>
            </div>
        </div>

        <!-- Step 1: Import Slip -->
        <div class="card" id="import-card">
            <div class="card-title">Step 1: Import Slip</div>
            <div class="import-section">
                <div class="import-title">Snap or upload your bet slip</div>
                <div class="import-buttons">
                    <button class="btn-import" onclick="document.getElementById('camera-input').click()">
                        📷 Take Photo
                    </button>
                    <button class="btn-import" onclick="document.getElementById('library-input').click()">
                        📁 Choose Photo
                    </button>
                </div>
                <input type="file" id="camera-input" accept="image/*" capture="environment" onchange="handleFileSelect(event)" style="display: none;">
                <input type="file" id="library-input" accept="image/*" onchange="handleFileSelect(event)" style="display: none;">
                <div id="file-info" class="file-info">No file selected</div>
                <div id="file-error"></div>
                <div style="margin-top: 16px; font-size: 11px; color: #666;">
                    Or skip and enter manually below
                </div>
            </div>
        </div>

        <!-- Step 2: Bet Slip Editor -->
        <div class="card">
            <div class="card-title">Step 2: Bet Slip</div>
            <div id="extracted-display"></div>
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
        </div>

        <!-- Step 3: Evaluate Button -->
        <button class="btn-primary" id="evaluate-btn" onclick="evaluateSlip()">Evaluate Slip</button>

        <!-- Results Area -->
        <div id="request-status-container"></div>
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

            // Set initial idle status
            setRequestStatus('idle', 'Waiting for input');

            // Add input listeners for leg count
            for (let i = 1; i <= 4; i++) {
                document.getElementById('leg' + i).addEventListener('input', updateLegCount);
            }

            // Restore plan from localStorage
            const savedPlan = localStorage.getItem('leadingLightTier');
            if (savedPlan && ['good', 'better', 'best'].includes(savedPlan)) {
                document.getElementById('plan').value = savedPlan;
            }

            // Save plan to localStorage on change
            document.getElementById('plan').addEventListener('change', function() {
                localStorage.setItem('leadingLightTier', this.value);
            });
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
                const value = document.getElementById('leg' + i).value.trim();
                if (value) count++;
            }
            document.getElementById('leg-count').textContent = count;
        }

        function collectSlipLegs() {
            const legs = [];
            for (let i = 1; i <= 4; i++) {
                const value = document.getElementById('leg' + i).value.trim();
                if (value) legs.push(value);
            }
            return legs;
        }

        // Request tracking state
        let currentRequest = null;

        function generateRequestId() {
            return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
        }

        function setRequestStatus(state, message, details = null) {
            const container = document.getElementById('request-status-container');
            if (!container) return;

            if (state === 'hidden') {
                container.innerHTML = '';
                return;
            }

            let statusClass = '';
            let icon = '';
            let spinnerHtml = '';

            switch (state) {
                case 'idle':
                    statusClass = 'idle';
                    icon = '⏸';
                    break;
                case 'loading':
                    statusClass = 'loading';
                    icon = '⏳';
                    spinnerHtml = '<span class="spinner"></span>';
                    break;
                case 'success':
                    statusClass = 'success';
                    icon = '✓';
                    break;
                case 'error':
                    statusClass = 'error';
                    icon = '✗';
                    break;
            }

            let html = '<div class="request-status ' + statusClass + '">';
            html += '<div class="status-header">';
            html += icon + ' ' + message;
            if (spinnerHtml) html += spinnerHtml;
            html += '</div>';

            if (details) {
                html += '<div class="status-details">' + details + '</div>';
            }

            if (currentRequest && state === 'error') {
                html += '<div class="error-detail">';
                if (currentRequest.httpStatus) {
                    html += '<strong>HTTP ' + currentRequest.httpStatus + '</strong><br>';
                }
                if (currentRequest.errorDetail) {
                    html += currentRequest.errorDetail;
                }
                html += '</div>';
            }

            html += '</div>';
            container.innerHTML = html;
        }

        function validateFile(file) {
            const MAX_SIZE_MB = 5;
            const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

            // Check file type
            if (!file.type.startsWith('image/')) {
                return {
                    valid: false,
                    error: "That file isn't an image. Upload a screenshot/photo of the bet slip."
                };
            }

            // Check file size
            if (file.size > MAX_SIZE_BYTES) {
                return {
                    valid: false,
                    error: 'File too large. Max ' + MAX_SIZE_MB + ' MB.'
                };
            }

            return { valid: true };
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            const fileInfo = document.getElementById('file-info');
            const fileError = document.getElementById('file-error');

            if (!file) {
                fileInfo.textContent = 'No file selected';
                fileInfo.className = 'file-info';
                fileError.innerHTML = '';
                return;
            }

            // Update file info display
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            fileInfo.textContent = 'Selected: ' + file.name + ' | ' + file.type + ' | ' + sizeMB + ' MB';
            fileInfo.className = 'file-info selected';

            // Validate file
            const validation = validateFile(file);
            if (!validation.valid) {
                fileInfo.className = 'file-info error';
                fileError.innerHTML = '<div class="inline-error">' + validation.error + '</div>';
                return;
            }

            fileError.innerHTML = '';

            // Proceed to upload
            handleImageUpload(file);
        }

        async function handleImageUpload(file) {
            const resultsArea = document.getElementById('results-area');
            const extractedDisplay = document.getElementById('extracted-display');
            const evaluateBtn = document.getElementById('evaluate-btn');

            // Initialize request tracking
            const requestId = generateRequestId();
            const startedAt = new Date().toISOString();

            currentRequest = {
                id: requestId,
                endpoint: '/leading-light/evaluate/image',
                startedAt: startedAt,
                finishedAt: null,
                httpStatus: null,
                errorDetail: null
            };

            // Clear previous results
            resultsArea.innerHTML = '';
            extractedDisplay.innerHTML = '';

            // Set loading state
            setRequestStatus('loading', 'Uploading image...', 'Request ID: ' + requestId + ' | Started: ' + new Date(startedAt).toLocaleTimeString());

            // Disable evaluate button during upload
            if (evaluateBtn) evaluateBtn.disabled = true;

            try {
                const formData = new FormData();
                formData.append('image', file);
                formData.append('plan', document.getElementById('plan').value);

                const response = await fetch('/leading-light/evaluate/image', {
                    method: 'POST',
                    body: formData
                });

                const finishedAt = new Date().toISOString();
                currentRequest.finishedAt = finishedAt;
                currentRequest.httpStatus = response.status;

                // Handle non-OK responses
                if (!response.ok) {
                    let errorText = '';
                    try {
                        const data = await response.json();
                        // User-friendly error messages based on error code
                        if (data.detail?.code === 'FILE_TOO_LARGE') {
                            errorText = 'Image is too large. Please use an image under 5MB.';
                        } else if (data.detail?.code === 'INVALID_FILE_TYPE') {
                            errorText = 'Please upload an image file (JPG, PNG, etc.)';
                        } else if (data.detail?.code === 'RATE_LIMITED') {
                            errorText = 'Too many uploads. Please wait a few minutes and try again.';
                        } else if (data.detail?.code === 'NOT_A_BET_SLIP') {
                            errorText = 'This doesn\'t look like a bet slip. Try a different image.';
                        } else if (data.detail?.code === 'IMAGE_PARSE_NOT_CONFIGURED') {
                            errorText = 'Image parsing is not available right now. Try entering your bet manually.';
                        } else {
                            errorText = data.detail?.detail || JSON.stringify(data);
                        }
                        currentRequest.errorDetail = errorText;
                    } catch (e) {
                        // Failed to parse JSON error response
                        errorText = await response.text();
                        currentRequest.errorDetail = errorText;
                    }

                    setRequestStatus('error', 'Request failed', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());
                    return;
                }

                // Parse successful response
                const data = await response.json();

                // Show extracted text
                extractedDisplay.innerHTML = '<div class="extracted-text">✓ Extracted: ' + data.input.extracted_bet_text + '</div>';

                // Populate slip editor with extracted legs
                const legs = data.input.extracted_bet_text.split('\\n').filter(l => l.trim());
                for (let i = 0; i < 4; i++) {
                    const input = document.getElementById('leg' + (i + 1));
                    input.value = legs[i] || '';
                }
                updateLegCount();

                // Render results immediately (image endpoint does full evaluation)
                renderResults(data);

                // Set success state
                setRequestStatus('success', 'Analysis complete', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());

            } catch (error) {
                // Network error or other exception
                const finishedAt = new Date().toISOString();
                currentRequest.finishedAt = finishedAt;
                currentRequest.errorDetail = 'Network error: ' + error.message;

                setRequestStatus('error', 'Request failed', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());

            } finally {
                // Re-enable evaluate button
                if (evaluateBtn) evaluateBtn.disabled = false;
            }
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
            const extractedDisplay = document.getElementById('extracted-display');
            const evaluateBtn = document.getElementById('evaluate-btn');

            // Initialize request tracking
            const requestId = generateRequestId();
            const startedAt = new Date().toISOString();

            currentRequest = {
                id: requestId,
                endpoint: '/leading-light/evaluate/text',
                startedAt: startedAt,
                finishedAt: null,
                httpStatus: null,
                errorDetail: null
            };

            // Clear previous results
            resultsArea.innerHTML = '';
            extractedDisplay.innerHTML = '';

            // Set loading state
            setRequestStatus('loading', 'Evaluating slip...', 'Request ID: ' + requestId + ' | Started: ' + new Date(startedAt).toLocaleTimeString());

            // Disable evaluate button during request
            if (evaluateBtn) evaluateBtn.disabled = true;

            try {
                const response = await fetch('/leading-light/evaluate/text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bet_text: betText, plan: plan })
                });

                const finishedAt = new Date().toISOString();
                currentRequest.finishedAt = finishedAt;
                currentRequest.httpStatus = response.status;

                // Handle non-OK responses
                if (!response.ok) {
                    let errorText = '';
                    try {
                        const data = await response.json();
                        errorText = data.detail?.detail || JSON.stringify(data);
                        currentRequest.errorDetail = errorText;
                    } catch (e) {
                        // Failed to parse JSON error response
                        errorText = await response.text();
                        currentRequest.errorDetail = errorText;
                    }

                    setRequestStatus('error', 'Request failed', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());
                    return;
                }

                // Parse successful response
                const data = await response.json();

                // Render results
                renderResults(data);

                // Set success state
                setRequestStatus('success', 'Analysis complete', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());

            } catch (error) {
                // Network error or other exception
                const finishedAt = new Date().toISOString();
                currentRequest.finishedAt = finishedAt;
                currentRequest.errorDetail = 'Network error: ' + error.message;

                setRequestStatus('error', 'Request failed', 'Request ID: ' + requestId + ' | Finished: ' + new Date(finishedAt).toLocaleTimeString());

            } finally {
                // Re-enable evaluate button
                if (evaluateBtn) evaluateBtn.disabled = false;
            }
        }

        function renderResults(data) {
            const interpretation = data.interpretation.fragility;
            const evaluation = data.evaluation;
            const explain = data.explain || {};

            const bucketClass = 'badge-' + interpretation.bucket;

            // Check if explain is empty (GOOD plan)
            const isExplainEmpty = Object.keys(explain).length === 0;

            let summaryItems = '';
            if (explain.summary && explain.summary.length > 0) {
                for (let i = 0; i < explain.summary.length; i++) {
                    summaryItems += '<li>' + explain.summary[i] + '</li>';
                }
            }

            let correlationsList = '';
            if (evaluation.correlations.length > 0) {
                correlationsList = '<ul style="margin-top: 8px;">';
                for (let i = 0; i < evaluation.correlations.length; i++) {
                    const c = evaluation.correlations[i];
                    correlationsList += '<li><strong>' + c.tag + ':</strong> ' + c.description + ' (Weight: ' + c.weight.toFixed(2) + ')</li>';
                }
                correlationsList += '</ul>';
            } else {
                correlationsList = '<p style="margin-top: 8px; color: #666;">No correlations detected</p>';
            }

            let nextStepHtml = '';
            if (explain.recommended_next_step) {
                nextStepHtml = '<p>' + explain.recommended_next_step + '</p>';
            }

            let html = '';
            html += '<!-- Verdict Card -->';
            html += '<div class="verdict-card">';
            html += '<div class="verdict-title">Verdict</div>';
            html += '<div class="verdict-grid">';
            html += '<div class="verdict-item">';
            html += '<div class="verdict-label">Risk Level</div>';
            html += '<div class="verdict-value">' + evaluation.inductor.level.toUpperCase() + '</div>';
            html += '</div>';
            html += '<div class="verdict-item">';
            html += '<div class="verdict-label">Fragility</div>';
            html += '<div class="verdict-value">' + evaluation.metrics.final_fragility.toFixed(1) + '</div>';
            html += '</div>';
            html += '</div>';
            html += '<div class="verdict-footer">';
            html += '<div class="verdict-bucket">';
            html += '<div class="verdict-label">Bucket</div>';
            html += '<div style="margin-top: 8px;">';
            html += '<span class="badge ' + bucketClass + '">' + interpretation.bucket + '</span>';
            html += '</div>';
            html += '</div>';
            html += '<div class="verdict-recommendation">';
            html += '<strong>Recommendation:</strong> ' + evaluation.recommendation.action.toUpperCase() + '<br>';
            html += evaluation.recommendation.reason;
            html += '</div>';
            html += '</div>';
            html += '</div>';

            html += '<!-- Explanation Card -->';
            html += '<div class="card">';
            html += '<div class="card-title">Explanation</div>';
            html += '<div class="card-content">';
            html += '<p><strong>' + interpretation.meaning + '</strong></p>';

            // Check if summary is locked
            if (isExplainEmpty || !explain.summary || explain.summary.length === 0) {
                html += '<div class="locked">';
                html += '<div class="locked-icon">🔒</div>';
                html += '<div class="locked-title">Summary Locked</div>';
                html += '<div>Locked on this plan. Upgrade to Better to see the explanation.</div>';
                html += '<div class="locked-upgrade">Upgrade to Better for Summary. Upgrade to Best for Alerts + Next Step.</div>';
                html += '</div>';
            } else {
                html += '<ul>';
                html += summaryItems;
                html += '</ul>';
            }

            html += '</div>';
            html += '</div>';

            html += '<!-- Alerts Card -->';
            html += '<div class="card">';
            html += '<div class="card-title">Alerts</div>';
            html += '<div class="card-content">';

            // Check if alerts is locked or empty
            const plan = document.getElementById('plan').value;
            if (plan !== 'best') {
                // Non-BEST plans: show locked
                html += '<div class="locked">';
                html += '<div class="locked-icon">🔒</div>';
                html += '<div class="locked-title">Alerts Locked</div>';
                html += '<div>Locked on this plan. Upgrade to Best to see alerts.</div>';
                html += '<div class="locked-upgrade">Upgrade to Best for full analysis with alerts and next-step guidance.</div>';
                html += '</div>';
            } else if (!explain.alerts || explain.alerts.length === 0) {
                // BEST plan but no alerts: show empty state (not locked)
                html += '<p style="color: #666;">✅ No alerts detected for this slip.</p>';
            } else {
                // BEST plan with alerts: render list
                html += '<ul>';
                for (let i = 0; i < explain.alerts.length; i++) {
                    html += '<li>' + explain.alerts[i] + '</li>';
                }
                html += '</ul>';
            }

            html += '</div>';
            html += '</div>';

            html += '<!-- Next Steps Card -->';
            html += '<div class="card">';
            html += '<div class="card-title">Next Steps</div>';
            html += '<div class="card-content">';
            html += '<p><strong>' + interpretation.what_to_do + '</strong></p>';

            // Check if recommended_next_step is locked or missing
            if (plan !== 'best') {
                // Non-BEST plans: show locked
                html += '<div class="locked">';
                html += '<div class="locked-icon">🔒</div>';
                html += '<div class="locked-title">Next Step Guidance Locked</div>';
                html += '<div>Locked on this plan. Upgrade to Best for next-step guidance.</div>';
                html += '<div class="locked-upgrade">Upgrade to Best for personalized next-step recommendations.</div>';
                html += '</div>';
            } else if (!explain.recommended_next_step) {
                // BEST plan but no next step: show empty state (not locked)
                html += '<p style="color: #666;">No next-step guidance returned for this case.</p>';
            } else {
                // BEST plan with next step: render normally
                html += nextStepHtml;
            }

            html += '</div>';
            html += '</div>';

            html += '<!-- Details Drawer -->';
            html += '<details>';
            html += '<summary>Metrics</summary>';
            html += '<div class="metric-grid">';
            html += '<div class="metric-item">';
            html += '<div class="metric-label">Raw Fragility</div>';
            html += '<div class="metric-value">' + evaluation.metrics.raw_fragility.toFixed(1) + '</div>';
            html += '</div>';
            html += '<div class="metric-item">';
            html += '<div class="metric-label">Leg Penalty</div>';
            html += '<div class="metric-value">' + evaluation.metrics.leg_penalty.toFixed(1) + '</div>';
            html += '</div>';
            html += '<div class="metric-item">';
            html += '<div class="metric-label">Correlation Penalty</div>';
            html += '<div class="metric-value">' + evaluation.metrics.correlation_penalty.toFixed(1) + '</div>';
            html += '</div>';
            html += '<div class="metric-item">';
            html += '<div class="metric-label">Multiplier</div>';
            html += '<div class="metric-value">' + evaluation.metrics.multiplier.toFixed(2) + 'x</div>';
            html += '</div>';
            html += '</div>';
            html += '</details>';

            html += '<details>';
            html += '<summary>Correlations</summary>';
            html += correlationsList;
            html += '</details>';

            html += '<details>';
            html += '<summary>Raw JSON</summary>';
            html += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            html += '</details>';

            document.getElementById('results-area').innerHTML = html;
        }

        function clearResults() {
            document.getElementById('results-area').innerHTML = '';
            document.getElementById('extracted-display').innerHTML = '';
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
            const plan = document.getElementById('plan').value;
            const caseName = document.getElementById('voice-case').value;
            const playerDiv = document.getElementById('narration-player');

            // Check if voice is locked (non-BEST plans)
            if (plan !== 'best') {
                playerDiv.innerHTML = '<div class="locked">' +
                    '<div class="locked-icon">🔒</div>' +
                    '<div class="locked-title">Voice Narration Locked</div>' +
                    '<div>Voice narration is only available on the Best plan.</div>' +
                    '<div class="locked-upgrade">Upgrade to Best to unlock voice-powered demos and narration.</div>' +
                    '</div>';
                return;
            }

            playerDiv.innerHTML = '<div class="loading">Loading narration</div>';

            try {
                const textResponse = await fetch('/leading-light/demo/' + caseName + '/narration-text');
                const textData = await textResponse.json();

                if (!textResponse.ok) {
                    throw new Error(textData.detail?.detail || 'Failed to load narration');
                }

                const audioUrl = '/leading-light/demo/' + caseName + '/narration?plan=best';

                let playerHtml = '';
                playerHtml += '<div class="demo-content">';
                playerHtml += '<p style="font-style: italic; color: #aaa; margin-bottom: 12px;">"' + textData.narration + '"</p>';
                playerHtml += '<audio controls src="' + audioUrl + '">';
                playerHtml += 'Your browser does not support the audio element.';
                playerHtml += '</audio>';
                playerHtml += '</div>';
                playerDiv.innerHTML = playerHtml;
            } catch (error) {
                playerDiv.innerHTML = '<div class="error">' + error.message + '</div>';
            }
        }

        async function loadDemo() {
            const caseName = document.getElementById('demo-case').value;
            const contentDiv = document.getElementById('demo-content');

            contentDiv.innerHTML = '<div class="loading">Loading demo notes</div>';

            try {
                const response = await fetch('/demo/onboarding-bundle?case_name=' + caseName);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail?.detail || 'Failed to load demo');
                }

                const selected = data.selected;

                let keyPoints = '';
                for (let i = 0; i < selected.plain_english.length; i++) {
                    keyPoints += '<li>' + selected.plain_english[i] + '</li>';
                }

                let demoHtml = '';
                demoHtml += '<div class="demo-content">';
                demoHtml += '<div class="demo-title">Example: ' + selected.title + '</div>';
                demoHtml += '<div class="context-item">';
                demoHtml += '<div class="context-label">Who it\'s for</div>';
                demoHtml += '<div class="context-value">' + selected.context.who_its_for + '</div>';
                demoHtml += '</div>';
                demoHtml += '<div class="context-item">';
                demoHtml += '<div class="context-label">Why this case</div>';
                demoHtml += '<div class="context-value">' + selected.context.why_this_case + '</div>';
                demoHtml += '</div>';
                demoHtml += '<div class="context-item">';
                demoHtml += '<div class="context-label">What to notice</div>';
                demoHtml += '<div class="context-value">' + selected.context.what_to_notice + '</div>';
                demoHtml += '</div>';
                demoHtml += '<div style="margin-top: 16px;">';
                demoHtml += '<div class="subsection-title" style="margin-bottom: 8px;">Key Points</div>';
                demoHtml += '<ul>';
                demoHtml += keyPoints;
                demoHtml += '</ul>';
                demoHtml += '</div>';
                demoHtml += '<details style="margin-top: 12px;">';
                demoHtml += '<summary>Raw JSON</summary>';
                demoHtml += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                demoHtml += '</details>';
                demoHtml += '</div>';
                contentDiv.innerHTML = demoHtml;
            } catch (error) {
                contentDiv.innerHTML = '<div class="error">' + error.message + '</div>';
            }
        }
    </script>

    <!-- Build Footer Stamp -->
    <div class="build-footer{{STALE_CLASS}}">
        <a href="/build" target="_blank">{{FOOTER_TEXT}}</a>
    </div>
</body>
</html>
    """
    # Replace placeholders with dynamic values
    html_content = html_content.replace("{{BUILD_COMMIT}}", build_commit)
    html_content = html_content.replace("{{STALE_CLASS}}", stale_class)
    html_content = html_content.replace("{{FOOTER_TEXT}}", footer_text)
    return HTMLResponse(content=html_content)
