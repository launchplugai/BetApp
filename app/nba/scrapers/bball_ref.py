"""
Basketball-Reference.com Scraper

Fetches historical advanced stats and player metrics.
"""
import logging
import time
from datetime import date
from typing import List, Dict, Optional
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.nba.models import DimPlayer, FactBoxScore

logger = logging.getLogger(__name__)


class BasketballReferenceScraper:
    """Scrape advanced stats from Basketball-Reference."""
    
    BASE_URL = "https://www.basketball-reference.com"
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            follow_redirects=True
        )
    
    def scrape_player_advanced_stats(
        self, 
        player_name: str,
        season: str = "2026"
    ) -> Optional[Dict]:
        """
        Scrape advanced stats for a player.
        
        Args:
            player_name: Player name (e.g., "LeBron James")
            season: Season year (e.g., "2026" for 2025-26)
            
        Returns:
            Dict with advanced metrics: BPM, VORP, WS/48, etc.
        """
        # Basketball-Reference uses player ID in URL
        # For MVP: /players/j/jamesle01.html
        # We'd need a player ID mapping or search
        
        logger.info(f"Fetching B-Ref stats for {player_name} ({season})")
        
        # TODO: Implement player search to get proper URL
        # For now, return placeholder
        return {
            'player_name': player_name,
            'season': season,
            'bpm': None,  # Box Plus/Minus
            'vorp': None,  # Value Over Replacement Player
            'ws_per_48': None,  # Win Shares per 48 min
            'per': None,  # Player Efficiency Rating
            'ts_pct': None,  # True Shooting %
        }
    
    def scrape_team_ratings(
        self, 
        team_abbrev: str,
        season: str = "2026"
    ) -> Optional[Dict]:
        """
        Scrape team offensive/defensive ratings.
        
        Args:
            team_abbrev: 3-letter team code (e.g., "LAL")
            season: Season year
            
        Returns:
            Dict with team ratings
        """
        # B-Ref team URLs: /teams/LAL/2026.html
        url = f"{self.BASE_URL}/teams/{team_abbrev}/{season}.html"
        
        logger.info(f"Fetching team ratings: {url}")
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find team stats table
            stats_table = soup.find('table', id='team_misc')
            
            if not stats_table:
                logger.warning(f"No stats table found for {team_abbrev}")
                return None
            
            # Extract key metrics
            # B-Ref HTML structure varies, this is simplified
            ratings = {
                'team': team_abbrev,
                'season': season,
                'offensive_rating': None,
                'defensive_rating': None,
                'net_rating': None,
                'pace': None,
                'strength_of_schedule': None
            }
            
            # Parse table rows
            for row in stats_table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                stat_name = cells[0].get_text(strip=True).lower()
                stat_value = cells[1].get_text(strip=True)
                
                try:
                    if 'offensive rating' in stat_name:
                        ratings['offensive_rating'] = float(stat_value)
                    elif 'defensive rating' in stat_name:
                        ratings['defensive_rating'] = float(stat_value)
                    elif 'pace' in stat_name:
                        ratings['pace'] = float(stat_value)
                    elif 'sos' in stat_name or 'strength' in stat_name:
                        ratings['strength_of_schedule'] = float(stat_value)
                except ValueError:
                    continue
            
            # Calculate net rating if we have both
            if ratings['offensive_rating'] and ratings['defensive_rating']:
                ratings['net_rating'] = ratings['offensive_rating'] - ratings['defensive_rating']
            
            return ratings
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch B-Ref team ratings: {e}")
            return None
    
    def scrape_player_game_log(
        self, 
        player_id: str,
        season: str = "2026"
    ) -> List[Dict]:
        """
        Scrape game log for a player.
        
        Args:
            player_id: B-Ref player ID (e.g., "jamesle01")
            season: Season year
            
        Returns:
            List of game dicts with stats
        """
        url = f"{self.BASE_URL}/players/{player_id[0]}/{player_id}/gamelog/{season}"
        
        logger.info(f"Fetching game log: {url}")
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find game log table
            table = soup.find('table', id='pgl_basic')
            
            if not table:
                return []
            
            games = []
            
            for row in table.find_all('tr', class_=''):
                # Skip header rows
                if 'thead' in row.get('class', []):
                    continue
                
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue
                
                game = {
                    'date': cells[1].get_text(strip=True),
                    'opponent': cells[4].get_text(strip=True),
                    'result': cells[6].get_text(strip=True),  # W/L
                    'minutes': cells[7].get_text(strip=True),
                    'points': cells[26].get_text(strip=True),
                    'rebounds': cells[19].get_text(strip=True),
                    'assists': cells[20].get_text(strip=True),
                }
                
                games.append(game)
            
            return games
            
        except Exception as e:
            logger.error(f"Failed to scrape game log: {e}")
            return []
    
    def close(self):
        """Close HTTP client."""
        self.client.close()


def run_bball_ref_team_update(db: Session, team_abbrev: str, season: str) -> bool:
    """
    Fetch and store team ratings from B-Ref.
    
    Args:
        db: Database session
        team_abbrev: Team code (e.g., "LAL")
        season: Season year
        
    Returns:
        True if successful
    """
    scraper = BasketballReferenceScraper()
    
    try:
        ratings = scraper.scrape_team_ratings(team_abbrev, season)
        
        if not ratings:
            return False
        
        # TODO: Store in database (need to add team_ratings table)
        logger.info(f"Fetched ratings for {team_abbrev}: {ratings}")
        
        return True
        
    finally:
        scraper.close()
