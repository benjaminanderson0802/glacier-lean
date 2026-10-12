# Register the source checkout to launch at this Windows user's next sign-in.
# Run from PowerShell as the same user; no administrator prompt is needed.
$ErrorActionPreference = 'Stop'
$TaskName = 'Glacier Dev Backend'
$Launcher = Join-Path $env:USERPROFILE 'glacier-dev-run.ps1'

if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
    throw "Could not find $Launcher. Save glacier-dev-run.ps1 there first."
}

$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Launcher`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Starts the Glacier source checkout at this user''s sign-in.' -Force | Out-Null
Write-Host "Registered '$TaskName' for $env:USERNAME. It starts at the next sign-in."
