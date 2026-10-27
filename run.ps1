$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    Write-Host "[ERROR] Quasar is not set up yet. Run: $Root\setup.ps1" -ForegroundColor Red
    exit 2
}
& $Python (Join-Path $Root 'quasar.py') @args
exit $LASTEXITCODE
