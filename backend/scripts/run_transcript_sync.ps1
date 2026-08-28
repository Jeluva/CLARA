# Wrapper for scripts/fetch_transcripts_local.py, meant to be run by Windows
# Task Scheduler (docs/devlog/BACKLOG.md, transcripts automation follow-up
# to fase-12: "programarlo con cron / Task Scheduler" was already flagged
# there and never done). Reads CLARA_INGEST_SECRET from backend/.env so the
# secret lives in one gitignored place, not duplicated into the task
# definition or this script.
#
# fase-12 found YouTube rate-limits by request volume, not a permanent
# block -- running this more than ~once/day risks re-triggering that, so
# the scheduled task this is wired to should stay at a daily cadence.

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $backendDir ".env"
$logDir = Join-Path $backendDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "transcript_sync.log"

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

if (-not (Test-Path $envFile)) {
    Write-Log "ERROR: no se encontro backend/.env -- nada que leer, abortando."
    exit 1
}

$secretLine = Get-Content $envFile | Where-Object { $_ -match '^INGEST_SECRET=' } | Select-Object -Last 1
if (-not $secretLine) {
    Write-Log "ERROR: INGEST_SECRET no esta seteado en backend/.env -- agregalo (mismo valor que INGEST_SECRET en Render) y reintenta."
    exit 1
}
$secretValue = $secretLine.Substring('INGEST_SECRET='.Length).Trim()
if (-not $secretValue) {
    Write-Log "ERROR: INGEST_SECRET esta vacio en backend/.env."
    exit 1
}

$env:CLARA_BACKEND_URL = "https://clara-l955.onrender.com"
$env:CLARA_INGEST_SECRET = $secretValue

Write-Log "Arrancando fetch_transcripts_local.py contra $($env:CLARA_BACKEND_URL)"
Set-Location $backendDir
try {
    $output = & "$backendDir\venv\Scripts\python.exe" "scripts\fetch_transcripts_local.py" 2>&1
    $output | ForEach-Object { Write-Log $_ }
    Write-Log "Corrida terminada OK."
} catch {
    Write-Log "ERROR: $_"
    exit 1
}
