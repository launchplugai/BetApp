"""
NBA Data Scrapers

Web scraping for injury reports, news, and supplementary data.
"""
from app.nba.scrapers.espn import ESPNInjuryScraper, run_injury_scraper
from app.nba.scrapers.bball_ref import (
    BasketballReferenceScraper, 
    run_bball_ref_team_update
)

__all__ = [
    'ESPNInjuryScraper', 
    'run_injury_scraper',
    'BasketballReferenceScraper',
    'run_bball_ref_team_update'
]
