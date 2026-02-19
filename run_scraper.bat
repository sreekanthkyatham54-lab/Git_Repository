@echo off
REM run_scraper.bat — Run this daily to update live IPO data
REM Schedule via Windows Task Scheduler to run at 8:00 AM daily

cd /d "%~dp0"
echo Running SME IPO Scraper at %date% %time%
python scraper.py
echo Done. Data saved to data\live_ipo_data.json
pause
