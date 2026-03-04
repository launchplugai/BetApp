# Bug Report: Builder Blank Page

## Issue
Users experiencing blank/black page when navigating to `/app?screen=builder`

## Root Cause
Invalid `dna_protocol_context` stored in `sessionStorage` with malformed game IDs like:
- `lal-gsw-2026-02-09` (mock NBA format, not real API format)
- Missing sport prefix or `-at-` separator

When builder loaded invalid protocol and called `/api/odds/{invalid_game_id}`,
API returned 404 → JavaScript error → blank page.

## Error Chain
1. Old code stored mock game IDs in sessionStorage
2. Builder loaded invalid protocol data
3. `loadMarkets()` called with invalid game ID
4. API returned 404 for `/api/odds/lal-gsw-2026-02-09`
5. No error handling → JS execution stopped → blank page

## Fix Applied
Commit: `4f53177`

### Changes
1. **Protocol validation** - Validate stored protocol before use:
   ```javascript
   if (gameId && gameId.includes('-at-') && gameId.startsWith('nhl-')) {
       // Use stored protocol
   } else {
       // Clear invalid data, fetch fresh
   }
   ```

2. **Auto-clear invalid data** - Remove bad sessionStorage automatically

3. **Error handling** - Wrap init in try/catch with user-friendly error display:
   ```javascript
   try {
       await loadProtocol();
       await loadMarkets();
       renderGameHeader();
       renderMarket();
       renderLegs();
   } catch (error) {
       // Show reload button instead of blank page
   }
   ```

## Prevention Measures
- [x] Validate all sessionStorage data before use
- [x] Add global error boundary for builder initialization
- [x] Clear invalid data automatically
- [ ] Add Sentry or similar for client-side error tracking
- [ ] Add e2e test for builder loading with invalid protocol

## Testing
- [x] Builder loads with valid protocol
- [x] Builder auto-recovers from invalid protocol
- [x] Error display shows on complete failure
- [ ] Test on mobile browsers
