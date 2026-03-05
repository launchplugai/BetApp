"""
NBA Data Ingestion Service

Fetches data from nba_api and populates database.
Industry-standard ETL pattern.
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv2,
    commonteamroster,
    commonplayerinfo,
    scoreboardv2,
    leaguestandings
)
from nba_api.stats.static import teams as nba_teams, players as nba_players

from app.nba.models import (
    DimTeam, DimPlayer, DimGame, DimSeason,
    FactBoxScore, FactTeamBoxScore,
    ContextInjury, ContextRestDays, ContextPlayoffStandings
)

logger = logging.getLogger(__name__)


class NBADataIngestion:
    """Main data ingestion service."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # =========================================================================
    # DIMENSION TABLES (Initial Load)
    # =========================================================================
    
    def sync_teams(self) -> int:
        """
        Sync all NBA teams from static data.
        Returns count of teams synced.
        """
        logger.info("Syncing NBA teams...")
        
        teams_data = nba_teams.get_teams()
        count = 0
        
        for team_data in teams_data:
            team = self.db.query(DimTeam).filter_by(
                team_id=team_data['id']
            ).first()
            
            if not team:
                team = DimTeam(
                    team_id=team_data['id'],
                    abbreviation=team_data['abbreviation'],
                    nickname=team_data['nickname'],
                    city=team_data['city'],
                    full_name=team_data['full_name'],
                    active=True
                )
                self.db.add(team)
                count += 1
            else:
                # Update active teams
                team.abbreviation = team_data['abbreviation']
                team.nickname = team_data['nickname']
                team.city = team_data['city']
                team.full_name = team_data['full_name']
                team.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Synced {count} new teams")
        return count
    
    def sync_players(self, active_only: bool = True) -> int:
        """
        Sync all NBA players from static data.
        Returns count of players synced.
        """
        logger.info("Syncing NBA players...")
        
        players_data = nba_players.get_players()
        if active_only:
            players_data = nba_players.get_active_players()
        
        count = 0
        
        for player_data in players_data:
            player = self.db.query(DimPlayer).filter_by(
                player_id=player_data['id']
            ).first()
            
            photo_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_data['id']}.png"

            if not player:
                player = DimPlayer(
                    player_id=player_data['id'],
                    first_name=player_data.get('first_name', ''),
                    last_name=player_data.get('last_name', ''),
                    full_name=player_data.get('full_name', ''),
                    active=player_data.get('is_active', True),
                    photo_url=photo_url
                )
                self.db.add(player)
                count += 1
            else:
                player.active = player_data.get('is_active', True)
                player.photo_url = photo_url
                player.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Synced {count} new players")
        return count
    
    # =========================================================================
    # GAMES & BOX SCORES (Daily ETL)
    # =========================================================================
    
    def fetch_games_for_date(self, game_date: date, retries: int = 3) -> List[Dict]:
        """Fetch all games for a specific date with retry logic."""
        logger.info(f"Fetching games for {game_date}")
        
        for attempt in range(retries):
            try:
                scoreboard = scoreboardv2.ScoreboardV2(
                    game_date=game_date.strftime("%Y-%m-%d"),
                    timeout=60
                )
                games = scoreboard.get_normalized_dict()['GameHeader']
                logger.info(f"Fetched {len(games)} games")
                return games
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All retries failed for {game_date}")
                    raise
    
    def ingest_game(self, game_data: Dict, season: str) -> DimGame:
        """
        Ingest a single game into dim_games.
        Returns the DimGame object.
        """
        game_id = game_data['GAME_ID']
        
        # Check if already exists
        game = self.db.query(DimGame).filter_by(game_id=game_id).first()
        
        if not game:
            game = DimGame(
                game_id=game_id,
                game_date=datetime.strptime(
                    str(game_data['GAME_DATE_EST']), 
                    "%Y-%m-%d"
                ).date(),
                season=season,
                season_type=game_data.get('SEASON_STAGE_ID', 1),  # 1=reg, 2=playoffs
                home_team_id=game_data['HOME_TEAM_ID'],
                away_team_id=game_data['VISITOR_TEAM_ID'],
                home_score=game_data.get('HOME_TEAM_POINTS'),
                away_score=game_data.get('VISITOR_TEAM_POINTS'),
                status=self._parse_game_status(game_data.get('GAME_STATUS_TEXT'))
            )
            self.db.add(game)
        else:
            # Update if status changed
            game.home_score = game_data.get('HOME_TEAM_POINTS')
            game.away_score = game_data.get('VISITOR_TEAM_POINTS')
            game.status = self._parse_game_status(game_data.get('GAME_STATUS_TEXT'))
            game.updated_at = datetime.utcnow()
        
        self.db.commit()
        return game
    
    def ingest_box_scores(self, game_id: str) -> int:
        """
        Ingest player and team box scores for a game.
        Returns count of box scores ingested.
        """
        logger.info(f"Ingesting box scores for game {game_id}")
        
        try:
            boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
                game_id=game_id
            )
            
            player_stats = boxscore.get_normalized_dict()['PlayerStats']
            team_stats = boxscore.get_normalized_dict()['TeamStats']
            
            count = 0
            
            # Ingest player stats
            for player_data in player_stats:
                box = self.db.query(FactBoxScore).filter_by(
                    game_id=game_id,
                    player_id=player_data['PLAYER_ID']
                ).first()
                
                if not box:
                    box = FactBoxScore(
                        game_id=game_id,
                        player_id=player_data['PLAYER_ID'],
                        team_id=player_data['TEAM_ID'],
                        started=(player_data.get('START_POSITION') is not None),
                        minutes=self._parse_minutes(player_data.get('MIN')),
                        points=player_data.get('PTS', 0),
                        rebounds=player_data.get('REB', 0),
                        assists=player_data.get('AST', 0),
                        steals=player_data.get('STL', 0),
                        blocks=player_data.get('BLK', 0),
                        turnovers=player_data.get('TO', 0),
                        fouls=player_data.get('PF', 0),
                        fgm=player_data.get('FGM', 0),
                        fga=player_data.get('FGA', 0),
                        fg_pct=player_data.get('FG_PCT'),
                        fg3m=player_data.get('FG3M', 0),
                        fg3a=player_data.get('FG3A', 0),
                        fg3_pct=player_data.get('FG3_PCT'),
                        ftm=player_data.get('FTM', 0),
                        fta=player_data.get('FTA', 0),
                        ft_pct=player_data.get('FT_PCT'),
                        plus_minus=player_data.get('PLUS_MINUS')
                    )
                    self.db.add(box)
                    count += 1
            
            # Ingest team stats
            for team_data in team_stats:
                team_box = self.db.query(FactTeamBoxScore).filter_by(
                    game_id=game_id,
                    team_id=team_data['TEAM_ID']
                ).first()
                
                if not team_box:
                    # Determine if home team
                    game = self.db.query(DimGame).filter_by(game_id=game_id).first()
                    is_home = (team_data['TEAM_ID'] == game.home_team_id)
                    
                    team_box = FactTeamBoxScore(
                        game_id=game_id,
                        team_id=team_data['TEAM_ID'],
                        is_home=is_home,
                        points=team_data.get('PTS', 0),
                        fgm=team_data.get('FGM', 0),
                        fga=team_data.get('FGA', 0),
                        fg_pct=team_data.get('FG_PCT'),
                        fg3m=team_data.get('FG3M', 0),
                        fg3a=team_data.get('FG3A', 0),
                        fg3_pct=team_data.get('FG3_PCT'),
                        ftm=team_data.get('FTM', 0),
                        fta=team_data.get('FTA', 0),
                        ft_pct=team_data.get('FT_PCT'),
                        off_reb=team_data.get('OREB', 0),
                        def_reb=team_data.get('DREB', 0),
                        total_reb=team_data.get('REB', 0),
                        assists=team_data.get('AST', 0),
                        steals=team_data.get('STL', 0),
                        blocks=team_data.get('BLK', 0),
                        turnovers=team_data.get('TO', 0),
                        fouls=team_data.get('PF', 0)
                    )
                    self.db.add(team_box)
                    count += 1
            
            self.db.commit()
            logger.info(f"Ingested {count} box scores for game {game_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error ingesting box scores for {game_id}: {e}")
            self.db.rollback()
            return 0
    
    # =========================================================================
    # STANDINGS & CONTEXT
    # =========================================================================
    
    def update_standings(self, as_of_date: date, season: str) -> int:
        """
        Update playoff standings for all teams.
        Returns count of standings updated.
        """
        logger.info(f"Updating standings for {as_of_date}")
        
        try:
            standings = leaguestandings.LeagueStandings(
                league_id='00',
                season=season,
                season_type='Regular Season'
            )
            
            standings_data = standings.get_normalized_dict()['Standings']
            count = 0
            
            for team_data in standings_data:
                standing = ContextPlayoffStandings(
                    team_id=team_data['TeamID'],
                    as_of_date=as_of_date,
                    season=season,
                    wins=team_data.get('WINS', 0),
                    losses=team_data.get('LOSSES', 0),
                    win_pct=team_data.get('WinPCT'),
                    conference_rank=team_data.get('ConferenceRank'),
                    games_back=team_data.get('GamesBack'),
                    playoff_seed=team_data.get('PlayoffRank'),
                    clinched_playoff=team_data.get('ClinchIndicator') == 'x',
                )
                self.db.add(standing)
                count += 1
            
            self.db.commit()
            logger.info(f"Updated {count} team standings")
            return count
            
        except Exception as e:
            logger.error(f"Error updating standings: {e}")
            self.db.rollback()
            return 0
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _parse_game_status(self, status_text: Optional[str]) -> str:
        """Parse game status text into canonical form."""
        if not status_text:
            return "Scheduled"
        
        status_lower = status_text.lower()
        if "final" in status_lower:
            return "Final"
        elif any(q in status_lower for q in ['1st', '2nd', '3rd', '4th', 'ot']):
            return "Live"
        else:
            return "Scheduled"
    
    def _parse_minutes(self, minutes_str: Optional[str]) -> Optional[float]:
        """Parse minutes string (e.g., '35:42') into float."""
        if not minutes_str:
            return None
        
        try:
            if ':' in minutes_str:
                mins, secs = minutes_str.split(':')
                return float(mins) + float(secs) / 60
            else:
                return float(minutes_str)
        except (ValueError, AttributeError):
            return None


# =============================================================================
# DAILY ETL ORCHESTRATION
# =============================================================================

def run_daily_etl(db_session: Session, target_date: Optional[date] = None):
    """
    Run the daily ETL pipeline.
    
    Steps:
    1. Fetch yesterday's games
    2. Ingest box scores
    3. Update standings
    4. Calculate rest days
    5. Warm cache
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    logger.info(f"Starting daily ETL for {target_date}")
    
    ingestion = NBADataIngestion(db_session)
    
    # Step 1: Fetch games
    games = ingestion.fetch_games_for_date(target_date)
    logger.info(f"Found {len(games)} games for {target_date}")
    
    # Step 2: Ingest each game + box scores
    season = f"{target_date.year}-{str(target_date.year + 1)[-2:]}"
    
    for game_data in games:
        game = ingestion.ingest_game(game_data, season)
        
        # Only ingest box scores for completed games
        if game.status == "Final":
            ingestion.ingest_box_scores(game.game_id)
    
    # Step 3: Update standings
    ingestion.update_standings(target_date, season)
    
    logger.info(f"Daily ETL complete for {target_date}")
