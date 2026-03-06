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
            Sport(id="MLB", label="MLB", active=True),
            Sport(id="SOCCER", label="Soccer", active=True),
            Sport(id="UFC", label="UFC", active=True),
            Sport(id="TENNIS", label="Tennis", active=True),
        ]
    
    def get_games(self, sport: str) -> List[Game]:
        """Return mock games for a sport."""
        if sport.upper() == "NBA":
            return self._get_nba_games()
        elif sport.upper() == "NFL":
            return self._get_nfl_games()
        elif sport.upper() == "NHL":
            return self._get_nhl_games()
        elif sport.upper() == "MLB":
            return self._get_mlb_games()
        elif sport.upper() == "SOCCER":
            return self._get_soccer_games()
        elif sport.upper() == "UFC":
            return self._get_ufc_games()
        elif sport.upper() == "TENNIS":
            return self._get_tennis_games()
        else:
            return []
    
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Return mock odds for a game."""
        game_lower = game_id.lower()
        if "nba" in game_lower or "lal" in game_lower or "mia" in game_lower or "dal" in game_lower:
            return self._get_nba_odds()
        elif "nfl" in game_lower or "chiefs" in game_lower or "eagles" in game_lower:
            return self._get_nfl_odds()
        elif "nhl" in game_lower or "leafs" in game_lower or "bruins" in game_lower:
            return self._get_nhl_odds()
        elif "mlb" in game_lower or "yankees" in game_lower or "dodgers" in game_lower:
            return self._get_mlb_odds()
        elif "soccer" in game_lower or "epl" in game_lower or "laliga" in game_lower:
            return self._get_soccer_odds()
        elif "ufc" in game_lower or "fight" in game_lower:
            return self._get_ufc_odds()
        elif "tennis" in game_lower or "wimbledon" in game_lower:
            return self._get_tennis_odds()
        else:
            return []
    
    def _get_nba_games(self) -> List[Game]:
        """Mock NBA games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="nba-lal-gsw-tonight",
                league="NBA",
                home="Lakers",
                away="Warriors",
                start_time=(now + timedelta(hours=2)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="nba-mia-bos-tonight",
                league="NBA",
                home="Heat",
                away="Celtics",
                start_time=(now + timedelta(hours=4)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="nba-dal-phx-tonight",
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
                id="nfl-kc-buf-tonight",
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
                id="nhl-tor-mtl-tonight",
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
        """Mock NHL odds - FULL SPORTSBOOK COVERAGE."""
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
            MarketOdds(
                market="player_points",
                selections=[
                    Selection(label="Auston Matthews O0.5 PTS", line=0.5, odds=-160),
                    Selection(label="Auston Matthews U0.5 PTS", line=0.5, odds=+140),
                    Selection(label="Cole Caufield O0.5 PTS", line=0.5, odds=-130),
                    Selection(label="Cole Caufield U0.5 PTS", line=0.5, odds=+110),
                ]
            ),
            MarketOdds(
                market="player_shots",
                selections=[
                    Selection(label="Auston Matthews O3.5 SOG", line=3.5, odds=-120),
                    Selection(label="Auston Matthews U3.5 SOG", line=3.5, odds=+100),
                    Selection(label="William Nylander O2.5 SOG", line=2.5, odds=-140),
                    Selection(label="William Nylander U2.5 SOG", line=2.5, odds=+120),
                ]
            ),
            MarketOdds(
                market="goalie_saves",
                selections=[
                    Selection(label="Ilya Samsonov O28.5 Saves", line=28.5, odds=-110),
                    Selection(label="Ilya Samsonov U28.5 Saves", line=28.5, odds=-110),
                    Selection(label="Sam Montembeault O27.5 Saves", line=27.5, odds=-110),
                    Selection(label="Sam Montembeault U27.5 Saves", line=27.5, odds=-110),
                ]
            ),
        ]
    
    def _get_mlb_games(self) -> List[Game]:
        """Mock MLB games."""
        now = datetime.utcnow()
        return [
            Game(id="mlb-nyy-bos-tonight", league="MLB", home="Yankees", away="Red Sox", start_time=(now + timedelta(hours=3)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="mlb-lad-sf-tonight", league="MLB", home="Dodgers", away="Giants", start_time=(now + timedelta(hours=4)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="mlb-hou-tex-tonight", league="MLB", home="Astros", away="Rangers", start_time=(now + timedelta(hours=5)).isoformat() + "Z", status="SCHEDULED"),
        ]
    
    def _get_mlb_odds(self) -> List[MarketOdds]:
        """Mock MLB odds - FULL COVERAGE."""
        return [
            MarketOdds(market="moneyline", selections=[Selection(label="Yankees ML", line=None, odds=-140), Selection(label="Red Sox ML", line=None, odds=+120)]),
            MarketOdds(market="run_line", selections=[Selection(label="Yankees -1.5", line=-1.5, odds=+130), Selection(label="Red Sox +1.5", line=1.5, odds=-150)]),
            MarketOdds(market="total", selections=[Selection(label="Over 8.5", line=8.5, odds=-110), Selection(label="Under 8.5", line=8.5, odds=-110)]),
            MarketOdds(market="first_five_ml", selections=[Selection(label="F5 Yankees ML", line=None, odds=-130), Selection(label="F5 Red Sox ML", line=None, odds=+110)]),
            MarketOdds(market="first_five_total", selections=[Selection(label="F5 Over 4.5", line=4.5, odds=-110), Selection(label="F5 Under 4.5", line=4.5, odds=-110)]),
            MarketOdds(market="pitcher_strikeouts", selections=[Selection(label="Gerrit Cole O6.5 Ks", line=6.5, odds=-115), Selection(label="Gerrit Cole U6.5 Ks", line=6.5, odds=-105)]),
            MarketOdds(market="pitcher_outs", selections=[Selection(label="Cole O17.5 Outs", line=17.5, odds=-120), Selection(label="Cole U17.5 Outs", line=17.5, odds=+100)]),
            MarketOdds(market="batter_hits", selections=[Selection(label="Aaron Judge O1.5 Hits", line=1.5, odds=+120), Selection(label="Aaron Judge U1.5 Hits", line=1.5, odds=-140)]),
            MarketOdds(market="batter_home_runs", selections=[Selection(label="Judge Anytime HR", line=None, odds=+240), Selection(label="Devers Anytime HR", line=None, odds=+320)]),
            MarketOdds(market="batter_rbis", selections=[Selection(label="Judge O0.5 RBI", line=0.5, odds=-110), Selection(label="Judge U0.5 RBI", line=0.5, odds=-110)]),
            MarketOdds(market="team_total", selections=[Selection(label="Yankees O4.5", line=4.5, odds=-110), Selection(label="Yankees U4.5", line=4.5, odds=-110)]),
        ]
    
    def _get_soccer_games(self) -> List[Game]:
        """Mock Soccer games."""
        now = datetime.utcnow()
        return [
            Game(id="epl-mci-liv-tonight", league="EPL", home="Man City", away="Liverpool", start_time=(now + timedelta(hours=2)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="laliga-rm-bar-tonight", league="La Liga", home="Real Madrid", away="Barcelona", start_time=(now + timedelta(hours=4)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="ucl-bay-psg-tonight", league="UCL", home="Bayern", away="PSG", start_time=(now + timedelta(hours=6)).isoformat() + "Z", status="SCHEDULED"),
        ]
    
    def _get_soccer_odds(self) -> List[MarketOdds]:
        """Mock Soccer odds - FULL COVERAGE."""
        return [
            MarketOdds(market="moneyline", selections=[Selection(label="Man City ML", line=None, odds=-130), Selection(label="Liverpool ML", line=None, odds=+280), Selection(label="Draw", line=None, odds=+280)]),
            MarketOdds(market="spread", selections=[Selection(label="Man City -1.0", line=-1.0, odds=+120), Selection(label="Liverpool +1.0", line=1.0, odds=-140)]),
            MarketOdds(market="total", selections=[Selection(label="Over 2.5", line=2.5, odds=-120), Selection(label="Under 2.5", line=2.5, odds=+100)]),
            MarketOdds(market="both_teams_to_score", selections=[Selection(label="BTTS Yes", line=None, odds=-140), Selection(label="BTTS No", line=None, odds=+120)]),
            MarketOdds(market="first_half_ml", selections=[Selection(label="1H City", line=None, odds=-110), Selection(label="1H Liverpool", line=None, odds=+350), Selection(label="1H Draw", line=None, odds=+130)]),
            MarketOdds(market="first_half_total", selections=[Selection(label="1H Over 1.0", line=1.0, odds=-130), Selection(label="1H Under 1.0", line=1.0, odds=+110)]),
            MarketOdds(market="player_goals", selections=[Selection(label="Haaland Anytime Goal", line=None, odds=-140), Selection(label="Salah Anytime Goal", line=None, odds=+160)]),
            MarketOdds(market="player_shots", selections=[Selection(label="Haaland O3.5 Shots", line=3.5, odds=-110), Selection(label="Haaland U3.5 Shots", line=3.5, odds=-110)]),
            MarketOdds(market="corners", selections=[Selection(label="Over 9.5 Corners", line=9.5, odds=-110), Selection(label="Under 9.5 Corners", line=9.5, odds=-110)]),
            MarketOdds(market="cards", selections=[Selection(label="Over 3.5 Cards", line=3.5, odds=+100), Selection(label="Under 3.5 Cards", line=3.5, odds=-120)]),
            MarketOdds(market="correct_score", selections=[Selection(label="1-0 City", line=None, odds=+650), Selection(label="2-1 City", line=None, odds=+800), Selection(label="1-1 Draw", line=None, odds=+600)]),
        ]
    
    def _get_ufc_games(self) -> List[Game]:
        """Mock UFC fights."""
        now = datetime.utcnow()
        return [
            Game(id="ufc-main-001", league="UFC", home="Islam Makhachev", away="Charles Oliveira", start_time=(now + timedelta(hours=6)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="ufc-co-001", league="UFC", home="Sean O'Malley", away="Marlon Vera", start_time=(now + timedelta(hours=4)).isoformat() + "Z", status="SCHEDULED"),
        ]
    
    def _get_ufc_odds(self) -> List[MarketOdds]:
        """Mock UFC odds - FULL COVERAGE."""
        return [
            MarketOdds(market="moneyline", selections=[Selection(label="Makhachev ML", line=None, odds=-280), Selection(label="Oliveira ML", line=None, odds=+220)]),
            MarketOdds(market="method_of_victory", selections=[Selection(label="Makhachev KO/TKO", line=None, odds=+350), Selection(label="Makhachev Submission", line=None, odds=+220), Selection(label="Makhachev Decision", line=None, odds=+240)]),
            MarketOdds(market="round_betting", selections=[Selection(label="Makhachev R1", line=None, odds=+450), Selection(label="Makhachev R2", line=None, odds=+550), Selection(label="Over 2.5 Rounds", line=2.5, odds=-140)]),
            MarketOdds(market="total_rounds", selections=[Selection(label="Over 1.5 Rounds", line=1.5, odds=-180), Selection(label="Under 1.5 Rounds", line=1.5, odds=+150)]),
            MarketOdds(market="fight_to_go_distance", selections=[Selection(label="Yes - Goes Distance", line=None, odds=+140), Selection(label="No - Ends Early", line=None, odds=-160)]),
        ]
    
    def _get_tennis_games(self) -> List[Game]:
        """Mock Tennis matches."""
        now = datetime.utcnow()
        return [
            Game(id="wimbledon-m-001", league="Wimbledon", home="Carlos Alcaraz", away="Novak Djokovic", start_time=(now + timedelta(hours=5)).isoformat() + "Z", status="SCHEDULED"),
            Game(id="uso-w-001", league="US Open", home="Iga Swiatek", away="Coco Gauff", start_time=(now + timedelta(hours=3)).isoformat() + "Z", status="SCHEDULED"),
        ]
    
    def _get_tennis_odds(self) -> List[MarketOdds]:
        """Mock Tennis odds - FULL COVERAGE."""
        return [
            MarketOdds(market="moneyline", selections=[Selection(label="Alcaraz ML", line=None, odds=-160), Selection(label="Djokovic ML", line=None, odds=+140)]),
            MarketOdds(market="set_spread", selections=[Selection(label="Alcaraz -1.5 Sets", line=-1.5, odds=+120), Selection(label="Djokovic +1.5 Sets", line=1.5, odds=-140)]),
            MarketOdds(market="total_games", selections=[Selection(label="Over 38.5 Games", line=38.5, odds=-110), Selection(label="Under 38.5 Games", line=38.5, odds=-110)]),
            MarketOdds(market="set_1_winner", selections=[Selection(label="Alcaraz S1", line=None, odds=-130), Selection(label="Djokovic S1", line=None, odds=+110)]),
            MarketOdds(market="exact_sets", selections=[Selection(label="3-0 Alcaraz", line=None, odds=+280), Selection(label="3-1 Alcaraz", line=None, odds=+320), Selection(label="3-2 Either", line=None, odds=+450)]),
            MarketOdds(market="total_sets", selections=[Selection(label="Over 3.5 Sets", line=3.5, odds=+140), Selection(label="Under 3.5 Sets", line=3.5, odds=-160)]),
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
