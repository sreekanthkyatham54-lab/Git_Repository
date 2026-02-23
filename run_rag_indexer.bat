@echo off
REM run_rag_indexer.bat — Semantic chunking + embedding pipeline
REM Usage:
REM   run_rag_indexer.bat          → index only new IPOs (skips already done)
REM   run_rag_indexer.bat --force  → re-index ALL IPOs (use after code changes)

echo.
echo ============================================================
echo   TradeSage RAG Semantic Indexer
echo ============================================================
echo.

cd /d "%~dp0"

SET PYTHON=C:\Users\sreek\AppData\Local\Python\bin\python.exe

echo   Using Python: %PYTHON%
echo.
echo   Installing dependencies...
%PYTHON% -m pip install sentence-transformers numpy pdfplumber --quiet

echo.
if "%1"=="--force" (
    echo   FORCE MODE — re-indexing all IPOs
    %PYTHON% rag_indexer.py --force
) else (
    echo   Indexing new IPOs only (pass --force to re-index all)
    %PYTHON% rag_indexer.py
)

echo.
echo ============================================================
echo   Done.
echo ============================================================
echo.
pause
