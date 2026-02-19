#!/bin/bash
# run_scraper.sh — Mac/Linux version
# Add to crontab: 0 8 * * * /path/to/sme-ipo-research/run_scraper.sh

cd "$(dirname "$0")"
echo "Running SME IPO Scraper at $(date)"
python scraper.py
echo "Done."
