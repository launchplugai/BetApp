# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added (VC-3)
- **Payoff Banner**: "Fix Applied" banner shows after apply-fix flow with before/after signal, fragility, and delta
- **Mini Diff**: Collapsed "See what changed" section showing primary failure and recommendation changes
- **Loop Shortcuts**: Re-Evaluate, Try Another Fix, and Save buttons for quick iteration
- **Numeric Delta**: Prominent delta display in payoff line with styled delta-num class

### Changed (VC-3)
- Builder blocked message updated: "Run an evaluation first to get a recommended fix."
- Loop shortcuts replaced old post-action buttons (eval-action-reeval, eval-action-save)

### Fixed (VC-3, GIT-1)
- Fixed apply-fix endpoint missing imports (get_session_id, get_current_user)
- Fixed apply-fix endpoint using correct NormalizedInput field (input_text not bet_text)
- Fixed apply-fix endpoint building proper evaluation response data

### Tests (VC-3)
- Added TestVC3DeltaPayoff class with 22 tests covering:
  - Payoff banner presence and structure
  - Mini diff presence and structure
  - Loop shortcuts HTML and CSS
  - Blocked builder copy update
  - Delta numeric display
  - Apply-fix endpoint functionality

## [Previous] - VC-2: Builder as Forced Fix
- Builder can only be entered via Fastest Fix CTA
- Fix Mode UI with problem display, delta comparison, single action button
- Apply fix returns to Evaluate with new results

## [Previous] - VC-1: Evaluation Screen Compression
- Compressed layout with PRIMARY FAILURE → FASTEST FIX → DELTA PREVIEW → Details accordion
- Visual hierarchy prioritizing actionable information
