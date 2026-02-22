@echo off
REM run_rag_indexer.bat — Index DRHP PDFs for RAG-powered Q&A

echo.
echo ============================================================
echo   TradeSage RAG Indexer
echo ============================================================
echo.

cd /d "%~dp0"

REM Your Python location (confirmed from 'where python')
SET PYTHON=C:\Users\sreek\AppData\Local\Python\bin\python.exe

echo   Using Python: %PYTHON%
echo.

REM Install dependencies
echo   Installing dependencies (sentence-transformers, numpy)...
echo   First time may take 2-3 minutes to download...
echo.
%PYTHON% -m pip install sentence-transformers numpy --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ⚠ pip install had issues — trying to continue anyway...
    echo   If indexer fails, run manually:
    echo   %PYTHON% -m pip install sentence-transformers numpy
    echo.
)

echo   Running RAG indexer...
echo   First run downloads embedding model (~90MB, one time only)
echo   Then ~2-3 minutes per IPO PDF
echo.
%PYTHON% rag_indexer.py

echo.
echo ============================================================
echo   Done. RAG Q&A is now active for indexed IPOs.
echo   Users will see page citations in every AI answer.
echo ============================================================
echo.
pause
