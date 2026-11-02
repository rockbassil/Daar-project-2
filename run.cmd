@echo off
cd /d "%~dp0"
python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/stats',timeout=2)); assert d.get('corpus_ready') and d.get('graph')" >nul 2>&1
if not errorlevel 1 (
  start "" "http://127.0.0.1:8000"
  exit /b 0
)
python -m library validate
if errorlevel 1 (
  echo.
  echo The library is not ready. Run: python scripts/prepare_library.py --target 1700
  pause
  exit /b 1
)
echo.
echo Open http://127.0.0.1:8000 in your browser.
echo Keep this window open. Press Ctrl+C to stop the server.
start "" "http://127.0.0.1:8000"
python -m library serve --host 0.0.0.0 --port 8000
pause
