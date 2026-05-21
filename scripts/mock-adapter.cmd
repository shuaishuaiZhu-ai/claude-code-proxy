@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%mock_openai_provider.py" --port 8000
exit /b %ERRORLEVEL%
