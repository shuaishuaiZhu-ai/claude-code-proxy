@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy doctor --profile chatgpt-subscription %*
exit /b %ERRORLEVEL%
