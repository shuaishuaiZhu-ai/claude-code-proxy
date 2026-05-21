@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
if errorlevel 1 exit /b %ERRORLEVEL%
if "%~1"=="" (
  python -m ccproxy run -- claude --bare --model sonnet
) else (
  python -m ccproxy run -- claude --bare %*
)
exit /b %ERRORLEVEL%
