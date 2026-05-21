@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
if "%~1"=="" (
  python -m ccproxy run -- claude --model sonnet
) else (
  python -m ccproxy run -- claude %*
)
exit /b %ERRORLEVEL%
