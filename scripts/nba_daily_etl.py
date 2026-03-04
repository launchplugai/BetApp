#!/usr/bin/env python3
"""
NBA Daily ETL Script.

Run via cron at 6am ET daily:
0 6 * * * /var/lib/openbot/workdir/target/.venv/bin/python /var/lib/openbot/workdir/target/scripts/nba_daily_etl.py >> /var/log/nba_etl.log 2>&1
"""

import sys
import logging
from datetime import date, timedelta
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.nba.database import init_database, get_db_session
from app.nba.ingestion import run_daily_etl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/nba_etl.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run daily ETL pipeline."""
    logger.info("=" * 60)
    logger.info("Starting NBA Daily ETL")
    logger.info("=" * 60)
    
    # Initialize
    init_database()
    db = get_db_session()
    
    try:
        # Get yesterday's date
        yesterday = date.today() - timedelta(days=1)
        
        # Run ETL
        logger.info(f"Processing games for {yesterday}")
        run_daily_etl(db, yesterday)
        
        logger.info("✅ Daily ETL complete")
        return 0
        
    except Exception as e:
        logger.error(f"❌ ETL failed: {e}", exc_info=True)
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
