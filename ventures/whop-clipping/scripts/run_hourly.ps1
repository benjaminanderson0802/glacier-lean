param(
    [string]$Python = "python",
    [string]$ClipHome = $env:CLIP_HOME
)

$ErrorActionPreference = "Stop"
$ventureDir = Split-Path -Parent $PSScriptRoot
if (-not $ClipHome) {
    $ClipHome = Join-Path $env:USERPROFILE ".glacier\ventures\whop-clipping"
}
$logDir = Join-Path $ClipHome "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ("hourly-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

Push-Location $ventureDir
try {
    "[{0}] Producer start" -f (Get-Date -Format o) | Add-Content -Path $logPath
    & $Python -m scripts.producer 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Producer failed with exit code $LASTEXITCODE" }
    "[{0}] Distributor start" -f (Get-Date -Format o) | Add-Content -Path $logPath
    & $Python -m scripts.distributor --live 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Distributor failed with exit code $LASTEXITCODE" }
    "[{0}] Hourly run complete" -f (Get-Date -Format o) | Add-Content -Path $logPath
}
catch {
    "[{0}] ERROR: {1}" -f (Get-Date -Format o), $_ | Add-Content -Path $logPath
    throw
}
finally {
    Pop-Location
}
