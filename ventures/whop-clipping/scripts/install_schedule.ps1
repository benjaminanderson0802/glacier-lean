param(
    [switch]$Live,
    [string]$Python = "",
    [string]$ClipHome = $env:CLIP_HOME,
    [string]$TaskName = "Glacier Whop Clipping Hourly"
)

$ErrorActionPreference = "Stop"
$ventureDir = Split-Path -Parent $PSScriptRoot
$repoDir = Split-Path -Parent $ventureDir
if (-not $Python) {
    $repoPython = Join-Path $repoDir ".venv\Scripts\python.exe"
    $ownerPython = "C:\Users\benja\glacier-dev\.venv\Scripts\python.exe"
    if (Test-Path $repoPython) { $Python = $repoPython }
    elseif (Test-Path $ownerPython) { $Python = $ownerPython }
    else { $Python = "python" }
}
if (-not $ClipHome) {
    $ClipHome = Join-Path $env:USERPROFILE ".glacier\ventures\whop-clipping"
}
$configPath = Join-Path $ClipHome "config.json"
if (-not (Test-Path $configPath)) {
    throw "Create $configPath from config.example.json and finish owner setup first."
}
$config = Get-Content -Raw -Path $configPath | ConvertFrom-Json
$config.live = [bool]$Live.IsPresent
$configJson = $config | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($configPath, $configJson, [System.Text.UTF8Encoding]::new($false))

$runner = Join-Path $PSScriptRoot "run_hourly.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -Python `"$Python`" -ClipHome `"$ClipHome`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $ventureDir
$start = (Get-Date).AddMinutes(2)
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration ([TimeSpan]::FromDays(3650))
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Description "Runs the local Whop clipping Producer and Distributor hourly." -Force | Out-Null
Write-Output "Registered '$TaskName' for the current user. Live uploads: $($config.live)."
