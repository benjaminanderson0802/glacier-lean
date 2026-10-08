param(
    [Parameter(Mandatory = $true)]
    [string] $Installer,
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$dataDir = Join-Path $env:APPDATA 'org.glacier.desktop'
$installerPath = (Resolve-Path -LiteralPath $Installer -ErrorAction Stop).Path
$installerVersion = (Get-Item -LiteralPath $installerPath).VersionInfo.ProductVersion
if (-not $installerVersion) { $installerVersion = (Get-Item -LiteralPath $installerPath).VersionInfo.FileVersion }
if (-not $installerVersion) {
    throw 'The installer file does not contain a product version.'
}

function Write-Step([string] $Text) {
    Write-Host "[STEP] $Text"
}

function Get-GlacierProcesses {
    $all = @(Get-CimInstance Win32_Process -Filter "Name='glacier-desktop.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue)
    $desktop = @($all | Where-Object { $_.Name -ieq 'glacier-desktop.exe' })
    $ids = @($desktop | ForEach-Object { [int]$_.ProcessId })
    $engines = @($all | Where-Object {
        $_.Name -ieq 'python.exe' -and $ids -contains [int]$_.ParentProcessId -and
        $_.CommandLine -match '(?i)uvicorn\s+app:app'
    })
    return @($desktop + $engines)
}

function Stop-GlacierProcesses {
    $targets = @(Get-GlacierProcesses)
    if ($targets.Count -eq 0) { return }

    # Ask the desktop shell to close normally. Its close handler stops the engine child.
    foreach ($target in @($targets | Where-Object { $_.Name -ieq 'glacier-desktop.exe' })) {
        $process = Get-Process -Id ([int]$target.ProcessId) -ErrorAction SilentlyContinue
        if ($process) { [void]$process.CloseMainWindow() }
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ([DateTime]::UtcNow -lt $deadline) {
        $remaining = @(Get-GlacierProcesses)
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 250
    }

    # Stop only the identified Glacier shell and its uvicorn child, never other Python processes.
    $remaining = @(Get-GlacierProcesses)
    foreach ($target in $remaining) {
        Stop-Process -Id ([int]$target.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}

function Get-ApiJson([string] $BaseUrl, [string] $Path, [string] $EngineToken) {
    $headers = @{ Authorization = "Bearer $EngineToken" }
    return Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers $headers -TimeoutSec 10
}

function Get-EngineEndpoint {
    $desktop = @(Get-CimInstance Win32_Process -Filter "Name='glacier-desktop.exe'" -ErrorAction SilentlyContinue)
    foreach ($process in $desktop) {
        if ($process.CommandLine -match '(?i)127\.0\.0\.1:(\d{1,5})') {
            $port = [int]$Matches[1]
            if ($port -gt 0 -and $port -le 65535) { return "http://127.0.0.1:$port" }
        }
    }
    return $null
}

if ($DryRun) {
    Write-Step 'Stop Glacier desktop and its engine gracefully, then forcefully after 10 seconds.'
    Write-Step "Back up settings.json and sidecar.json from $dataDir to a timestamped sibling folder."
    Write-Step "Run $installerPath silently with /S and wait for it to finish."
    Write-Step 'Start Glacier from its installed executable.'
    Write-Step 'Wait up to 90 seconds for the local engine.'
    Write-Step "Check /api/health, /api/releases/current version $installerVersion, /api/assistant/settings engines and active route, memory note count, and vault path using Authorization: Bearer [redacted]."
    Write-Step 'Print a short PASS/FAIL table.'
    exit 0
}

$checks = [ordered]@{
    'Health' = 'FAIL'
    'Installed version' = 'FAIL'
    'Engines and route' = 'FAIL'
    'Memory note count' = 'SKIP'
    'Vault path' = 'FAIL'
}
$memoryCountBefore = $null
$vaultPathBefore = Join-Path $dataDir 'vault'
$vaultPathAfter = $vaultPathBefore
$token = $null
$failure = $null

try {
    # Capture the read-only baseline before stopping Glacier, if its existing API is reachable.
    $existingBase = Get-EngineEndpoint
    if ($existingBase -and (Test-Path -LiteralPath (Join-Path $dataDir '.engine-token') -PathType Leaf)) {
        $token = (Get-Content -LiteralPath (Join-Path $dataDir '.engine-token') -Raw).Trim()
        if ($token) {
            try {
                $baselineNotes = @(Get-ApiJson $existingBase '/api/memory/notes' $token)
                $memoryCountBefore = $baselineNotes.Count
            } catch {
                $memoryCountBefore = $null
            }
        }
        $token = $null
    }

    Write-Step 'Stop Glacier desktop and its engine gracefully, then forcefully after 10 seconds.'
    Stop-GlacierProcesses

    Write-Step "Back up settings.json and sidecar.json from $dataDir."
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $backupDir = Join-Path (Split-Path -Parent $dataDir) "org.glacier.desktop-review-backup-$stamp"
    $suffix = 0
    while (Test-Path -LiteralPath $backupDir) {
        $suffix++
        $backupDir = Join-Path (Split-Path -Parent $dataDir) "org.glacier.desktop-review-backup-$stamp-$suffix"
    }
    $filesToBackUp = @('settings.json', 'sidecar.json') | ForEach-Object { Join-Path $dataDir $_ } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    if (@($filesToBackUp).Count -gt 0) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
        foreach ($file in $filesToBackUp) { Copy-Item -LiteralPath $file -Destination $backupDir }
    }

    Write-Step "Run the installer silently (/S) and wait: $installerPath"
    $install = Start-Process -FilePath $installerPath -ArgumentList '/S' -Wait -PassThru
    if ($install.ExitCode -ne 0) { throw "The installer exited with code $($install.ExitCode)." }

    Write-Step 'Start Glacier.'
    $installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Glacier'
    $desktopExe = Join-Path $installRoot 'glacier-desktop.exe'
    if (-not (Test-Path -LiteralPath $desktopExe -PathType Leaf)) {
        $desktopExe = Join-Path $env:ProgramFiles 'Glacier\glacier-desktop.exe'
    }
    if (-not (Test-Path -LiteralPath $desktopExe -PathType Leaf)) {
        $uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
        $uninstallKeys = @($uninstallKey, 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall')
        $entry = Get-ChildItem -LiteralPath $uninstallKeys -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty -LiteralPath $_.PSPath } |
            Where-Object { $_.DisplayName -eq 'Glacier' -and $_.InstallLocation } | Select-Object -First 1
        if ($entry) { $desktopExe = Join-Path $entry.InstallLocation.Trim().Trim('"') 'glacier-desktop.exe' }
    }
    if (-not (Test-Path -LiteralPath $desktopExe -PathType Leaf)) { throw 'Could not find the installed glacier-desktop.exe.' }
    Start-Process -FilePath $desktopExe | Out-Null

    Write-Step 'Wait up to 90 seconds for the local engine.'
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    $baseUrl = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        $baseUrl = Get-EngineEndpoint
        if ($baseUrl) {
            try {
                $healthProbe = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/health" -TimeoutSec 2
                if ($healthProbe.ok -eq $true) { break }
            } catch { }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $baseUrl) { throw 'The engine endpoint was not found within 90 seconds.' }

    $tokenPath = Join-Path $dataDir '.engine-token'
    if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) { throw 'The engine token file was not created.' }
    $token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
    if (-not $token) { throw 'The engine token file is empty.' }

    $health = Get-ApiJson $baseUrl '/api/health' $token
    $checks['Health'] = if ($health.ok -eq $true) { 'PASS' } else { 'FAIL' }

    $release = Get-ApiJson $baseUrl '/api/releases/current' $token
    $checks['Installed version'] = if ([string]$release.version -eq [string]$installerVersion) { 'PASS' } else { 'FAIL' }

    $engineInfo = Get-ApiJson $baseUrl '/api/assistant/settings' $token
    $checks['Engines and route'] = if (@($engineInfo.engines).Count -gt 0 -and $engineInfo.active_engine) { 'PASS' } else { 'FAIL' }

    $notesAfter = @(Get-ApiJson $baseUrl '/api/memory/notes' $token)
    if ($null -ne $memoryCountBefore) {
        $checks['Memory note count'] = if ($notesAfter.Count -eq $memoryCountBefore) { 'PASS' } else { 'FAIL' }
    }

    $vaultPathAfter = Join-Path $dataDir 'vault'
    $checks['Vault path'] = if ([string]$vaultPathAfter -eq [string]$vaultPathBefore) { 'PASS' } else { 'FAIL' }
    if (@($checks.Values | Where-Object { $_ -eq 'FAIL' }).Count -gt 0) { throw 'One or more review checks failed.' }
} catch {
    # Do not include arbitrary exception details in the table; they can contain request data.
    $failure = $_.Exception.Message -replace '(?i)token=[^&\s]+', 'token=[redacted]'
    if ($token) { $failure = $failure.Replace($token, '[redacted]') }
} finally {
    $token = $null
}

Write-Host ''
Write-Host 'Glacier review install'
Write-Host ('{0,-24} {1}' -f 'Check', 'Result')
Write-Host ('{0,-24} {1}' -f '------------------------', '------')
foreach ($name in $checks.Keys) { Write-Host ('{0,-24} {1}' -f $name, $checks[$name]) }
if ($failure) { Write-Host "Details: $failure" }
if (@($checks.Values | Where-Object { $_ -eq 'FAIL' }).Count -gt 0 -or $failure) { exit 1 }
