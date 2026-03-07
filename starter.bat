@echo off

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "REQ_FILE="

if exist "req.txt" (
  set "REQ_FILE=req.txt"
) else if exist "requirements.txt" (
  set "REQ_FILE=requirements.txt"
) else if exist "requirements-docs.txt" (
  set "REQ_FILE=requirements-docs.txt"
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
  echo [1/4] Creating virtual environment in "%VENV_DIR%"...
  where py >nul 2>&1
  if %errorlevel%==0 (
    py -3 -m venv "%VENV_DIR%"
  ) else (
    python -m venv "%VENV_DIR%"
  )
  if errorlevel 1 (
    echo Failed to create virtual environment. Make sure Python is installed.
    exit /b 1
  )
) else (
  echo [1/4] Virtual environment already exists: "%VENV_DIR%"
)

echo [2/4] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

echo [3/4] Upgrading pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo Failed to upgrade pip tools.
  exit /b 1
)

if defined REQ_FILE (
  echo [4/4] Installing dependencies from "%REQ_FILE%"...
  pip install -r "%REQ_FILE%"
  if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
  )
) else (
  echo [4/4] No req.txt or requirements.txt file found. Skipping dependency install.
)

echo.
echo Environment is ready and active in this terminal.

echo [5/5] Launching docs webpage...
start "" "http://127.0.0.1:8000/"
python -m mkdocs serve --dev-addr 127.0.0.1:8000 --dirty --watch mkdocs.yml --watch docs --verbose
