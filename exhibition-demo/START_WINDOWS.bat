@echo off
setlocal
cd /d "%~dp0"

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Python 3.10 or newer is required. Install it and enable Add Python to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating isolated Q-SHIFT exhibition environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create the local Python environment. Install Python 3.10+ and try again.
    pause
    exit /b 1
  )
)

set "PY=%CD%\.venv\Scripts\python.exe"
"%PY%" -c "import fastapi,uvicorn,numpy,stim,pymatching" >nul 2>&1
if errorlevel 1 (
  echo Installing the pinned simulation dependencies. Internet is needed only for this first setup.
  "%PY%" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Check the error above and retry.
    pause
    exit /b 1
  )
)

echo Starting the local-only Q-SHIFT demo. Keep this window open; press Ctrl+C to stop.
echo The browser opens after the health endpoint responds.
"%PY%" server.py
if errorlevel 1 pause
endlocal
