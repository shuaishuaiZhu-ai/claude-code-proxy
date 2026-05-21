@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_chatgpt_subscription.ps1" -DoctorOnly %*
exit /b %ERRORLEVEL%
