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

function renderGameHeader() {
    if (!protocol) return;
    const [home, away] = protocol.teams;
    const isLive = protocol.status === 'LIVE';
    const score = protocol.score;

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
                    <iconify-icon icon="emojione-monotone:basketball" class="text-4xl text-yellow-500"></iconify-icon>
                </div>
                <h2 class="font-tanker text-2xl">${home.toUpperCase()}</h2>
                ${score ? `<span class="font-satoshi text-xl font-bold">${score.home}</span>` : ''}
            </div>
            <div class="flex flex-col items-center w-1/3">
                <span class="font-tanker text-3xl text-gray-600">VS</span>
            </div>
            <div class="flex flex-col items-center gap-2 w-1/3">
                <div class="w-16 h-16 rounded-full bg-white/5 p-3 border border-white/10 flex items-center justify-center">
                    <iconify-icon icon="emojione-monotone:basketball" class="text-4xl text-blue-500"></iconify-icon>
                </div>
                <h2 class="font-tanker text-2xl text-gray-300">${away.toUpperCase()}</h2>
                ${score ? `<span class="font-satoshi text-xl font-bold text-gray-400">${score.away}</span>` : ''}
            </div>
        </div>
    `;
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

        // Build legs array for DNA
        const dnaLegs = legs.map(l => ({
            market: l.market,
            team: l.team,
            player: l.player,
            prop: l.prop,
            line: l.line,
            odds: l.odds
        }));

        const response = await fetch('/app/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                input: inputText,
                tier: 'good',
                legs: dnaLegs
            })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const result = await response.json();
        console.log('DNA response:', result);

        // Store result
        sessionStorage.setItem('dna_analysis_result', JSON.stringify(result));

        // Display results
        displayResults(result);

    } catch (err) {
        console.error('DNA analysis failed:', err);
        showError('Analysis failed. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>ANALYZE WITH DNA</span><iconify-icon icon="lucide:zap"></iconify-icon>';
    }
}

function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    const verdictBadge = document.getElementById('verdict-badge');
    const confidenceScore = document.getElementById('confidence-score');
    const summaryText = document.getElementById('summary-text');
    const legsBreakdown = document.getElementById('legs-breakdown');

    // Extract verdict
    const verdict = data.overallAssessment?.verdict || 
                   data.verdict || 
                   data.overall_assessment?.verdict || 
                   'ANALYZING';
    
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

    // Confidence score
    const confidence = data.overallAssessment?.confidenceScore || 
                      data.confidence_score || 
                      data.overall_assessment?.confidence_score ||
                      0;
    const confidencePercent = Math.round(confidence * 100);
    confidenceScore.textContent = `${confidencePercent}%`;
    confidenceScore.className = `font-tanker text-xl ${confidencePercent >= 70 ? 'text-green-400' : confidencePercent >= 50 ? 'text-yellow-400' : 'text-red-400'}`;

    // Summary
    const summary = data.overallAssessment?.summary || 
                   data.summary || 
                   data.overall_assessment?.summary ||
                   'Analysis complete.';
    summaryText.textContent = summary;

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
