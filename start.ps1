param(
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$NANOBOT_DIR = Join-Path $ROOT_DIR "nanobot"
$VENV_PY = Join-Path $NANOBOT_DIR ".venv\Scripts\python.exe"
$CONFIG_FILE = Join-Path $NANOBOT_DIR "configs\tableclaw-bailian-dashscope.json"

if (-not $env:DASHSCOPE_API_KEY) {
    Write-Host "DASHSCOPE_API_KEY is required. Set it before running start.ps1."
    Write-Host '  $env:DASHSCOPE_API_KEY = "your-key"'
    exit 1
}

if (-not (Test-Path $VENV_PY)) {
    Write-Host "Missing nanobot virtual environment: $VENV_PY"
    Write-Host "Run this once: cd $NANOBOT_DIR; python -m venv .venv; .venv\Scripts\python -m pip install -e ."
    exit 1
}

Set-Location $ROOT_DIR
& $VENV_PY -m nanobot agent --config $CONFIG_FILE --no-logs @ExtraArgs