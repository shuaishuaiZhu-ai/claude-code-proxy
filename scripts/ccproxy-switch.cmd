@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
if "%~1"=="" (
  echo Usage: scripts\ccproxy-switch.cmd PROFILE [MODEL]
  echo Example: scripts\ccproxy-switch.cmd chatgpt-subscription ChatGPT5.5
  exit /b 2
)
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
if "%~2"=="" (
  python -m ccproxy model set --provider "%~1"
) else (
  python -m ccproxy model set --provider "%~1" --model "%~2"
)
exit /b %ERRORLEVEL%
