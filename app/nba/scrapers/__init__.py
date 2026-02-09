"""
NBA Data Scrapers

Web scraping for injury reports, news, and supplementary data.
"""
from app.nba.scrapers.espn import ESPNInjuryScraper, run_injury_scraper

__all__ = ['ESPNInjuryScraper', 'run_injury_scraper']
