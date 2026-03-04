# DNA Bet Engine - Supported Markets

Full sportsbook market coverage for all major sports.

## NBA Markets

### Main Lines
- **spread** - Full game point spread
- **total** - Full game over/under
- **moneyline** - Full game winner

### Player Props
- **player_points** - Individual player points
- **player_rebounds** - Individual player rebounds
- **player_assists** - Individual player assists
- **player_threes** - Individual player 3-pointers made
- **player_pra** - Points + Rebounds + Assists combo
- **player_specials** - Double-doubles, triple-doubles

### Team Props
- **team_totals** - Team over/under
- **team_quarters** - Team quarterly totals

### Game Props
- **game_props** - Special game events (OT, 10+ threes, etc.)

### Period Betting
- **first_half** / **second_half** - Halves
- **first_quarter** / **second_quarter** / **third_quarter** / **fourth_quarter** - Quarters

## NFL Markets

### Main Lines
- **spread** - Full game point spread
- **total** - Full game over/under
- **moneyline** - Full game winner

### Player Props
- **player_passing_yards** - QB passing yards
- **player_passing_tds** - QB passing touchdowns
- **player_rushing_yards** - Rushing yards
- **player_receiving_yards** - Receiving yards
- **player_anytime_td** - Anytime touchdown scorer
- **player_combos** - Multi-stat combinations

### Team Props
- **team_totals** - Team over/under

### Game Props
- **game_props** - First score, margin, etc.
- **first_team_to_score** - First scoring team
- **winning_margin** - Exact margin ranges

### Period Betting
- **first_half** / **second_half**
- **first_quarter** / **second_quarter**

### Alternate Lines
- **alternate_spread** - Different spreads
- **alternate_total** - Different totals

## NHL Markets

### Main Lines
- **puck_line** - Puck line (spread)
- **total** - Over/under
- **moneyline** - Winner

### Period Betting
- **first_period** / **second_period** / **third_period**

## Market Odds Format

```json
{
  "market": "spread",
  "selections": [
    {
      "label": "Lakers -4.5",
      "line": -4.5,
      "odds": -110
    },
    {
      "label": "Warriors +4.5",
      "line": 4.5,
      "odds": -110
    }
  ]
}
```

### Odds Format
- American odds (-110, +150)
- Negative = favorite (bet $110 to win $100)
- Positive = underdog (bet $100 to win $150)

### Line Types
- **spread**: Point differential (e.g., -4.5, +3.0)
- **total**: Over/under number (e.g., 220.5)
- **moneyline**: No line (null)
- **player props**: Stat threshold (e.g., 27.5 points)
