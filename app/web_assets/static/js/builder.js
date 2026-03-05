// S19-D: Parlay Builder Logic (using new /api/odds endpoint)
const API_BASE = '/api';
let protocol = null;
let markets = null;
let legs = [];
let currentMarket = 'main';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadProtocol();
        await loadMarkets();
        renderGameHeader();
        renderMarket();
        renderLegs();
    } catch (error) {
        console.error('Builder initialization failed:', error);
        document.body.innerHTML = `
            <div class="flex flex-col items-center justify-center h-screen text-white p-6">
                <h1 class="text-2xl font-bold mb-4">Something went wrong</h1>
                <p class="text-gray-400 mb-6">Failed to load builder. Please clear your cache and try again.</p>
                <button onclick="window.location.reload(true)" class="px-6 py-3 bg-neon text-white rounded-lg font-bold">
                    Reload Page
                </button>
                <button onclick="window.location.href='/'" class="mt-4 px-6 py-3 bg-white/10 text-white rounded-lg">
                    Go Home
                </button>
            </div>
        `;
    }
});

async function loadProtocol() {
    const stored = sessionStorage.getItem('dna_protocol_context');
    let useStored = false;
    
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            // Validate the stored protocol has a valid game ID format
            const gameId = parsed.gameId || parsed.protocolId;
            if (gameId && gameId.includes('-at-') && gameId.startsWith('nhl-')) {
                protocol = parsed;
                useStored = true;
            } else {
                sessionStorage.removeItem('dna_protocol_context');
            }
        } catch (e) {
            console.error('Failed to parse stored protocol, clearing:', e);
            sessionStorage.removeItem('dna_protocol_context');
        }
    }
    
    if (!useStored) {
        // Fetch first available NHL game as fallback
        try {
            const gamesResponse = await fetch(`${API_BASE}/games?sport=NHL`);
            if (gamesResponse.ok) {
                const games = await gamesResponse.json();
                if (games && games.length > 0) {
                    const game = games[0];
                    protocol = {
                        protocolId: game.id,
                        league: game.league,
                        gameId: game.id,
                        teams: [game.home, game.away],
                        status: game.status,
                        clock: null,
                        score: null
                    };
                    return;
                }
            }
        } catch (e) {
            console.error('Failed to fetch fallback game:', e);
        }
        // Ultimate fallback
        protocol = {
            protocolId: 'nhl-edmonton-oilers-at-anaheim-ducks-2026-02-26',
            league: 'NHL',
            gameId: 'nhl-edmonton-oilers-at-anaheim-ducks-2026-02-26',
            teams: ['Anaheim Ducks', 'Edmonton Oilers'],
            status: 'SCHEDULED',
            clock: null,
            score: null
        };
    }
}

async function loadMarkets() {
    if (!protocol) return;
    try {
        // S19-D: Use new /api/odds endpoint
        const gameId = protocol.gameId || protocol.protocolId || 'lal-gsw-2026-02-09';
        const response = await fetch(`${API_BASE}/odds/${gameId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // API returns array, transform to expected structure
        const marketsArray = await response.json();

        // Transform array to object structure expected by renderer
        markets = {
            spread: { home: {}, away: {} },
            total: { over: {}, under: {} },
            moneyline: { home: {}, away: {} },
            player_props: []
        };

        if (Array.isArray(marketsArray)) {
            marketsArray.forEach(m => {
                if (m.market === 'spread' && m.selections) {
                    m.selections.forEach(sel => {
                        if (sel.label && sel.label.includes(' -')) {
                            markets.spread.home = { line: sel.line || '-4.5', odds: sel.odds || -110 };
                        } else if (sel.label && sel.label.includes(' +')) {
                            markets.spread.away = { line: sel.line || '+4.5', odds: sel.odds || -110 };
                        }
                    });
                } else if (m.market === 'total' && m.selections) {
                    m.selections.forEach(sel => {
                        if (sel.label && sel.label.includes('Over')) {
                            markets.total.over = { line: sel.line || '220.5', odds: sel.odds || -110 };
                        } else if (sel.label && sel.label.includes('Under')) {
                            markets.total.under = { line: sel.line || '220.5', odds: sel.odds || -110 };
                        }
                    });
                } else if (m.market === 'moneyline' && m.selections) {
                    m.selections.forEach(sel => {
                        if (sel.label && !sel.label.includes('ML')) {
                            // First selection is usually home
                            if (!markets.moneyline.home.odds) {
                                markets.moneyline.home = { odds: sel.odds || -150 };
                            } else {
                                markets.moneyline.away = { odds: sel.odds || +130 };
                            }
                        }
                    });
                } else if ((m.market === 'player_prop' || m.market.startsWith('player_')) && m.selections) {
                    // Group selections by player + prop type
                    // API may return player_points, player_rebounds, player_assists, etc.
                    const propType = m.market.replace('player_', '').toUpperCase();
                    const propsMap = new Map();
                    m.selections.forEach(sel => {
                        // Pattern 1: "LeBron James O27.5 PTS"
                        let match = sel.label.match(/^(.+?)\s+([OU])([\d.]+)\s+(.+)$/i);

                        if (!match) {
                            // Pattern 2: "LeBron James Over 27.5 PTS"
                            match = sel.label.match(/^(.+?)\s+(Over|Under)\s+([\d.]+)\s+(.+)$/i);
                            if (match) {
                                match[2] = match[2].charAt(0).toUpperCase();
                                match = [match[0], match[1], match[2], match[3], match[4]];
                            }
                        }

                        if (match) {
                            const [, player, overUnder, line, prop] = match;
                            const key = `${player.trim()}|${prop.trim()}|${line}`;
                            if (!propsMap.has(key)) {
                                propsMap.set(key, {
                                    player: player.trim(),
                                    prop: prop.trim().toUpperCase(),
                                    line: parseFloat(line),
                                    over_odds: null,
                                    under_odds: null
                                });
                            }
                            const propData = propsMap.get(key);
                            if (overUnder === 'O' || overUnder === 'OVER') {
                                propData.over_odds = sel.odds || -110;
                            } else if (overUnder === 'U' || overUnder === 'UNDER') {
                                propData.under_odds = sel.odds || -110;
                            }
                        }
                    });
                    // Merge into existing player_props array (multiple market types)
                    markets.player_props = markets.player_props.concat(Array.from(propsMap.values()));
                }
            });
        }

        // Ensure we have defaults if API didn't return expected structure
        if (!markets.spread.home.line) {
            markets.spread.home = { line: '-4.5', odds: -110 };
            markets.spread.away = { line: '+4.5', odds: -110 };
        }
        if (!markets.total.over.line) {
            markets.total.over = { line: '220.5', odds: -110 };
            markets.total.under = { line: '220.5', odds: -110 };
        }
        if (!markets.moneyline.home.odds) {
            markets.moneyline.home = { odds: -150 };
            markets.moneyline.away = { odds: +130 };
        }

    } catch (err) {
        console.error('Failed to load markets:', err);
        // Fallback to default markets
        markets = {
            spread: { home: { line: '-4.5', odds: -110 }, away: { line: '+4.5', odds: -110 } },
            total: { over: { line: '220.5', odds: -110 }, under: { line: '220.5', odds: -110 } },
            moneyline: { home: { odds: -150 }, away: { odds: +130 } },
            player_props: []
        };
    }
}

function getSportIcon(league) {
    const icons = {
        'NBA': 'emojione-monotone:basketball',
        'NHL': 'game-icons:ice-hockey',
        'NFL': 'game-icons:american-football-helmet',
        'MLB': 'game-icons:baseball-bat'
    };
    return icons[league] || 'lucide:trophy';
}

function getSportColor(league) {
    const colors = {
        'NBA': { home: 'text-orange-500', away: 'text-purple-500' },
        'NHL': { home: 'text-yellow-500', away: 'text-blue-500' },
        'NFL': { home: 'text-red-500', away: 'text-blue-500' },
        'MLB': { home: 'text-green-500', away: 'text-red-500' }
    };
    return colors[league] || { home: 'text-gray-400', away: 'text-gray-400' };
}

function renderGameHeader() {
    if (!protocol) return;
    const [home, away] = protocol.teams;
    const isLive = protocol.status === 'LIVE';
    const score = protocol.score;
    const icon = getSportIcon(protocol.league);
    const colors = getSportColor(protocol.league);

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
                    <iconify-icon icon="${icon}" class="text-4xl ${colors.home}"></iconify-icon>
                </div>
                <h2 class="font-tanker text-2xl">${home.toUpperCase()}</h2>
                ${score ? `<span class="font-satoshi text-xl font-bold">${score.home}</span>` : ''}
            </div>
            <div class="flex flex-col items-center w-1/3">
                <span class="font-tanker text-3xl text-gray-600">VS</span>
            </div>
            <div class="flex flex-col items-center gap-2 w-1/3">
                <div class="w-16 h-16 rounded-full bg-white/5 p-3 border border-white/10 flex items-center justify-center">
                    <iconify-icon icon="${icon}" class="text-4xl ${colors.away}"></iconify-icon>
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
    } else if (currentMarket === 'quarters') {
        container.innerHTML = renderQuarters();
    } else if (currentMarket === 'halves') {
        container.innerHTML = renderHalves();
    } else {
        container.innerHTML = '<div class="text-center text-gray-500 py-8">Market not available</div>';
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
        return `
            <div class="text-center py-12 px-6">
                <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                    <iconify-icon icon="lucide:users" class="text-3xl text-gray-500"></iconify-icon>
                </div>
                <h4 class="font-tanker text-lg text-gray-300 mb-2">Player Props Coming Soon</h4>
                <p class="text-sm text-gray-500 max-w-xs mx-auto">
                    Individual player stats and prop bets are coming soon for ${protocol?.league || 'NHL'}. Stay tuned!
                </p>
            </div>
        `;
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
        // Handle quarter markets (q1_spread, q2_total, etc.)
        if (market.includes('_')) {
            return leg.market === market && leg.selection === identifier;
        }
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

async function addLeg(legData) {
    // S21-D: Load user preferences and check constraints
    let userPrefs = null;
    try {
        const token = sessionStorage.getItem('dna_auth_token') || localStorage.getItem('dna_auth_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const prefsResponse = await fetch(`${API_BASE}/preferences`, { headers });
        if (prefsResponse.ok) {
            userPrefs = await prefsResponse.json();
        }
    } catch (err) {
        // No user preferences found, using defaults
    }
    
    // S21-D: Check constraints if preferences exist
    if (userPrefs && userPrefs.constraints) {
        // Check max_legs
        const maxLegs = userPrefs.constraints.max_legs || 6;
        if (legs.length >= maxLegs) {
            showError(`Cannot add more than ${maxLegs} legs (your preference)`);
            return;
        }
        
        // Check no_unders
        if (userPrefs.constraints.no_unders && legData.selection.toLowerCase().includes('under')) {
            showError('Under bets disabled in your preferences');
            return;
        }
        
        // Check favorite_sports
        const favSports = userPrefs.constraints.favorite_sports || [];
        if (favSports.length > 0) {
            const currentSport = protocol?.league || 'NBA';
            if (!favSports.map(s => s.toUpperCase()).includes(currentSport.toUpperCase())) {
                showError(`${currentSport} not in your preferred sports: ${favSports.join(', ')}`);
                return;
            }
        }
    }

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
    renderLegs();
    recalculate();
    renderMarket(); // Re-render to update selected state
}

function removeLeg(index) {
    legs.splice(index, 1);
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
    const submitBtn = document.getElementById('submit-bet-btn');
    
    countEl.textContent = legs.length;
    
    if (legs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8 text-sm">No legs added yet. Select bets above to build your parlay.</div>';
        analyzeBtn.disabled = true;
        analyzeBtn.classList.add('bg-neon/50', 'cursor-not-allowed');
        analyzeBtn.classList.remove('bg-neon', 'cursor-pointer', 'hover:shadow-[0_0_30px_rgba(255,23,68,0.6)]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('cursor-not-allowed', 'opacity-50');
            submitBtn.classList.remove('cursor-pointer', 'hover:bg-neon/20');
        }
        return;
    }

    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove('bg-neon/50', 'cursor-not-allowed');
    analyzeBtn.classList.add('bg-neon', 'cursor-pointer', 'hover:shadow-[0_0_30px_rgba(255,23,68,0.6)]');
    
    // Enable submit button when legs are added
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('cursor-not-allowed', 'opacity-50');
        submitBtn.classList.add('cursor-pointer', 'hover:bg-neon/20');
    }

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

function setWager(amount) {
    const input = document.getElementById('wager-input');
    input.value = amount;
    recalculate();
    
    // Visual feedback - brief highlight
    input.parentElement.classList.add('border-neon');
    setTimeout(() => {
        input.parentElement.classList.remove('border-neon');
    }, 300);
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
        const response = await fetch('/app/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();

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
    const resultsSection = document.getElementById('results-section');
    const verdictBadge = document.getElementById('verdict-badge');
    const confidenceScore = document.getElementById('confidence-score');
    const summaryText = document.getElementById('summary-text');
    const legsBreakdown = document.getElementById('legs-breakdown');

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
    summaryText.innerHTML = `<div class="mb-2">${summary}</div>`;

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

// S18-E + Priority 1: Submit bet to backend
async function submitBet() {
    if (legs.length === 0) {
        showError('Add at least one leg to submit bet');
        return;
    }

    const wagerInput = document.getElementById('wager-input');
    const wager = parseInt(wagerInput.value) * 100; // Convert to cents

    if (isNaN(wager) || wager <= 0) {
        showError('Enter a valid wager amount');
        return;
    }

    // Build input text
    const inputText = legs.map(l => l.selection).join(' + ');

    // Get DNA analysis result if available
    const dnaResult = JSON.parse(sessionStorage.getItem('dna_analysis_result') || '{}');

    // Calculate total odds
    let totalOdds = 0;
    legs.forEach(leg => {
        if (leg.odds > 0) {
            totalOdds += leg.odds;
        } else {
            totalOdds -= 10000 / leg.odds; // Convert negative odds
        }
    });

    // Calculate payout
    let potentialPayout = wager;
    if (totalOdds > 0) {
        potentialPayout = Math.floor(wager * (totalOdds / 100 + 1));
    } else {
        potentialPayout = Math.floor(wager * (100 / Math.abs(totalOdds) + 1));
    }

    // Get auth token
    const token = sessionStorage.getItem('dna_auth_token') || localStorage.getItem('dna_auth_token');
    if (!token) {
        showError('Please log in to submit bet');
        setTimeout(() => window.location.href = '/app?screen=auth', 2000);
        return;
    }

    const submitBtn = document.getElementById('submit-bet-btn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>SUBMITTING...</span>';
    }

    try {
        const requestBody = {
            input_text: inputText,
            legs: legs.map(l => ({
                entity: l.player || l.team || 'Unknown',
                market: l.market,
                value: l.line ? String(l.line) : null,
                odds: l.odds,
                selection: l.selection
            })),
            wager: wager,
            total_odds: Math.round(totalOdds),
            potential_payout: potentialPayout,
            verdict: dnaResult.verdict,
            confidence: dnaResult.confidence
        };

        const response = await fetch('/api/bets/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(requestBody)
        });

        const result = await response.json();

        if (result.success) {
            showSuccess(`Bet submitted! ID: ${result.bet_id}`);
            // Clear legs after successful submission
            legs = [];
            renderLegs();
            recalculate();
            closeResults();
            // Redirect to history after 2 seconds
            setTimeout(() => window.location.href = '/app?screen=history', 2000);
        } else {
            showError(result.error || 'Failed to submit bet');
        }
    } catch (err) {
        console.error('Bet submission failed:', err);
        showError('Network error. Please try again.');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>SUBMIT BET</span>';
        }
    }
}

function renderQuarters() {
    const [home, away] = protocol.teams;
    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    
    // Use main game lines as fallback for quarters (simplified)
    const spread = markets.spread || { home: { line: '-4.5', odds: -110 }, away: { line: '+4.5', odds: -110 } };
    const total = markets.total || { over: { line: '220.5', odds: -110 }, under: { line: '220.5', odds: -110 } };
    
    let html = '<div class="space-y-4">';
    
    quarters.forEach(q => {
        html += `
            <div class="bg-card rounded-xl p-4 border border-white/5">
                <h4 class="font-tanker text-lg mb-3 text-neon">${q} LINES</h4>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <p class="text-xs text-gray-500 mb-2">${home.toUpperCase()}</p>
                        <div class="flex gap-2">
                            <button onclick='addLeg({market:"${q.toLowerCase()}_spread",team:"${home}",line:"${spread.home.line}",odds:${spread.home.odds},selection:"${home} ${spread.home.line} ${q}"})' 
                                class="flex-1 h-10 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 ${isLegSelected(q.toLowerCase() + '_spread', home + ' ' + spread.home.line + ' ' + q) ? 'leg-selected' : ''}">
                                ${spread.home.line} (${spread.home.odds})
                            </button>
                            <button onclick='addLeg({market:"${q.toLowerCase()}_total",side:"over",line:"${total.over.line}",odds:${total.over.odds},selection:"Over ${total.over.line} ${q}"})' 
                                class="flex-1 h-10 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 ${isLegSelected(q.toLowerCase() + '_total', 'Over ' + total.over.line + ' ' + q) ? 'leg-selected' : ''}">
                                O ${total.over.line}
                            </button>
                        </div>
                    </div>
                    <div>
                        <p class="text-xs text-gray-500 mb-2">${away.toUpperCase()}</p>
                        <div class="flex gap-2">
                            <button onclick='addLeg({market:"${q.toLowerCase()}_spread",team:"${away}",line:"${spread.away.line}",odds:${spread.away.odds},selection:"${away} ${spread.away.line} ${q}"})' 
                                class="flex-1 h-10 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 ${isLegSelected(q.toLowerCase() + '_spread', away + ' ' + spread.away.line + ' ' + q) ? 'leg-selected' : ''}">
                                ${spread.away.line} (${spread.away.odds})
                            </button>
                            <button onclick='addLeg({market:"${q.toLowerCase()}_total",side:"under",line:"${total.under.line}",odds:${total.under.odds},selection:"Under ${total.under.line} ${q}"})' 
                                class="flex-1 h-10 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 ${isLegSelected(q.toLowerCase() + '_total', 'Under ' + total.under.line + ' ' + q) ? 'leg-selected' : ''}">
                                U ${total.under.line}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

function renderHalves() {
    const [home, away] = protocol.teams;
    const halves = ['1st Half', '2nd Half'];
    
    // Use main game lines as fallback for halves (simplified)
    const spread = markets.spread || { home: { line: '-4.5', odds: -110 }, away: { line: '+4.5', odds: -110 } };
    const total = markets.total || { over: { line: '220.5', odds: -110 }, under: { line: '220.5', odds: -110 } };
    const moneyline = markets.moneyline || { home: { odds: -150 }, away: { odds: +130 } };
    
    let html = '<div class="space-y-4">';
    
    halves.forEach((half, idx) => {
        const halfCode = idx === 0 ? '1H' : '2H';
        html += `
            <div class="bg-card rounded-xl p-4 border border-white/5">
                <h4 class="font-tanker text-lg mb-3 text-neon">${half.toUpperCase()}</h4>
                <div class="grid grid-cols-7 gap-2 mb-3 text-[10px] font-bold text-gray-500 uppercase text-center">
                    <div class="col-span-2 text-left pl-2">Team</div>
                    <div class="col-span-2">Spread</div>
                    <div class="col-span-2">Total</div>
                    <div class="col-span-1">ML</div>
                </div>
                <div class="grid grid-cols-7 gap-2 mb-2">
                    <div class="col-span-2 flex items-center">
                        <span class="font-tanker text-sm">${home.toUpperCase()}</span>
                    </div>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_spread",team:"${home}",line:"${spread.home.line}",odds:${spread.home.odds},selection:"${home} ${spread.home.line} ${halfCode}"})'
                        class="col-span-2 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_spread', home + ' ' + spread.home.line + ' ' + halfCode) ? 'leg-selected' : ''}">
                        ${spread.home.line}
                    </button>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_total",side:"over",line:"${total.over.line}",odds:${total.over.odds},selection:"Over ${total.over.line} ${halfCode}"})'
                        class="col-span-2 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_total', 'Over ' + total.over.line + ' ' + halfCode) ? 'leg-selected' : ''}">
                        O ${total.over.line}
                    </button>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_moneyline",team:"${home}",odds:${moneyline.home.odds},selection:"${home} ML ${halfCode}"})'
                        class="col-span-1 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_moneyline', home + ' ML ' + halfCode) ? 'leg-selected' : ''}">
                        ${moneyline.home.odds}
                    </button>
                </div>
                <div class="grid grid-cols-7 gap-2">
                    <div class="col-span-2 flex items-center">
                        <span class="font-tanker text-sm text-gray-400">${away.toUpperCase()}</span>
                    </div>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_spread",team:"${away}",line:"${spread.away.line}",odds:${spread.away.odds},selection:"${away} ${spread.away.line} ${halfCode}"})'
                        class="col-span-2 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_spread', away + ' ' + spread.away.line + ' ' + halfCode) ? 'leg-selected' : ''}">
                        ${spread.away.line}
                    </button>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_total",side:"under",line:"${total.under.line}",odds:${total.under.odds},selection:"Under ${total.under.line} ${halfCode}"})'
                        class="col-span-2 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_total', 'Under ' + total.under.line + ' ' + halfCode) ? 'leg-selected' : ''}">
                        U ${total.under.line}
                    </button>
                    <button onclick='addLeg({market:"${halfCode.toLowerCase()}_moneyline",team:"${away}",odds:${moneyline.away.odds},selection:"${away} ML ${halfCode}"})'
                        class="col-span-1 h-10 rounded bg-white/5 border border-white/10 hover:bg-white/10 text-xs ${isLegSelected(halfCode.toLowerCase() + '_moneyline', away + ' ML ' + halfCode) ? 'leg-selected' : ''}">
                        ${moneyline.away.odds}
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-green-500/90 text-white px-6 py-3 rounded-lg z-50 font-bold';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
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
