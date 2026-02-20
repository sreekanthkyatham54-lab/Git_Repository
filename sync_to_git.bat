@echo off
REM sync_to_git.bat
REM Run this from your sme-ipo-research folder to copy ALL files to Git_Repository
REM Then just do Commit + Push in GitHub Desktop

SET SOURCE=%~dp0
SET TARGET=D:\sme-ipo-research\Git_Repository

echo Syncing all files to Git_Repository...

xcopy "%SOURCE%app.py"                    "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%data_loader.py"            "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%db_reader.py"              "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%scraper.py"                "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%drhp_scraper.py"           "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%requirements.txt"          "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%packages.txt"              "%TARGET%\"                    /Y /Q
xcopy "%SOURCE%README.md"                 "%TARGET%\"                    /Y /Q

xcopy "%SOURCE%pages\*"                   "%TARGET%\pages\"              /Y /Q
xcopy "%SOURCE%utils\*"                   "%TARGET%\utils\"              /Y /Q
xcopy "%SOURCE%data\*"                    "%TARGET%\data\"               /Y /Q

REM Copy .github folder (GitHub Actions workflow)
xcopy "%SOURCE%.github\workflows\*"  "%TARGET%\.github\workflows\"  /Y /Q /I

REM Copy .streamlit config
xcopy "%SOURCE%.streamlit\*"              "%TARGET%\.streamlit\"         /Y /Q /I

echo.
echo Done! All files synced.
echo Now open GitHub Desktop, Commit to main, then Push origin.
pause
