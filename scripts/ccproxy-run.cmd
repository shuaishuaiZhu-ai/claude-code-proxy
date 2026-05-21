@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
if "%~1"=="" (
  python -m ccproxy run -- claude --bare --model sonnet
) else (
  python -m ccproxy run -- claude --bare %*
)
exit /b %ERRORLEVEL%
