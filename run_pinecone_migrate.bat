@echo off
echo.
echo ============================================================
echo   TradeSage — Pinecone Migration
echo   Uploads all DRHP chunks to Pinecone cloud
echo   Run this ONCE after re-indexing
echo ============================================================
echo.

cd /d "%~dp0"

SET PYTHON=C:\Users\sreek\AppData\Local\Python\bin\python.exe

echo   Installing pinecone + python-dotenv...
%PYTHON% -m pip install pinecone python-dotenv --quiet

echo.
echo   Starting migration...
%PYTHON% pinecone_migrate.py

echo.
pause
