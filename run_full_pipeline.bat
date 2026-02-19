@echo off
REM run_full_pipeline.bat
REM Run this daily to get live IPO data + DRHP analysis
REM Schedule via Windows Task Scheduler at 8:00 AM

cd /d "%~dp0"
echo ============================================
echo Step 1: Fetching live IPO list + GMP data
echo ============================================
python scraper.py

echo.
echo ============================================
echo Step 2: Downloading + parsing DRHP PDFs
echo ============================================
python drhp_scraper.py

echo.
echo ============================================
echo Done! Start the app with:
echo   python -m streamlit run app.py
echo ============================================
pause
