@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "COMPOSE_FILE=docker-compose.openwebui.yml"
set "ENV_FILE=.env.openwebui"
set "EXAMPLE_ENV=.env.openwebui.example"
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"

if /I "%ACTION%"=="help" goto :help

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed or not in PATH.
  exit /b 1
)

set "DOCKER_CHECK_LOG=%TEMP%\openwebui_docker_check.log"
docker info >"%DOCKER_CHECK_LOG%" 2>&1
if errorlevel 1 (
  findstr /I /C:"Access is denied" "%DOCKER_CHECK_LOG%" >nul
  if not errorlevel 1 (
    echo Docker access denied for this user session.
    echo Fix options:
    echo   1. Start terminal as Administrator
    echo   2. Add your user to docker-users group, then sign out/in
    echo.
    echo Docker diagnostics:
    type "%DOCKER_CHECK_LOG%"
    exit /b 1
  )
  echo Docker daemon is not reachable. Start Docker Desktop and retry.
  echo Docker diagnostics:
  type "%DOCKER_CHECK_LOG%"
  exit /b 1
)

if not exist "%COMPOSE_FILE%" (
  echo Missing %COMPOSE_FILE%.
  exit /b 1
)

if not exist "%ENV_FILE%" (
  if exist "%EXAMPLE_ENV%" (
    copy /Y "%EXAMPLE_ENV%" "%ENV_FILE%" >nul
    echo Created %ENV_FILE% from %EXAMPLE_ENV%.
  ) else (
    echo Missing %ENV_FILE% and %EXAMPLE_ENV%.
    exit /b 1
  )
)

if /I "%ACTION%"=="start" goto :start
if /I "%ACTION%"=="up" goto :start
if /I "%ACTION%"=="stop" goto :stop
if /I "%ACTION%"=="down" goto :stop
if /I "%ACTION%"=="restart" goto :restart
if /I "%ACTION%"=="status" goto :status
if /I "%ACTION%"=="ps" goto :status
if /I "%ACTION%"=="logs" goto :logs
if /I "%ACTION%"=="logs-api" goto :logs_api
if /I "%ACTION%"=="logs-webui" goto :logs_webui
echo Unknown action: %ACTION%
goto :help

:start
echo Starting Open WebUI...
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" up -d --build
if errorlevel 1 exit /b 1
set "PORT=3000"
set "RAG_PORT=8001"
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
  if /I "%%A"=="OPEN_WEBUI_PORT" if not "%%B"=="" set "PORT=%%B"
  if /I "%%A"=="RAG_API_PORT" if not "%%B"=="" set "RAG_PORT=%%B"
)
echo RAG API: http://localhost:%RAG_PORT%/health
echo Open WebUI: http://localhost:%PORT%
echo Waiting for RAG API to become ready...
powershell -NoProfile -Command "$deadline=(Get-Date).AddSeconds(120); while((Get-Date)-lt $deadline){ try { $r=Invoke-WebRequest -Uri 'http://localhost:%RAG_PORT%/health' -UseBasicParsing -TimeoutSec 5; if($r.StatusCode -eq 200){ exit 0 } } catch {}; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo RAG API did not become ready within 120 seconds.
  echo Run ^`openwebui.bat logs-api^` to inspect startup logs.
  exit /b 1
)
echo Waiting for Open WebUI to become ready...
powershell -NoProfile -Command "$deadline=(Get-Date).AddSeconds(120); while((Get-Date)-lt $deadline){ try { $r=Invoke-WebRequest -Uri 'http://localhost:%PORT%/' -UseBasicParsing -TimeoutSec 5; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){ exit 0 } } catch {}; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo Open WebUI did not become ready within 120 seconds.
  echo Run ^`openwebui.bat logs-webui^` to inspect startup logs.
  exit /b 1
)
echo Open WebUI is ready.
start "" "http://localhost:%PORT%"
exit /b 0

:stop
echo Stopping Open WebUI...
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" down
exit /b %errorlevel%

:restart
call "%~f0" stop
if errorlevel 1 exit /b 1
call "%~f0" start
exit /b %errorlevel%

:status
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" ps
exit /b %errorlevel%

:logs
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" logs -f
exit /b %errorlevel%

:logs_api
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" logs -f rag-api
exit /b %errorlevel%

:logs_webui
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" logs -f open-webui
exit /b %errorlevel%

:help
echo Usage: openwebui.bat [start^|stop^|restart^|status^|logs^|logs-api^|logs-webui]
echo.
echo Examples:
echo   openwebui.bat start
echo   openwebui.bat logs-api
exit /b 0
