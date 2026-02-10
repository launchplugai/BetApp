"""
S19-A: Mock Provider Implementation

Returns hardcoded mock data in normalized canonical format.
Preserves existing mock data behavior.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from app.providers import (
    OddsProvider,
    ScoreProvider,
    Sport,
    Game,
    MarketOdds,
    Selection,
    LiveScore
)


class MockOddsProvider(OddsProvider):
    """Mock odds provider with hardcoded data."""
    
    def get_sports(self) -> List[Sport]:
        """Return available sports (mock data)."""
        return [
            Sport(id="NBA", label="NBA", active=True),
            Sport(id="NFL", label="NFL", active=True),
            Sport(id="NHL", label="NHL", active=True),
            Sport(id="MLB", label="MLB", active=False),
            Sport(id="SOCCER", label="Soccer", active=False),
        ]
    
    def get_games(self, sport: str) -> List[Game]:
        """Return mock games for a sport."""
        if sport.upper() == "NBA":
            return self._get_nba_games()
        elif sport.upper() == "NFL":
            return self._get_nfl_games()
        elif sport.upper() == "NHL":
            return self._get_nhl_games()
        else:
            return []
    
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Return mock odds for a game."""
        # Basic odds for any game
        if "nba" in game_id.lower() or "lal" in game_id.lower():
            return self._get_nba_odds()
        elif "nfl" in game_id.lower() or "chiefs" in game_id.lower():
            return self._get_nfl_odds()
        elif "nhl" in game_id.lower():
            return self._get_nhl_odds()
        else:
            return []
    
    def _get_nba_games(self) -> List[Game]:
        """Mock NBA games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="lal-gsw-2026-02-09",
                league="NBA",
                home="Lakers",
                away="Warriors",
                start_time=(now + timedelta(hours=2)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="mia-bos-2026-02-09",
                league="NBA",
                home="Heat",
                away="Celtics",
                start_time=(now + timedelta(hours=4)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="dal-phx-2026-02-09",
                league="NBA",
                home="Mavericks",
                away="Suns",
                start_time=(now + timedelta(hours=5)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nfl_games(self) -> List[Game]:
        """Mock NFL games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="chiefs-bills-2026-02-09",
                league="NFL",
                home="Chiefs",
                away="Bills",
                start_time=(now + timedelta(hours=3)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nhl_games(self) -> List[Game]:
        """Mock NHL games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="tor-mtl-2026-02-09",
                league="NHL",
                home="Maple Leafs",
                away="Canadiens",
                start_time=(now + timedelta(hours=6)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nba_odds(self) -> List[MarketOdds]:
        """Mock NBA odds - FULL SPORTSBOOK COVERAGE."""
        return [
            # MAIN LINES
            MarketOdds(
                market="spread",
                selections=[
                    Selection(label="Lakers -4.5", line=-4.5, odds=-110),
                    Selection(label="Warriors +4.5", line=4.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 220.5", line=220.5, odds=-110),
                    Selection(label="Under 220.5", line=220.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Lakers ML", line=None, odds=-180),
                    Selection(label="Warriors ML", line=None, odds=+150),
                ]
            ),
            # PLAYER PROPS - POINTS
            MarketOdds(
                market="player_points",
                selections=[
                    Selection(label="LeBron James O27.5 PTS", line=27.5, odds=-110),
                    Selection(label="LeBron James U27.5 PTS", line=27.5, odds=-110),
                    Selection(label="Anthony Davis O23.5 PTS", line=23.5, odds=-110),
                    Selection(label="Anthony Davis U23.5 PTS", line=23.5, odds=-110),
                    Selection(label="Stephen Curry O28.5 PTS", line=28.5, odds=-110),
                    Selection(label="Stephen Curry U28.5 PTS", line=28.5, odds=-110),
                    Selection(label="Austin Reaves O15.5 PTS", line=15.5, odds=-115),
                    Selection(label="Austin Reaves U15.5 PTS", line=15.5, odds=-105),
                    Selection(label="Klay Thompson O18.5 PTS", line=18.5, odds=-110),
                    Selection(label="Klay Thompson U18.5 PTS", line=18.5, odds=-110),
                ]
            ),
            # PLAYER PROPS - REBOUNDS
            MarketOdds(
                market="player_rebounds",
                selections=[
                    Selection(label="LeBron James O7.5 REB", line=7.5, odds=-120),
                    Selection(label="LeBron James U7.5 REB", line=7.5, odds=+100),
                    Selection(label="Anthony Davis O11.5 REB", line=11.5, odds=-130),
                    Selection(label="Anthony Davis U11.5 REB", line=11.5, odds=+110),
                    Selection(label="Stephen Curry O5.5 REB", line=5.5, odds=+120),
                    Selection(label="Stephen Curry U5.5 REB", line=5.5, odds=-140),
                    Selection(label="Draymond Green O8.5 REB", line=8.5, odds=-115),
                    Selection(label="Draymond Green U8.5 REB", line=8.5, odds=-105),
                ]
            ),
            # PLAYER PROPS - ASSISTS
            MarketOdds(
                market="player_assists",
                selections=[
                    Selection(label="LeBron James O8.5 AST", line=8.5, odds=-115),
                    Selection(label="LeBron James U8.5 AST", line=8.5, odds=-105),
                    Selection(label="Stephen Curry O6.5 AST", line=6.5, odds=-125),
                    Selection(label="Stephen Curry U6.5 AST", line=6.5, odds=+105),
                    Selection(label="Draymond Green O7.5 AST", line=7.5, odds=-110),
                    Selection(label="Draymond Green U7.5 AST", line=7.5, odds=-110),
                    Selection(label="Austin Reaves O5.5 AST", line=5.5, odds=+100),
                    Selection(label="Austin Reaves U5.5 AST", line=5.5, odds=-120),
                ]
            ),
            # PLAYER PROPS - THREES
            MarketOdds(
                market="player_threes",
                selections=[
                    Selection(label="Stephen Curry O4.5 3PM", line=4.5, odds=-130),
                    Selection(label="Stephen Curry U4.5 3PM", line=4.5, odds=+110),
                    Selection(label="Klay Thompson O3.5 3PM", line=3.5, odds=-115),
                    Selection(label="Klay Thompson U3.5 3PM", line=3.5, odds=-105),
                    Selection(label="LeBron James O2.5 3PM", line=2.5, odds=+120),
                    Selection(label="LeBron James U2.5 3PM", line=2.5, odds=-140),
                    Selection(label="Austin Reaves O2.5 3PM", line=2.5, odds=+100),
                    Selection(label="Austin Reaves U2.5 3PM", line=2.5, odds=-120),
                ]
            ),
            # PLAYER PROPS - COMBOS (PTS+REB+AST)
            MarketOdds(
                market="player_pra",
                selections=[
                    Selection(label="LeBron James O42.5 PRA", line=42.5, odds=-115),
                    Selection(label="LeBron James U42.5 PRA", line=42.5, odds=-105),
                    Selection(label="Anthony Davis O38.5 PRA", line=38.5, odds=-110),
                    Selection(label="Anthony Davis U38.5 PRA", line=38.5, odds=-110),
                    Selection(label="Stephen Curry O38.5 PRA", line=38.5, odds=-120),
                    Selection(label="Stephen Curry U38.5 PRA", line=38.5, odds=+100),
                ]
            ),
            # PLAYER PROPS - DOUBLE-DOUBLE / TRIPLE-DOUBLE
            MarketOdds(
                market="player_specials",
                selections=[
                    Selection(label="LeBron James Double-Double", line=None, odds=-160),
                    Selection(label="LeBron James Triple-Double", line=None, odds=+280),
                    Selection(label="Anthony Davis Double-Double", line=None, odds=-200),
                    Selection(label="Anthony Davis Triple-Double", line=None, odds=+450),
                    Selection(label="Draymond Green Double-Double", line=None, odds=+140),
                    Selection(label="Draymond Green Triple-Double", line=None, odds=+600),
                ]
            ),
            # TEAM PROPS
            MarketOdds(
                market="team_totals",
                selections=[
                    Selection(label="Lakers O112.5", line=112.5, odds=-110),
                    Selection(label="Lakers U112.5", line=112.5, odds=-110),
                    Selection(label="Warriors O108.5", line=108.5, odds=-110),
                    Selection(label="Warriors U108.5", line=108.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="team_quarters",
                selections=[
                    Selection(label="Lakers 1Q O28.5", line=28.5, odds=-115),
                    Selection(label="Lakers 1Q U28.5", line=28.5, odds=-105),
                    Selection(label="Warriors 1Q O27.5", line=27.5, odds=-110),
                    Selection(label="Warriors 1Q U27.5", line=27.5, odds=-110),
                ]
            ),
            # GAME PROPS
            MarketOdds(
                market="game_props",
                selections=[
                    Selection(label="Yes - Either Team 10+ 3PM", line=None, odds=-280),
                    Selection(label="No - Either Team 10+ 3PM", line=None, odds=+220),
                    Selection(label="Yes - Game Goes to OT", line=None, odds=+1100),
                    Selection(label="No - Game Goes to OT", line=None, odds=-2200),
                    Selection(label="Highest Scoring Quarter: 1st", line=None, odds=+275),
                    Selection(label="Highest Scoring Quarter: 2nd", line=None, odds=+240),
                    Selection(label="Highest Scoring Quarter: 3rd", line=None, odds=+275),
                    Selection(label="Highest Scoring Quarter: 4th", line=None, odds=+185),
                ]
            ),
            # HALVES
            MarketOdds(
                market="first_half",
                selections=[
                    Selection(label="1H Lakers -2.5", line=-2.5, odds=-110),
                    Selection(label="1H Warriors +2.5", line=2.5, odds=-110),
                    Selection(label="1H Over 110.5", line=110.5, odds=-110),
                    Selection(label="1H Under 110.5", line=110.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="second_half",
                selections=[
                    Selection(label="2H Lakers -2.0", line=-2.0, odds=-110),
                    Selection(label="2H Warriors +2.0", line=2.0, odds=-110),
                    Selection(label="2H Over 110.0", line=110.0, odds=-110),
                    Selection(label="2H Under 110.0", line=110.0, odds=-110),
                ]
            ),
            # QUARTERS
            MarketOdds(
                market="first_quarter",
                selections=[
                    Selection(label="1Q Lakers -1.5", line=-1.5, odds=-115),
                    Selection(label="1Q Warriors +1.5", line=1.5, odds=-105),
                    Selection(label="1Q Over 56.5", line=56.5, odds=-110),
                    Selection(label="1Q Under 56.5", line=56.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="second_quarter",
                selections=[
                    Selection(label="2Q Lakers -1.0", line=-1.0, odds=-110),
                    Selection(label="2Q Warriors +1.0", line=1.0, odds=-110),
                    Selection(label="2Q Over 55.5", line=55.5, odds=-110),
                    Selection(label="2Q Under 55.5", line=55.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="third_quarter",
                selections=[
                    Selection(label="3Q Lakers -1.5", line=-1.5, odds=-115),
                    Selection(label="3Q Warriors +1.5", line=1.5, odds=-105),
                    Selection(label="3Q Over 56.0", line=56.0, odds=-110),
                    Selection(label="3Q Under 56.0", line=56.0, odds=-110),
                ]
            ),
            MarketOdds(
                market="fourth_quarter",
                selections=[
                    Selection(label="4Q Lakers -1.0", line=-1.0, odds=-110),
                    Selection(label="4Q Warriors +1.0", line=1.0, odds=-110),
                    Selection(label="4Q Over 56.5", line=56.5, odds=-110),
                    Selection(label="4Q Under 56.5", line=56.5, odds=-110),
                ]
            ),
        ]
    
    def _get_nfl_odds(self) -> List[MarketOdds]:
        """Mock NFL odds - FULL SPORTSBOOK COVERAGE."""
        return [
            # MAIN LINES
            MarketOdds(
                market="spread",
                selections=[
                    Selection(label="Chiefs -3.0", line=-3.0, odds=-110),
                    Selection(label="Bills +3.0", line=3.0, odds=-110),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 48.5", line=48.5, odds=-110),
                    Selection(label="Under 48.5", line=48.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Chiefs ML", line=None, odds=-150),
                    Selection(label="Bills ML", line=None, odds=+130),
                ]
            ),
            # PLAYER PROPS - PASSING
            MarketOdds(
                market="player_passing_yards",
                selections=[
                    Selection(label="Patrick Mahomes O275.5 PY", line=275.5, odds=-110),
                    Selection(label="Patrick Mahomes U275.5 PY", line=275.5, odds=-110),
                    Selection(label="Josh Allen O260.5 PY", line=260.5, odds=-110),
                    Selection(label="Josh Allen U260.5 PY", line=260.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="player_passing_tds",
                selections=[
                    Selection(label="Patrick Mahomes O2.5 TD", line=2.5, odds=-140),
                    Selection(label="Patrick Mahomes U2.5 TD", line=2.5, odds=+120),
                    Selection(label="Josh Allen O1.5 TD", line=1.5, odds=-160),
                    Selection(label="Josh Allen U1.5 TD", line=1.5, odds=+140),
                ]
            ),
            # PLAYER PROPS - RUSHING
            MarketOdds(
                market="player_rushing_yards",
                selections=[
                    Selection(label="Josh Allen O45.5 RY", line=45.5, odds=-110),
                    Selection(label="Josh Allen U45.5 RY", line=45.5, odds=-110),
                    Selection(label="Isiah Pacheco O65.5 RY", line=65.5, odds=-110),
                    Selection(label="Isiah Pacheco U65.5 RY", line=65.5, odds=-110),
                    Selection(label="James Cook O42.5 RY", line=42.5, odds=-110),
                    Selection(label="James Cook U42.5 RY", line=42.5, odds=-110),
                ]
            ),
            # PLAYER PROPS - RECEIVING
            MarketOdds(
                market="player_receiving_yards",
                selections=[
                    Selection(label="Travis Kelce O72.5 REC", line=72.5, odds=-110),
                    Selection(label="Travis Kelce U72.5 REC", line=72.5, odds=-110),
                    Selection(label="Stefon Diggs O78.5 REC", line=78.5, odds=-110),
                    Selection(label="Stefon Diggs U78.5 REC", line=78.5, odds=-110),
                    Selection(label="Rashee Rice O55.5 REC", line=55.5, odds=-110),
                    Selection(label="Rashee Rice U55.5 REC", line=55.5, odds=-110),
                ]
            ),
            # PLAYER PROPS - ANYTIME TD
            MarketOdds(
                market="player_anytime_td",
                selections=[
                    Selection(label="Travis Kelce Anytime TD", line=None, odds=-115),
                    Selection(label="Stefon Diggs Anytime TD", line=None, odds=+100),
                    Selection(label="Isiah Pacheco Anytime TD", line=None, odds=+120),
                    Selection(label="Josh Allen Anytime TD", line=None, odds=+200),
                ]
            ),
            # PLAYER PROPS - COMBOS
            MarketOdds(
                market="player_combos",
                selections=[
                    Selection(label="Mahomes 250+ PY + 2+ TD", line=None, odds=-130),
                    Selection(label="Allen 200+ PY + 1+ TD", line=None, odds=-150),
                ]
            ),
            # TEAM PROPS
            MarketOdds(
                market="team_totals",
                selections=[
                    Selection(label="Chiefs O25.5", line=25.5, odds=-110),
                    Selection(label="Chiefs U25.5", line=25.5, odds=-110),
                    Selection(label="Bills O22.5", line=22.5, odds=-110),
                    Selection(label="Bills U22.5", line=22.5, odds=-110),
                ]
            ),
            # GAME PROPS
            MarketOdds(
                market="game_props",
                selections=[
                    Selection(label="Yes - First Score TD", line=None, odds=-220),
                    Selection(label="No - First Score TD (FG/Safety)", line=None, odds=+180),
                    Selection(label="Yes - Either Team 2+ TD in 1Q", line=None, odds=+260),
                    Selection(label="Yes - Game Decided by 3pts or Less", line=None, odds=+340),
                    Selection(label="Yes - OT Required", line=None, odds=+900),
                ]
            ),
            MarketOdds(
                market="first_team_to_score",
                selections=[
                    Selection(label="Chiefs First Score", line=None, odds=-130),
                    Selection(label="Bills First Score", line=None, odds=+110),
                ]
            ),
            MarketOdds(
                market="winning_margin",
                selections=[
                    Selection(label="Chiefs 1-6 pts", line=None, odds=+360),
                    Selection(label="Chiefs 7-12 pts", line=None, odds=+480),
                    Selection(label="Chiefs 13+ pts", line=None, odds=+550),
                    Selection(label="Bills 1-6 pts", line=None, odds=+400),
                    Selection(label="Bills 7-12 pts", line=None, odds=+600),
                    Selection(label="Bills 13+ pts", line=None, odds=+800),
                ]
            ),
            # HALVES
            MarketOdds(
                market="first_half",
                selections=[
                    Selection(label="1H Chiefs -1.5", line=-1.5, odds=-110),
                    Selection(label="1H Bills +1.5", line=1.5, odds=-110),
                    Selection(label="1H Over 24.5", line=24.5, odds=-110),
                    Selection(label="1H Under 24.5", line=24.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="second_half",
                selections=[
                    Selection(label="2H Chiefs -1.5", line=-1.5, odds=-110),
                    Selection(label="2H Bills +1.5", line=1.5, odds=-110),
                    Selection(label="2H Over 24.0", line=24.0, odds=-110),
                    Selection(label="2H Under 24.0", line=24.0, odds=-110),
                ]
            ),
            # QUARTERS
            MarketOdds(
                market="first_quarter",
                selections=[
                    Selection(label="1Q Chiefs -0.5", line=-0.5, odds=-115),
                    Selection(label="1Q Bills +0.5", line=0.5, odds=-105),
                    Selection(label="1Q Over 10.5", line=10.5, odds=-110),
                    Selection(label="1Q Under 10.5", line=10.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="second_quarter",
                selections=[
                    Selection(label="2Q Chiefs -0.5", line=-0.5, odds=-110),
                    Selection(label="2Q Bills +0.5", line=0.5, odds=-110),
                    Selection(label="2Q Over 11.0", line=11.0, odds=-110),
                    Selection(label="2Q Under 11.0", line=11.0, odds=-110),
                ]
            ),
            # ALTERNATE LINES
            MarketOdds(
                market="alternate_spread",
                selections=[
                    Selection(label="Chiefs -7.5", line=-7.5, odds=+180),
                    Selection(label="Chiefs -10.5", line=-10.5, odds=+280),
                    Selection(label="Bills +7.5", line=7.5, odds=-220),
                    Selection(label="Bills +10.5", line=10.5, odds=-320),
                ]
            ),
            MarketOdds(
                market="alternate_total",
                selections=[
                    Selection(label="Over 41.5", line=41.5, odds=-160),
                    Selection(label="Over 55.5", line=55.5, odds=+140),
                    Selection(label="Under 41.5", line=41.5, odds=+140),
                    Selection(label="Under 55.5", line=55.5, odds=-160),
                ]
            ),
        ]
    
    def _get_nhl_odds(self) -> List[MarketOdds]:
        """Mock NHL odds."""
        return [
            MarketOdds(
                market="puck_line",
                selections=[
                    Selection(label="Maple Leafs -1.5", line=-1.5, odds=+140),
                    Selection(label="Canadiens +1.5", line=1.5, odds=-170),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 6.5", line=6.5, odds=-115),
                    Selection(label="Under 6.5", line=6.5, odds=-105),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Maple Leafs ML", line=None, odds=-130),
                    Selection(label="Canadiens ML", line=None, odds=+110),
                ]
            ),
        ]


class MockScoreProvider(ScoreProvider):
    """Mock score provider with live game simulation."""
    
    def get_score(self, game_id: str) -> Optional[LiveScore]:
        """Return mock live score."""
        # Only return score for "live" games (mock simulation)
        if "lal" in game_id.lower():
            return LiveScore(
                game_id=game_id,
                home_score=102,
                away_score=98,
                period="4th",
                clock="5:23",
                status="LIVE"
            )
        
        # Return None for games that aren't "live"
        return None
