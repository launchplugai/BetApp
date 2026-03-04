#!/bin/bash
# Setup NBA Daily ETL Cron Job
#
# Run this script to install the cron job:
# sudo bash scripts/setup_nba_cron.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
ETL_SCRIPT="$PROJECT_DIR/scripts/nba_daily_etl.py"

# Cron expression: 6am ET daily
CRON_TIME="0 6 * * *"

# Full cron command
CRON_CMD="$CRON_TIME $PYTHON_BIN $ETL_SCRIPT >> /var/log/nba_etl.log 2>&1"

echo "================================"
echo "NBA Daily ETL Cron Setup"
echo "================================"
echo ""
echo "This will add the following cron job:"
echo "$CRON_CMD"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Aborted."
    exit 1
fi

# Add to crontab (avoid duplicates)
(crontab -l 2>/dev/null | grep -v "$ETL_SCRIPT"; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed!"
echo ""
echo "Verify with: crontab -l"
echo "View logs: tail -f /var/log/nba_etl.log"
