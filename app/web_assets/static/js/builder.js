// S16-B: Parlay Builder Logic
const API_BASE = '/api/mock';
let protocol = null;
let markets = null;
let legs = [];
let currentMarket = 'main';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadProtocol();
    await loadMarkets();
    renderGameHeader();
    renderMarket();
    renderLegs();
});

async function loadProtocol() {
    const stored = sessionStorage.getItem('dna_protocol_context');
    if (stored) {
        protocol = JSON.parse(stored);
        console.log('Protocol loaded:', protocol);
    } else {
        console.warn('No protocol in sessionStorage');
        // Fallback for testing
        protocol = {
            protocolId: 'test',
            league: 'NBA',
            gameId: 'nba_001',
            teams: ['Lakers', 'Warriors'],
            status: 'LIVE',
            clock: 'Q3 8:42',
            score: { home: 88, away: 82 }
        };
    }
}

async function loadMarkets() {
    if (!protocol) return;
    try {
        // Use the gameId from protocol, or fallback to nba_001
        const gameId = protocol.gameId.includes('_') ? protocol.gameId : 'nba_001';
        const response = await fetch(`${API_BASE}/odds/${gameId}`);
        const data = await response.json();
        markets = data.odds;
        console.log('Markets loaded:', markets);
    } catch (err) {
        console.error('Failed to load markets:', err);
    }
}

// League icon mapping — correct sport icon per league
const LEAGUE_ICONS = {
    'NBA': 'emojione-monotone:basketball',
    'NFL': 'fluent:sport-american-football-24-regular',
    'NHL': 'ph:hockey-light',
    'MLB': 'guidance:baseball',
    'Soccer': 'ph:soccer-ball-light',
    'MMA': 'game-icons:boxing-glove',
};

function getLeagueIcon(league) {
    return LEAGUE_ICONS[league] || LEAGUE_ICONS['NBA'];
}

function renderGameHeader() {
    if (!protocol) return;
    const [home, away] = protocol.teams;
    const isLive = protocol.status === 'LIVE';
    const score = protocol.score;
    const sportIcon = getLeagueIcon(protocol.league);

    document.getElementById('game-info').innerHTML = `
        <div class="flex justify-between items-center mb-4">
            <span class="text-xs font-bold text-gray-400 uppercase">${protocol.league} • ${isLive ? 'LIVE' : 'Upcoming'}</span>
            ${isLive ? `<div class="flex items-center gap-2 bg-neon/10 px-2 py-1 rounded border border-neon/30">
                <div class="w-1.5 h-1.5 bg-neon rounded-full animate-pulse"></div>
                <span class="text-neon text-xs font-bold">${protocol.clock}</span>
            </div>` : ''}
        </div>
        <div class="flex justify-between items-center">
            <div class="flex flex-col items-center gap-2 w-1/3">
                <div class="w-16 h-16 rounded-full bg-white/5 p-3 border border-white/10 flex items-center justify-center">
                    <iconify-icon icon="${sportIcon}" class="text-4xl text-yellow-500"></iconify-icon>
                </div>
                <h2 class="font-tanker text-2xl">${home.toUpperCase()}</h2>
                ${score ? `<span class="font-satoshi text-xl font-bold">${score.home}</span>` : ''}
            </div>
            <div class="flex flex-col items-center w-1/3">
                <span class="font-tanker text-3xl text-gray-600">VS</span>
            </div>
            <div class="flex flex-col items-center gap-2 w-1/3">
                <div class="w-16 h-16 rounded-full bg-white/5 p-3 border border-white/10 flex items-center justify-center">
                    <iconify-icon icon="${sportIcon}" class="text-4xl text-blue-500"></iconify-icon>
                </div>
                <h2 class="font-tanker text-2xl text-gray-300">${away.toUpperCase()}</h2>
                ${score ? `<span class="font-satoshi text-xl font-bold text-gray-400">${score.away}</span>` : ''}
            </div>
        </div>
    `;

    // Fetch and display protocol risk signals
    fetchProtocolRisk();
}

async function fetchProtocolRisk() {
    if (!protocol || !protocol.protocolId) return;
    try {
        const response = await fetch(`${API_BASE}/protocols/${protocol.protocolId}/risk`);
        if (!response.ok) return;
        const risk = await response.json();
        if (risk.triggeredCount > 0) {
            renderProtocolSignals(risk);
        }
    } catch (err) {
        console.log('Protocol risk fetch skipped:', err.message);
    }
}

function renderProtocolSignals(risk) {
    const container = document.getElementById('protocol-signals');
    if (!container) return;

    const riskColors = {
        none: { bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/20' },
        low: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20' },
        moderate: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/20' },
        high: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
        critical: { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/40' },
    };

    const categoryIcons = {
        physical: 'lucide:battery-low',
        tactical: 'lucide:swords',
        volatility: 'lucide:activity',
        psychological: 'lucide:brain',
        market: 'lucide:trending-up',
    };

    const signals = risk.signals || [];
    if (signals.length === 0) return;

    let html = `
        <div class="mb-4">
            <div class="flex items-center gap-2 mb-3">
                <iconify-icon icon="lucide:shield-alert" class="text-neon text-sm"></iconify-icon>
                <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">PROTOCOL INTELLIGENCE</span>
                <span class="text-[10px] font-bold text-neon bg-neon/10 px-1.5 py-0.5 rounded">${risk.triggeredCount} ACTIVE</span>
            </div>
            <p class="text-xs text-gray-400 mb-3">${risk.riskSummary}</p>
            <div class="space-y-2">
    `;

    for (const signal of signals.slice(0, 5)) {
        const colors = riskColors[signal.risk] || riskColors.none;
        const icon = categoryIcons[signal.category] || 'lucide:info';

        html += `
            <div class="${colors.bg} rounded-lg p-3 border ${colors.border}">
                <div class="flex items-center gap-2 mb-1">
                    <iconify-icon icon="${icon}" class="${colors.text} text-sm"></iconify-icon>
                    <span class="text-[10px] font-bold ${colors.text} uppercase">${signal.protocol.replace(/_/g, ' ')}</span>
                    <span class="text-[10px] ${colors.text} ml-auto">${Math.round(signal.confidence * 100)}% conf</span>
                </div>
                <p class="text-xs text-gray-300">${signal.explanation}</p>
            </div>
        `;
    }

    html += `
            </div>
            <div class="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                <div class="text-center">
                    <div class="text-[10px] text-gray-500 uppercase">Fragility</div>
                    <div class="font-tanker text-lg ${risk.fragilityScore >= 0.5 ? 'text-red-400' : risk.fragilityScore >= 0.3 ? 'text-yellow-400' : 'text-green-400'}">
                        ${(risk.fragilityScore * 100).toFixed(0)}%
                    </div>
                </div>
                <div class="text-center">
                    <div class="text-[10px] text-gray-500 uppercase">Confidence</div>
                    <div class="font-tanker text-lg text-white">${(risk.confidenceScore * 100).toFixed(0)}%</div>
                </div>
                <div class="text-center">
                    <div class="text-[10px] text-gray-500 uppercase">Protocols</div>
                    <div class="font-tanker text-lg text-neon">${risk.triggeredCount}</div>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;
    container.classList.remove('hidden');
}

function switchMarket(market) {
    currentMarket = market;
    document.querySelectorAll('#market-tabs button').forEach(btn => {
        btn.classList.remove('bg-neon', 'text-white');
        btn.classList.add('bg-card', 'text-gray-400');
    });
    document.getElementById(`tab-${market}`).classList.add('bg-neon', 'text-white');
    document.getElementById(`tab-${market}`).classList.remove('bg-card', 'text-gray-400');
    renderMarket();
}

function renderMarket() {
    const container = document.getElementById('market-content');
    if (!markets) {
        container.innerHTML = '<div class="text-center text-gray-500">Loading markets...</div>';
        return;
    }

    if (currentMarket === 'main') {
        container.innerHTML = renderMainLines();
    } else if (currentMarket === 'props') {
        container.innerHTML = renderPlayerProps();
    } else {
        container.innerHTML = '<div class="text-center text-gray-500 py-8">Coming soon</div>';
    }
}

function renderMainLines() {
    const [home, away] = protocol.teams;
    const spread = markets.spread;
    const total = markets.total;
    const moneyline = markets.moneyline;

    return `
        <div class="grid grid-cols-7 gap-2 mb-3 text-[10px] font-bold text-gray-500 uppercase text-center">
            <div class="col-span-2 text-left pl-2">Team</div>
            <div class="col-span-2">Spread</div>
            <div class="col-span-1">Total</div>
            <div class="col-span-2">Money</div>
        </div>
        <div class="grid grid-cols-7 gap-2 mb-3">
            <div class="col-span-2 flex items-center">
                <span class="font-tanker text-lg">${home.toUpperCase()}</span>
            </div>
            <button onclick='addLeg({market:"spread",team:"${home}",line:${spread.home.line},odds:${spread.home.odds},selection:"${home} ${spread.home.line}"})' 
                class="col-span-2 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('spread', home) ? 'leg-selected' : ''}">
                <span class="text-xs font-bold">${spread.home.line}</span>
                <span class="text-[10px] text-gray-400">${spread.home.odds}</span>
            </button>
            <button onclick='addLeg({market:"total",side:"over",line:${total.over.line},odds:${total.over.odds},selection:"Over ${total.over.line}"})' 
                class="col-span-1 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('total', 'Over') ? 'leg-selected' : ''}">
                <span class="text-xs">O ${total.over.line}</span>
            </button>
            <button onclick='addLeg({market:"moneyline",team:"${home}",odds:${moneyline.home.odds},selection:"${home} ML"})' 
                class="col-span-2 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('moneyline', home) ? 'leg-selected' : ''}">
                <span class="text-xs font-bold">${moneyline.home.odds}</span>
            </button>
        </div>
        <div class="grid grid-cols-7 gap-2">
            <div class="col-span-2 flex items-center">
                <span class="font-tanker text-lg text-gray-400">${away.toUpperCase()}</span>
            </div>
            <button onclick='addLeg({market:"spread",team:"${away}",line:${spread.away.line},odds:${spread.away.odds},selection:"${away} ${spread.away.line}"})' 
                class="col-span-2 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('spread', away) ? 'leg-selected' : ''}">
                <span class="text-xs font-bold">${spread.away.line}</span>
                <span class="text-[10px] text-gray-400">${spread.away.odds}</span>
            </button>
            <button onclick='addLeg({market:"total",side:"under",line:${total.under.line},odds:${total.under.odds},selection:"Under ${total.under.line}"})' 
                class="col-span-1 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('total', 'Under') ? 'leg-selected' : ''}">
                <span class="text-xs">U ${total.under.line}</span>
            </button>
            <button onclick='addLeg({market:"moneyline",team:"${away}",odds:${moneyline.away.odds},selection:"${away} ML"})' 
                class="col-span-2 h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('moneyline', away) ? 'leg-selected' : ''}">
                <span class="text-xs font-bold">${moneyline.away.odds}</span>
            </button>
        </div>
    `;
}

function renderPlayerProps() {
    const props = markets.player_props || [];
    if (props.length === 0) {
        return '<div class="text-center text-gray-500 py-8">No player props available</div>';
    }

    return `
        <div class="space-y-3">
            ${props.map(prop => `
                <div class="glass-panel p-4 rounded-xl">
                    <div class="flex justify-between items-center mb-3">
                        <div>
                            <div class="font-tanker text-lg">${prop.player}</div>
                            <div class="text-xs text-gray-500 uppercase">${prop.prop}</div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-gray-400">Line</div>
                            <div class="font-bold text-white">${prop.line}</div>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <button onclick='addLeg({market:"player_prop",player:"${prop.player}",prop:"${prop.prop}",line:${prop.line},odds:${prop.over_odds},selection:"${prop.player} O${prop.line} ${prop.prop}"})' 
                            class="h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('player_prop', prop.player + ' Over') ? 'leg-selected' : ''}">
                            <span class="text-xs font-bold">Over ${prop.line}</span>
                            <span class="text-[10px] text-gray-400">${prop.over_odds}</span>
                        </button>
                        <button onclick='addLeg({market:"player_prop",player:"${prop.player}",prop:"${prop.prop}",line:${prop.line},odds:${prop.under_odds},selection:"${prop.player} U${prop.line} ${prop.prop}"})' 
                            class="h-12 rounded-lg bg-card border border-white/5 hover:bg-white/5 flex flex-col items-center justify-center ${isLegSelected('player_prop', prop.player + ' Under') ? 'leg-selected' : ''}">
                            <span class="text-xs font-bold">Under ${prop.line}</span>
                            <span class="text-[10px] text-gray-400">${prop.under_odds}</span>
                        </button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function isLegSelected(market, identifier) {
    return legs.some(leg => {
        if (market === 'spread' || market === 'moneyline') {
            return leg.market === market && leg.team === identifier;
        }
        if (market === 'total') {
            return leg.market === market && leg.selection.includes(identifier);
        }
        if (market === 'player_prop') {
            return leg.market === market && leg.selection.includes(identifier);
        }
        return false;
    });
}

function addLeg(legData) {
    // Check if already exists - if so, remove it
    const existingIndex = legs.findIndex(l => {
        if (l.market !== legData.market) return false;
        if (legData.team && l.team === legData.team) return true;
        if (legData.player && l.player === legData.player && l.line === legData.line) return true;
        if (legData.side && l.side === legData.side) return true;
        return false;
    });
    
    if (existingIndex >= 0) {
        removeLeg(existingIndex);
        return;
    }

    // Add new leg with unique ID
    const leg = {
        id: `leg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        ...legData
    };
    
    legs.push(leg);
    console.log('Leg added:', leg);
    renderLegs();
    recalculate();
    renderMarket(); // Re-render to update selected state
}

function removeLeg(index) {
    legs.splice(index, 1);
    console.log('Leg removed, remaining:', legs.length);
    renderLegs();
    recalculate();
    renderMarket(); // Re-render to update selected state
}

function clearAllLegs() {
    legs = [];
    renderLegs();
    recalculate();
    renderMarket();
}

function renderLegs() {
    const container = document.getElementById('legs-list');
    const countEl = document.getElementById('leg-count');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    countEl.textContent = legs.length;
    
    if (legs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8 text-sm">No legs added yet. Select bets above to build your parlay.</div>';
        analyzeBtn.disabled = true;
        analyzeBtn.classList.add('bg-neon/50', 'cursor-not-allowed');
        analyzeBtn.classList.remove('bg-neon', 'cursor-pointer', 'hover:shadow-[0_0_30px_rgba(255,23,68,0.6)]');
        return;
    }

    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove('bg-neon/50', 'cursor-not-allowed');
    analyzeBtn.classList.add('bg-neon', 'cursor-pointer', 'hover:shadow-[0_0_30px_rgba(255,23,68,0.6)]');

    container.innerHTML = legs.map((leg, index) => {
        const marketColors = {
            'spread': 'neon',
            'total': 'blue-500',
            'moneyline': 'green-500',
            'player_prop': 'purple-500'
        };
        const color = marketColors[leg.market] || 'gray-500';
        const marketLabel = leg.market.replace('_', ' ').toUpperCase();

        return `
            <div class="glass-panel p-4 rounded-xl border-l-4 border-l-${color} relative">
                <button onclick="removeLeg(${index})" class="absolute top-3 right-3 text-gray-600 hover:text-white transition-colors">
                    <iconify-icon icon="lucide:x" class="text-lg"></iconify-icon>
                </button>
                <div class="flex items-center gap-2 mb-2">
                    <span class="text-${color} font-bold text-xs uppercase tracking-wider">${marketLabel}</span>
                    <div class="h-3 w-[1px] bg-white/20"></div>
                    <span class="text-gray-400 text-xs">${protocol.teams.join(' vs ')}</span>
                </div>
                <div class="flex justify-between items-end">
                    <div>
                        <div class="font-tanker text-lg tracking-wide">${leg.selection}</div>
                        <div class="text-xs text-gray-500">${leg.market === 'player_prop' ? 'Player Props' : 'Main Lines'}</div>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-white">${leg.odds}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function americanToDecimal(odds) {
    return odds > 0 ? (odds / 100) + 1 : (100 / Math.abs(odds)) + 1;
}

function calculateParlayOdds(legsArray) {
    if (legsArray.length === 0) return null;
    const decimalOdds = legsArray.map(l => americanToDecimal(l.odds));
    const product = decimalOdds.reduce((a, b) => a * b, 1);
    return product >= 2 ? Math.round((product - 1) * 100) : Math.round(-100 / (product - 1));
}

function calculatePayout(wager, odds) {
    if (!odds) return 0;
    return odds > 0 
        ? wager + (wager * odds / 100)
        : wager + (wager * 100 / Math.abs(odds));
}

function recalculate() {
    const totalOdds = calculateParlayOdds(legs);
    const wager = parseFloat(document.getElementById('wager-input').value) || 0;
    const payout = totalOdds ? calculatePayout(wager, totalOdds) : 0;

    document.getElementById('total-odds').textContent = totalOdds ? (totalOdds > 0 ? `+${totalOdds}` : totalOdds) : '—';
    document.getElementById('est-payout').textContent = `$${payout.toFixed(2)}`;
}

async function analyzeWithDNA() {
    if (legs.length === 0) return;

    const btn = document.getElementById('analyze-btn');
    btn.disabled = true;
    btn.innerHTML = '<span>ANALYZING...</span><iconify-icon icon="lucide:loader" class="animate-spin"></iconify-icon>';

    try {
        // Build input text
        const inputText = legs.map(l => l.selection).join(' + ');

        // Build legs array for DNA (CanonicalLeg format)
        const dnaLegs = legs.map(l => ({
            entity: l.player || l.team || 'Unknown',
            market: l.market,
            value: l.line ? String(l.line) : l.selection,
            raw: l.selection
        }));

        const requestBody = {
            input: inputText,
            tier: 'good',
            legs: dnaLegs
        };
        console.log('Sending DNA request:', requestBody);
        
        const response = await fetch('/app/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log('DNA response:', result);

        // Store result
        sessionStorage.setItem('dna_analysis_result', JSON.stringify(result));

        // Display results
        displayResults(result);

    } catch (err) {
        console.error('DNA analysis failed:', err);
        showError(`Analysis failed: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>ANALYZE WITH DNA</span><iconify-icon icon="lucide:zap"></iconify-icon>';
    }
}

function displayResults(data) {
    console.log('DNA Result data:', data);
    
    const resultsSection = document.getElementById('results-section');
    const verdictBadge = document.getElementById('verdict-badge');
    const confidenceScore = document.getElementById('confidence-score');
    const summaryText = document.getElementById('summary-text');
    const legsBreakdown = document.getElementById('legs-breakdown');

    // Debug: hidden by default
    const rawDataHtml = `<details class="mt-4"><summary class="text-xs text-gray-500 cursor-pointer">Debug</summary><pre class="text-[10px] overflow-auto bg-black/50 p-2 rounded mt-2 text-gray-400">${JSON.stringify(data, null, 2).substring(0, 1000)}</pre></details>`;

    // Extract verdict from DNA engine response
    // Response: { evaluation: { recommendation: { action: 'ACCEPT'|'REDUCE'|'AVOID' } } }
    let verdict = 'UNKNOWN';
    
    const action = data.evaluation?.recommendation?.action ?? 
                   data.recommendation?.action;
    
    if (action) {
        const actionUpper = String(action).toUpperCase();
        verdict = actionUpper === 'ACCEPT' ? 'GOOD' : 
                  actionUpper === 'REDUCE' ? 'RISKY' : 
                  actionUpper === 'AVOID' ? 'PASS' : 'UNKNOWN';
    }
    
    console.log('Extracted verdict:', verdict, 'action:', action);
    
    // Verdict styling
    const verdictColors = {
        'GOOD': 'bg-green-500/20 text-green-400 border border-green-500/30',
        'BETTER': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
        'BEST': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
        'RISKY': 'bg-red-500/20 text-red-400 border border-red-500/30',
        'CAUTION': 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
        'PASS': 'bg-red-500/20 text-red-400 border border-red-500/30',
        'ANALYZING': 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
    };
    
    verdictBadge.className = `px-6 py-3 rounded-xl font-tanker text-2xl tracking-wider ${verdictColors[verdict] || verdictColors['ANALYZING']}`;
    verdictBadge.textContent = verdict;

    // Confidence score from DNA engine (100 - fragilityScore)
    let confidence = 0;
    let fragilityScore = data.fragilityScore ?? data.evaluation?.fragilityScore;
    
    // Fallback: search for fragility in response
    if (fragilityScore === undefined) {
        const jsonStr = JSON.stringify(data);
        const match = jsonStr.match(/"fragility[_\w]*":\s*(\d+\.?\d*)/i);
        if (match) fragilityScore = parseFloat(match[1]);
    }
    
    if (fragilityScore !== undefined && !isNaN(fragilityScore)) {
        confidence = Math.max(0, Math.min(1, (100 - Number(fragilityScore)) / 100));
    }
    const confidencePercent = Math.round(confidence * 100);
    confidenceScore.textContent = `${confidencePercent}%`;
    confidenceScore.className = `font-tanker text-xl ${confidencePercent >= 70 ? 'text-green-400' : confidencePercent >= 50 ? 'text-yellow-400' : 'text-red-400'}`;

    // Summary from DNA engine
    let summary = 'Analysis complete.';
    if (data.evaluation?.recommendation?.reason) {
        summary = data.evaluation.recommendation.reason;
    } else if (data.evaluation?.interpretation?.summary) {
        summary = data.evaluation.interpretation.summary;
    } else if (data.recommendation?.reason) {
        summary = data.recommendation.reason;
    } else if (data.interpretation?.summary) {
        summary = data.interpretation.summary;
    }
    summaryText.innerHTML = `<div class="mb-2">${summary}</div>${rawDataHtml}`;

    // Render protocol risk in DNA results (if present)
    renderProtocolRiskInResults(data);

    // Sprint 2: Render explainability sections
    renderExplainabilitySections(data);

    // Legs breakdown
    const legResults = data.legs || data.leg_results || [];
    if (legResults.length > 0) {
        legsBreakdown.innerHTML = `
            <h4 class="font-tanker text-sm text-gray-400 mb-3">LEG BREAKDOWN</h4>
            ${legResults.map(leg => {
                const signal = leg.signal || leg.verdict || '—';
                const signalColor = signal.toLowerCase().includes('good') || signal.toLowerCase().includes('pass') ? 'text-green-400' :
                                   signal.toLowerCase().includes('risk') || signal.toLowerCase().includes('caution') ? 'text-red-400' : 'text-gray-400';
                return `
                    <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                        <span class="text-sm">${leg.player || leg.team || leg.selection || 'Leg'}</span>
                        <span class="text-xs font-bold ${signalColor}">${signal}</span>
                    </div>
                `;
            }).join('')}
        `;
    } else {
        legsBreakdown.innerHTML = '';
    }

    // Show results section
    resultsSection.classList.remove('hidden');

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function closeResults() {
    document.getElementById('results-section').classList.add('hidden');
}

function showError(message) {
    // Simple error toast
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-red-500/90 text-white px-6 py-3 rounded-lg z-50 font-bold';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function navigateTo(screen) {
    window.location.href = `/new?screen=${screen}`;
}

function goBack() {
    window.history.back();
}

// =============================================================================
// Sprint 2: Explainability Section Rendering
// =============================================================================

function renderExplainabilitySections(data) {
    const container = document.getElementById('explainability-panels');
    if (!container) return;

    const sections = data.explainabilitySections;
    if (!sections) {
        container.innerHTML = '';
        return;
    }

    let html = '<h4 class="font-tanker text-sm text-gray-400 mb-3 tracking-wider">WHY THIS GRADE</h4>';

    // Structural Risk
    const sr = sections.structuralRisk;
    if (sr) {
        html += renderExplainPanel({
            icon: 'lucide:shield',
            title: 'STRUCTURAL RISK',
            headline: sr.headline,
            level: sr.level,
            summary: sr.summary,
            detail: sr.inductorDetail ? formatInductorDetail(sr.inductorDetail) : null,
            recommendation: sr.recommendation,
            recommendationReason: sr.recommendationReason,
            primaryFailureType: sr.primaryFailureType,
            primaryFailureSeverity: sr.primaryFailureSeverity,
        });
    }

    // Correlation
    const corr = sections.correlation;
    if (corr) {
        html += renderExplainPanel({
            icon: 'lucide:link',
            title: 'CORRELATION',
            headline: corr.headline,
            level: corr.count > 0 ? (corr.penalty > 10 ? 'critical' : 'loaded') : 'stable',
            summary: corr.summary,
            detail: corr.details ? formatCorrelationDetails(corr.details, corr.multiplier) : null,
            penalty: corr.penalty,
        });
    }

    // Fragility Breakdown
    const frag = sections.fragilityBreakdown;
    if (frag) {
        html += renderExplainPanel({
            icon: 'lucide:activity',
            title: 'FRAGILITY',
            headline: frag.headline,
            level: fragilityToLevel(frag.finalFragility),
            summary: frag.summary,
            detail: frag.blocks ? formatBlockDetails(frag.blocks) : null,
            fragility: frag.finalFragility,
        });
    }

    // Context Snapshot
    const ctx = sections.contextSnapshot;
    if (ctx) {
        html += renderExplainPanel({
            icon: 'lucide:cloud',
            title: 'CONTEXT',
            headline: ctx.headline,
            level: ctx.hasContext ? 'loaded' : 'stable',
            summary: ctx.summary,
            detail: ctx.modifiers ? formatContextModifiers(ctx.modifiers) : null,
        });
    }

    container.innerHTML = html;
}

function renderExplainPanel(opts) {
    const levelColors = {
        stable: { border: 'border-green-500/30', badge: 'bg-green-500/20 text-green-400', dot: 'bg-green-500' },
        loaded: { border: 'border-yellow-500/30', badge: 'bg-yellow-500/20 text-yellow-400', dot: 'bg-yellow-500' },
        tense: { border: 'border-orange-500/30', badge: 'bg-orange-500/20 text-orange-400', dot: 'bg-orange-500' },
        critical: { border: 'border-red-500/30', badge: 'bg-red-500/20 text-red-400', dot: 'bg-red-500' },
    };
    const colors = levelColors[opts.level] || levelColors.stable;

    let content = '';

    // Summary (BETTER + BEST tiers)
    if (opts.summary) {
        content += `<p class="text-sm text-gray-300 mt-3">${opts.summary}</p>`;
    }

    // Recommendation (BETTER + BEST)
    if (opts.recommendation) {
        const recColors = { accept: 'text-green-400', reduce: 'text-yellow-400', avoid: 'text-red-400' };
        const recColor = recColors[opts.recommendation] || 'text-gray-400';
        content += `<div class="mt-2 flex items-center gap-2">
            <span class="text-xs text-gray-500 uppercase">Action:</span>
            <span class="text-xs font-bold ${recColor} uppercase">${opts.recommendation}</span>
        </div>`;
        if (opts.recommendationReason) {
            content += `<p class="text-xs text-gray-400 mt-1">${opts.recommendationReason}</p>`;
        }
    }

    // Primary failure (BEST)
    if (opts.primaryFailureType) {
        const sevColor = opts.primaryFailureSeverity === 'high' ? 'text-red-400' :
                         opts.primaryFailureSeverity === 'medium' ? 'text-yellow-400' : 'text-gray-400';
        content += `<div class="mt-2 flex items-center gap-2">
            <span class="text-xs text-gray-500">Primary risk:</span>
            <span class="text-xs font-bold ${sevColor}">${opts.primaryFailureType.replace(/_/g, ' ')}</span>
            <span class="text-[10px] ${sevColor} uppercase">(${opts.primaryFailureSeverity})</span>
        </div>`;
    }

    // Penalty badge
    let penaltyBadge = '';
    if (opts.penalty !== undefined && opts.penalty > 0) {
        penaltyBadge = `<span class="text-[10px] font-bold text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">+${opts.penalty.toFixed(1)}pt</span>`;
    }

    // Fragility score
    let fragBadge = '';
    if (opts.fragility !== undefined) {
        fragBadge = `<span class="text-[10px] font-bold ${colors.badge} px-1.5 py-0.5 rounded">${opts.fragility.toFixed(1)}/100</span>`;
    }

    // Detail section (BEST tier - collapsible)
    let detailHtml = '';
    if (opts.detail) {
        detailHtml = `<details class="mt-3">
            <summary class="text-[10px] text-gray-500 cursor-pointer uppercase tracking-wider hover:text-gray-300 transition-colors">Show Detail</summary>
            <div class="mt-2 space-y-1">${opts.detail}</div>
        </details>`;
    }

    return `
        <div class="bg-white/[0.02] rounded-xl p-4 border ${colors.border} relative overflow-hidden">
            <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                    <div class="w-1.5 h-1.5 rounded-full ${colors.dot}"></div>
                    <iconify-icon icon="${opts.icon}" class="text-sm text-gray-400"></iconify-icon>
                    <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">${opts.title}</span>
                </div>
                <div class="flex items-center gap-2">
                    ${penaltyBadge}
                    ${fragBadge}
                </div>
            </div>
            <div class="font-tanker text-lg tracking-wide text-white">${opts.headline}</div>
            ${content}
            ${detailHtml}
        </div>
    `;
}

function formatInductorDetail(detail) {
    return `
        <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="bg-white/5 rounded p-2">
                <div class="text-gray-500 text-[10px] uppercase">Final Fragility</div>
                <div class="font-bold text-white">${detail.finalFragility.toFixed(1)}</div>
            </div>
            <div class="bg-white/5 rounded p-2">
                <div class="text-gray-500 text-[10px] uppercase">Leg Penalty</div>
                <div class="font-bold text-white">+${detail.legPenalty.toFixed(1)}pt</div>
            </div>
            <div class="bg-white/5 rounded p-2">
                <div class="text-gray-500 text-[10px] uppercase">Corr. Penalty</div>
                <div class="font-bold text-white">+${detail.correlationPenalty.toFixed(1)}pt</div>
            </div>
            <div class="bg-white/5 rounded p-2">
                <div class="text-gray-500 text-[10px] uppercase">Corr. Multiplier</div>
                <div class="font-bold text-white">${detail.correlationMultiplier.toFixed(2)}x</div>
            </div>
        </div>
    `;
}

function formatCorrelationDetails(details, multiplier) {
    let html = details.map(d => `
        <div class="flex justify-between items-center p-2 bg-white/5 rounded text-xs">
            <span class="text-gray-300">${d.type.replace(/_/g, ' ')}</span>
            <span class="font-bold text-red-400">+${d.penalty.toFixed(1)}pt</span>
        </div>
    `).join('');
    if (multiplier) {
        html += `<div class="text-[10px] text-gray-500 mt-1">Multiplier: ${multiplier.toFixed(2)}x</div>`;
    }
    return html;
}

function formatBlockDetails(blocks) {
    return blocks.map(b => `
        <div class="flex justify-between items-center p-2 bg-white/5 rounded text-xs">
            <div class="flex-1 min-w-0">
                <div class="text-gray-300 truncate">${b.selection}</div>
                <div class="text-[10px] text-gray-500 uppercase">${b.betType.replace(/_/g, ' ')}</div>
            </div>
            <div class="text-right shrink-0 ml-3">
                <div class="text-gray-400">base: ${b.baseFragility.toFixed(2)}</div>
                <div class="font-bold text-white">eff: ${b.effectiveFragility.toFixed(2)}</div>
            </div>
        </div>
    `).join('');
}

function formatContextModifiers(modifiers) {
    return modifiers.map(m => `
        <div class="flex justify-between items-center p-2 bg-white/5 rounded text-xs">
            <div>
                <span class="text-gray-300 uppercase font-bold">${m.type}</span>
                <span class="text-gray-500 ml-2">${m.blockSelection}</span>
            </div>
            <div class="text-right">
                <span class="font-bold ${m.delta > 0 ? 'text-red-400' : 'text-green-400'}">
                    ${m.delta > 0 ? '+' : ''}${m.delta.toFixed(1)}pt
                </span>
            </div>
        </div>
    `).join('');
}

function fragilityToLevel(fragility) {
    if (fragility <= 15) return 'stable';
    if (fragility <= 35) return 'loaded';
    if (fragility <= 60) return 'tense';
    return 'critical';
}

// =============================================================================
// Protocol Risk in DNA Results
// =============================================================================

function renderProtocolRiskInResults(data) {
    const container = document.getElementById('explainability-panels');
    if (!container) return;

    const protocolRisk = data.protocolRisk || data.protocol_risk;
    if (!protocolRisk || !protocolRisk.triggeredCount) return;

    const categoryIcons = {
        physical: 'lucide:battery-low',
        tactical: 'lucide:swords',
        volatility: 'lucide:activity',
        psychological: 'lucide:brain',
        market: 'lucide:trending-up',
    };

    // Build category risk summary
    const categoryRisks = protocolRisk.categoryRisks || {};
    const activeCats = Object.entries(categoryRisks)
        .filter(([_, risk]) => risk !== 'none')
        .sort((a, b) => {
            const order = { critical: 0, high: 1, moderate: 2, low: 3 };
            return (order[a[1]] || 4) - (order[b[1]] || 4);
        });

    const riskColors = {
        low: 'text-green-400',
        moderate: 'text-yellow-400',
        high: 'text-red-400',
        critical: 'text-red-300',
    };

    let catHtml = activeCats.map(([cat, risk]) => {
        const icon = categoryIcons[cat] || 'lucide:info';
        const color = riskColors[risk] || 'text-gray-400';
        return `
            <div class="flex items-center gap-2 p-2 bg-white/5 rounded text-xs">
                <iconify-icon icon="${icon}" class="${color}"></iconify-icon>
                <span class="text-gray-300 capitalize">${cat}</span>
                <span class="font-bold ${color} ml-auto uppercase text-[10px]">${risk}</span>
            </div>
        `;
    }).join('');

    // Dual evaluation comparison (if present)
    let dualHtml = '';
    const dual = protocolRisk.dual_evaluation || protocolRisk.dualEvaluation;
    if (dual && dual.adjusted) {
        const impact = dual.adjusted.protocol_impact || dual.adjusted.protocolImpact || 0;
        const modifier = dual.adjusted.stability_modifier || dual.adjusted.stabilityModifier || 1;
        dualHtml = `
            <div class="mt-3 pt-3 border-t border-white/5">
                <div class="text-[10px] text-gray-500 uppercase mb-2">DNA + Protocol Comparison</div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="bg-white/5 rounded p-2">
                        <div class="text-[10px] text-gray-500">Stability</div>
                        <div class="font-bold ${modifier < 0.85 ? 'text-red-400' : modifier < 0.95 ? 'text-yellow-400' : 'text-green-400'}">${(modifier * 100).toFixed(0)}%</div>
                    </div>
                    <div class="bg-white/5 rounded p-2">
                        <div class="text-[10px] text-gray-500">Protocol Impact</div>
                        <div class="font-bold text-red-400">-${(impact * 100).toFixed(1)}%</div>
                    </div>
                </div>
            </div>
        `;
    }

    // Prepend protocol panel before other explainability sections
    const protocolPanel = renderExplainPanel({
        icon: 'lucide:shield-alert',
        title: 'PROTOCOL INTELLIGENCE',
        headline: protocolRisk.riskSummary ? protocolRisk.riskSummary.split('.')[0] : 'Contextual Risk Detected',
        level: protocolRisk.fragilityScore >= 0.5 ? 'critical' : protocolRisk.fragilityScore >= 0.3 ? 'tense' : 'loaded',
        summary: protocolRisk.riskSummary,
        detail: catHtml + dualHtml,
    });

    container.insertAdjacentHTML('afterbegin', protocolPanel);
}
