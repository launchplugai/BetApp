"""
ESPN NBA Injury Scraper

Fetches injury reports from ESPN and normalizes to ContextInjury format.
"""
import logging
import time
from datetime import date, datetime
from typing import List, Dict, Optional
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.nba.models import ContextInjury, DimPlayer, DimTeam

logger = logging.getLogger(__name__)


class ESPNInjuryScraper:
    """Scrape NBA injury reports from ESPN."""
    
    BASE_URL = "https://www.espn.com/nba/injuries"
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def scrape_injuries(self) -> List[Dict]:
        """
        Scrape current injury report from ESPN.
        
        Returns list of injury dicts with keys:
        - player_name
        - team_name (ESPN format, needs normalization)
        - injury_type
        - status (Out, Doubtful, Questionable, Probable)
        - expected_return
        """
        logger.info(f"Fetching injuries from {self.BASE_URL}")
        
        try:
            response = self.client.get(self.BASE_URL)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch ESPN injuries: {e}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        # ESPN organizes by team sections
        team_sections = soup.find_all('div', class_=re.compile(r'ResponsiveTable'))
        
        for section in team_sections:
            # Extract team name from header
            team_header = section.find('span', class_='team-name')
            if not team_header:
                continue
            
            team_name = team_header.get_text(strip=True)
            
            # Find injury table
            table = section.find('table')
            if not table:
                continue
            
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                injury = {
                    'player_name': cells[0].get_text(strip=True),
                    'team_name': team_name,
                    'injury_type': cells[1].get_text(strip=True),
                    'status': self._normalize_status(cells[2].get_text(strip=True)),
                    'expected_return': cells[3].get_text(strip=True) if len(cells) > 3 else None
                }
                injuries.append(injury)
        
        logger.info(f"Scraped {len(injuries)} injuries from ESPN")
        return injuries
    
    def _normalize_status(self, raw_status: str) -> str:
        """Normalize ESPN status to canonical form."""
        status_lower = raw_status.lower()
        
        if 'out' in status_lower:
            return 'Out'
        elif 'doubtful' in status_lower:
            return 'Doubtful'
        elif 'questionable' in status_lower:
            return 'Questionable'
        elif 'probable' in status_lower:
            return 'Probable'
        else:
            return 'GTD'  # Game-time decision
    
    def save_to_database(self, db: Session, injuries: List[Dict]) -> int:
        """
        Save scraped injuries to database.
        
        Matches players by name, creates injury records.
        Returns count saved.
        """
        count = 0
        
        for injury_data in injuries:
            # Find player by name
            player = self._find_player(db, injury_data['player_name'])
            if not player:
                logger.warning(f"Player not found: {injury_data['player_name']}")
                continue
            
            # Find team
            team = self._find_team(db, injury_data['team_name'])
            if not team:
                logger.warning(f"Team not found: {injury_data['team_name']}")
                continue
            
            # Check for existing active injury
            existing = db.query(ContextInjury).filter(
                ContextInjury.player_id == player.player_id,
                ContextInjury.status.in_(['Out', 'Doubtful', 'Questionable']),
                ContextInjury.return_date.is_(None)
            ).first()
            
            if existing:
                # Update existing
                existing.injury_type = injury_data['injury_type']
                existing.status = injury_data['status']
                existing.reported_at = datetime.utcnow()
            else:
                # Create new
                injury = ContextInjury(
                    player_id=player.player_id,
                    team_id=team.team_id,
                    injury_type=injury_data['injury_type'],
                    status=injury_data['status'],
                    injury_date=date.today(),
                    source='ESPN'
                )
                db.add(injury)
                count += 1
        
        db.commit()
        return count
    
    def _find_player(self, db: Session, name: str) -> Optional[DimPlayer]:
        """Find player by name (fuzzy match)."""
        # Try exact match first
        player = db.query(DimPlayer).filter(
            DimPlayer.full_name.ilike(name)
        ).first()
        
        if player:
            return player
        
        # Try last name only (for partial matches)
        parts = name.split()
        if len(parts) >= 2:
            last_name = parts[-1]
            player = db.query(DimPlayer).filter(
                DimPlayer.last_name.ilike(last_name)
            ).first()
        
        return player
    
    def _find_team(self, db: Session, espn_team_name: str) -> Optional[DimTeam]:
        """Find team by ESPN name."""
        # ESPN uses full names like "Los Angeles Lakers"
        # Try various matching strategies
        
        # 1. Exact full name
        team = db.query(DimTeam).filter(
            DimTeam.full_name.ilike(espn_team_name)
        ).first()
        
        if team:
            return team
        
        # 2. City + nickname
        for team in db.query(DimTeam).all():
            if team.city in espn_team_name and team.nickname in espn_team_name:
                return team
        
        return None
    
    def close(self):
        """Close HTTP client."""
        self.client.close()


def run_injury_scraper(db: Session) -> int:
    """
    Run full injury scrape and save.
    
    Returns count of new/updated injuries.
    """
    scraper = ESPNInjuryScraper()
    
    try:
        injuries = scraper.scrape_injuries()
        if injuries:
            count = scraper.save_to_database(db, injuries)
            logger.info(f"Saved {count} injuries to database")
            return count
        return 0
    finally:
        scraper.close()
