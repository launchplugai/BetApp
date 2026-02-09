# Page Packet: Builder (`/app?screen=builder`)

## Page Purpose
Primary parlay construction interface. Users select legs from markets, build parlays, and request DNA analysis.

---

## Elements Inventory

### Buttons
| ID | Text | Purpose | Enabled Rules | API Call |
|----|------|---------|---------------|----------|
| back-btn | Arrow left | Navigate back | Always | History.back() |
| more-btn | Three dots | Future menu | Always | None |
| tab-main | MAIN LINES | Switch market | Always | None (client) |
| tab-props | PLAYER PROPS | Switch market | Always | None (client) |
| tab-quarters | QUARTERS | Switch market | Always | None (client) |
| tab-halves | HALVES | Switch market | Always | None (client) |
| spread-home | Line + odds | Add spread leg | Markets loaded | None (client) |
| spread-away | Line + odds | Add spread leg | Markets loaded | None (client) |
| total-over | O + line | Add over leg | Markets loaded | None (client) |
| total-under | U + line | Add under leg | Markets loaded | None (client) |
| ml-home | Odds | Add ML leg | Markets loaded | None (client) |
| ml-away | Odds | Add ML leg | Markets loaded | None (client) |
| quarter-spread-home | Line | Add Q spread | Markets loaded | None (client) |
| quarter-total-home | O line | Add Q total | Markets loaded | None (client) |
| half-spread-home | Line | Add H spread | Markets loaded | None (client) |
| half-total-home | O line | Add H total | Markets loaded | None (client) |
| clear-all | Clear All | Remove all legs | Legs.length > 0 | None (client) |
| analyze-btn | ANALYZE WITH DNA | Get analysis | Legs.length > 0 | POST /app/evaluate |
| submit-btn | SUBMIT BET | Save bet | Legs.length > 0, logged in | POST /api/bets |

### Inputs
| ID | Type | Purpose | Validation |
|----|------|---------|------------|
| wager-input | Number | Bet amount | Min: 1, Max: 100000 |

### Links
| Text | Route | Purpose |
|------|-------|---------|
| Home | /app?screen=dashboard | Navigate home |
| Search | /app?screen=browse | Find games |
| Build | /app?screen=builder | Active (self) |
| My Bets | /app?screen=history | View history |

---

## States

### Loading State
- Game header shows "Loading game..."
- Market content empty or spinner
- Buttons disabled

### Empty State  
- No game selected / no protocol context
- Show: "Select a game to build parlay"
- CTA: Browse games link

### Success State
- Game header populated with teams/score
- Markets loaded with lines
- Legs can be added/removed
- Wager input active
- Analyze button enabled when legs present

### Error State
- Markets failed to load
- Show: "Unable to load markets" + retry button
- Log error to console

### Partial State
- Some markets loaded (main lines OK, props empty)
- Show available markets, hide empty ones
- Don't block entire page

---

## API Calls

### 1. Load Markets
```
GET /api/odds/{gameId}
Request: {gameId: string}
Response: [{market, selections: [{label, line, odds}]}]
Errors: 404 (game not found), 500 (api error)
```

### 2. Analyze Parlay  
```
POST /app/evaluate
Request: {input: string, tier: string, legs: [...]}
Response: {explain: {confidence, summary}, ...}
Errors: 400 (invalid input), 429 (rate limit)
```

### 3. Submit Bet
```
POST /api/bets
Request: {input_text, legs, wager, ...}
Response: {id, status, ...}
Errors: 401 (unauthorized), 400 (validation)
```

---

## Tests Needed

### Unit Tests
- [ ] loadMarkets transforms API response correctly
- [ ] isLegSelected matches quarters/halves correctly
- [ ] addLeg adds to legs array
- [ ] removeLeg removes by index
- [ ] calculateParlayOdds math correct

### Integration Tests
- [ ] Full flow: load game → add leg → analyze → submit
- [ ] Market switching (main → props → quarters → halves)
- [ ] Leg selection persists across tab switches
- [ ] Wager updates payout calculation

### UI Smoke Tests
- [ ] All tabs clickable
- [ ] All buttons add legs
- [ ] Selected legs highlight red
- [ ] Legs appear in slip
- [ ] Analyze button enables with legs

---

## Debug Breadcrumbs

### Console Logs Expected
- "Protocol loaded: {...}"
- "Markets loaded: [...]"
- "Transformed markets: {...}"
- "Leg added: {...}"
- "Leg removed: {index}"

### Session Storage Keys
- `dna_protocol_context` - Current game context
- `dna_auth_token` - JWT for API calls
- `dna_analysis_result` - Last analysis

### Common Failures
1. **No markets** → Check `/api/odds/{gameId}` response
2. **Can't add leg** → Check `addLeg` function, leg structure
3. **No highlight** → Check `isLegSelected` matching logic
4. **Analyze fails** → Check `legs` array format in request

---

## Status

| Check | Status |
|-------|--------|
| Page renders | ✅ |
| All tabs work | ✅ |
| All buttons add legs | ✅ |
| Red highlight works | ✅ |
| API integration | ✅ |
| Tests written | ❌ |
| Contract validation | ❌ |
