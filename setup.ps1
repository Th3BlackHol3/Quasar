[CmdletBinding()]
param(
    [switch]$WithTools,
    [switch]$CheckTools,
    [switch]$UpgradePip
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Bootstrap = Join-Path $Root 'bootstrap.py'
$PythonLauncher = Get-Command 'py' -ErrorAction SilentlyContinue
$PythonCommand = Get-Command 'python' -ErrorAction SilentlyContinue
if ($PythonLauncher) {
    $Executable = $PythonLauncher.Source
    $PythonArgs = @('-3', $Bootstrap)
} elseif ($PythonCommand) {
    $Executable = $PythonCommand.Source
    $PythonArgs = @($Bootstrap)
} else {
    Write-Host '[ERROR] Python 3.10+ was not found. Install it from https://www.python.org/downloads/windows/ and ensure it is available in PATH.' -ForegroundColor Red
    exit 127
}
if ($WithTools) { $PythonArgs += '--with-tools' }
if ($CheckTools) { $PythonArgs += '--check-tools' }
if ($UpgradePip) { $PythonArgs += '--upgrade-pip' }
& $Executable @PythonArgs
exit $LASTEXITCODE
