@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
if "%~1"=="" (
  echo Usage: scripts\ccproxy-switch.cmd PROFILE
  echo Example: scripts\ccproxy-switch.cmd openai-key
  exit /b 2
)
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy use %*
exit /b %ERRORLEVEL%
