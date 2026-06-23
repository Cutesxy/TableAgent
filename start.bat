@echo off
setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0
set NANOBOT_DIR=%ROOT_DIR%nanobot
set VENV_PY=%NANOBOT_DIR%\.venv\Scripts\python.exe
set CONFIG_FILE=%NANOBOT_DIR%\configs\tableclaw-bailian-dashscope.json
set SYNC_DOMAIN_PACK=%ROOT_DIR%scripts\sync_domain_pack.sh

if not defined DASHSCOPE_API_KEY (
    echo DASHSCOPE_API_KEY is required. Set it before running start.bat.
    echo   set DASHSCOPE_API_KEY=your-key
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo Missing nanobot virtual environment: %VENV_PY%
    echo Run this once: cd /d "%NANOBOT_DIR%" && python -m venv .venv && .venv\Scripts\python -m pip install -e .
    exit /b 1
)

cd /d "%ROOT_DIR%"
"%VENV_PY%" -m nanobot agent --config "%CONFIG_FILE%" --no-logs %*