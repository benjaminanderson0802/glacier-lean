param(
    [Parameter(Mandatory = $true)]
    [string] $Installer
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$installRoot = Join-Path $env:RUNNER_TEMP "glacier-smoke-install"
$appDataRoot = Join-Path $env:RUNNER_TEMP "glacier-smoke-appdata"
$dataDir = Join-Path $appDataRoot "org.glacier.desktop"
$backend = $null
$uninstaller = $null
$evidencePath = Join-Path $env:RUNNER_TEMP "glacier-first-automation-evidence.txt"
$evidence = $null

function Stop-Smoke([string] $Message) {
    throw "Windows desktop smoke test failed: $Message"
}

function Get-ApiJson([string] $Path, [string] $Token, [int] $TimeoutSec = 10) {
    try {
        return Invoke-RestMethod -Uri "$baseUrl$Path" -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec $TimeoutSec
    } catch {
        Stop-Smoke "API request $Path failed: $($_.Exception.Message)"
    }
}

function Safe-Text([string] $Value) {
    if (-not $Value) { return "" }
    if ($token) { return $Value.Replace($token, "[redacted]") }
    return $Value
}

try {
    if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
        Stop-Smoke "installer was not found: $Installer"
    }
    New-Item -ItemType Directory -Force -Path $installRoot, $appDataRoot, $dataDir | Out-Null

    # NSIS requires /D= as the final argument; backend data stays under RUNNER_TEMP via GLACIER_HOME.
    $installArgs = "/S", "/D=$installRoot"
    $install = Start-Process -FilePath $Installer -ArgumentList $installArgs -Wait -PassThru
    if ($install.ExitCode -ne 0) { Stop-Smoke "the silent installer exited with $($install.ExitCode)" }

    # Tauri's resource folder on Windows is the install folder itself (the app reads it via resource_dir()).
    $resourceRoot = @($installRoot, (Join-Path $installRoot "resources")) |
        Where-Object { Test-Path -LiteralPath (Join-Path $_ "runtime\x86_64-pc-windows-msvc\python.exe") -PathType Leaf } |
        Select-Object -First 1
    if (-not $resourceRoot) {
        Write-Host "Installed files (top two levels):"
        Get-ChildItem -LiteralPath $installRoot -Depth 1 | ForEach-Object { Write-Host "  $($_.FullName)" }
        Stop-Smoke "bundled Python was not installed"
    }
    $python = Join-Path $resourceRoot "runtime\x86_64-pc-windows-msvc\python.exe"
    $backendDir = Join-Path $resourceRoot "backend"
    if (-not (Test-Path -LiteralPath (Join-Path $backendDir "app.py") -PathType Leaf)) { Stop-Smoke "bundled backend was not installed" }

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    $baseUrl = "http://127.0.0.1:$port"

    # Match desktop/src-tauri/src/lib.rs: cwd=backend; python -s -m uvicorn app:app --host 127.0.0.1 --port <port>;
    # GLACIER_HOME is app data and the two low-resource values come from desktop/sidecar.json.
    $env:GLACIER_HOME = $dataDir
    $env:GLACIER_LOCAL_MODEL = "granite3.3:2b"
    $env:GLACIER_MAX_PARALLEL_RUNS = "1"
    $env:PYTHONNOUSERSITE = "1"
    # A real PC had npm's extensionless "codex" script on PATH; starting it shows a blocking
    # "Unsupported 16-bit application" box. Put the same kind of file first on PATH so the
    # smoke test fails (times out) if the engine ever tries to run it again.
    $trap = Join-Path $env:RUNNER_TEMP "glacier-npm-trap"
    New-Item -ItemType Directory -Force $trap | Out-Null
    Set-Content -LiteralPath (Join-Path $trap "codex") -Value "#!/bin/sh`nexit 0`n"
    Set-Content -LiteralPath (Join-Path $trap "gemini") -Value "#!/bin/sh`nexit 0`n"
    $env:PATH = "$trap;$env:PATH"
    $backend = Start-Process -FilePath $python `
        -ArgumentList @("-s", "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "$port") `
        -WorkingDirectory $backendDir -RedirectStandardOutput (Join-Path $dataDir "backend.log") `
        -RedirectStandardError (Join-Path $dataDir "backend-error.log") -PassThru

    $ready = $false
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($backend.HasExited) {
            foreach ($log in "backend.log", "backend-error.log") {
                $logPath = Join-Path $dataDir $log
                if (Test-Path -LiteralPath $logPath) { Write-Host "--- last lines of $log ---"; Get-Content -LiteralPath $logPath -Tail 40 | ForEach-Object { Write-Host $_ } }
            }
            Stop-Smoke "the bundled backend exited during startup (exit code $($backend.ExitCode))"
        }
        try {
            $health = Invoke-WebRequest -Uri "$baseUrl/api/health" -TimeoutSec 2
            if ($health.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { Stop-Smoke "GET /api/health did not succeed within 60 seconds" }

    try {
        Invoke-WebRequest -Uri "$baseUrl/api/system/settings" -TimeoutSec 10 | Out-Null
        Stop-Smoke "an API request without the engine token was accepted"
    } catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401) { }
        else { Stop-Smoke "the no-token API check did not return 401" }
    }

    $tokenPath = Join-Path $dataDir ".engine-token"
    $tokenDeadline = [DateTime]::UtcNow.AddSeconds(10)
    while (-not (Test-Path -LiteralPath $tokenPath) -and [DateTime]::UtcNow -lt $tokenDeadline) {
        Start-Sleep -Milliseconds 200
    }
    if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) { Stop-Smoke "backend did not create its engine token" }
    $token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
    if (-not $token) { Stop-Smoke "the engine token file is empty" }
    $authorized = Invoke-WebRequest -Uri "$baseUrl/api/system/settings" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 10
    if ($authorized.StatusCode -ne 200) { Stop-Smoke "the token-authenticated API request did not succeed" }

    # Use the bundled template catalog to find an offline flow. The starter proposal currently
    # exposes requires_local_model, which does not mean no extra tool is needed (Codex flows can
    # also have that value); inspect the API's flow steps and reject AI, network, and sub-flow steps.
    $proposal = Get-ApiJson "/api/starter" $token
    $templates = Get-ApiJson "/api/templates" $token
    $allowedTypes = @("schedule", "command", "check", "note")
    $networkPattern = '(?i)(\bcurl\b|\bwget\b|\binvoke-webrequest\b|\biwr\b|https?://|\bfetch_page\b|\b(ftp|ssh|scp)\b)'
    $eligible = @($templates | Where-Object {
        $flow = $_.template
        $_.installable -and $flow -and $flow.nodes.Count -gt 0 -and
        @($flow.nodes | Where-Object { $_.type -notin $allowedTypes }).Count -eq 0 -and
        @($flow.nodes | Where-Object { $_.type -eq "command" -and $_.config.cmd -match $networkPattern }).Count -eq 0 -and
        @($flow.nodes | Where-Object { $_.type -eq "note" }).Count -gt 0
    })
    if ($eligible.Count -eq 0) { Stop-Smoke "the installed template catalog has no offline starter flow with a saved note" }
    $selected = $eligible[0]
    $templateId = [string]$selected.id
    $noteNode = @($selected.template.nodes | Where-Object { $_.type -eq "note" } | Select-Object -First 1)[0]
    $expectedRelative = ([string]$noteNode.config.path).Replace("{run}", "RUN_ID")
    if (-not $expectedRelative -or $expectedRelative.Contains("..")) { Stop-Smoke "the selected starter has no safe note output path" }

    $applied = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/starter/apply" `
        -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" `
        -Body (@{ template_ids = @($templateId); mode = [string]$proposal.mode } | ConvertTo-Json -Compress) -TimeoutSec 20
    $created = @($applied.created | Where-Object { $_.template_id -eq $templateId } | Select-Object -First 1)[0]
    if (-not $created.id) { Stop-Smoke "starter apply did not create the selected offline automation" }

    $startedAt = [DateTime]::UtcNow
    $started = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/environments/$([uri]::EscapeDataString([string]$created.id))/run" `
        -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body "{}" -TimeoutSec 20
    $runId = [string]$started.run_id
    if (-not $runId) { Stop-Smoke "the starter automation did not return a run id" }
    $run = $null
    $runDeadline = $startedAt.AddSeconds(120)
    while ([DateTime]::UtcNow -lt $runDeadline) {
        $run = Get-ApiJson "/api/runs/$([uri]::EscapeDataString($runId))" $token
        if ($run.status -in @("done", "failed", "rejected", "canceled")) { break }
        Start-Sleep -Milliseconds 500
    }
    $elapsed = [Math]::Round(([DateTime]::UtcNow - $startedAt).TotalSeconds, 2)
    if (-not $run -or $run.status -ne "done") {
        $explanation = if ($run) { ($run.outputs.GetEnumerator() | ForEach-Object { "$($_.Key): $($_.Value)" }) -join "`n" } else { "No run status was returned." }
        Stop-Smoke "starter run $runId ended '$($run.status)' after ${elapsed}s. Explanation: $(Safe-Text $explanation)"
    }
    $expectedPath = Join-Path $dataDir ("vault\" + $expectedRelative.Replace("RUN_ID", $runId).Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $expectedPath -PathType Leaf)) {
        $explanation = ($run.outputs.GetEnumerator() | ForEach-Object { "$($_.Key): $($_.Value)" }) -join "`n"
        Stop-Smoke "starter run $runId finished done, but its expected note '$expectedRelative' was not found. Explanation: $(Safe-Text $explanation)"
    }

    $installerVersion = (Get-Item -LiteralPath $Installer).VersionInfo.ProductVersion
    if (-not $installerVersion) { $installerVersion = "not set" }
    $pythonVersion = (& $python --version 2>&1 | Out-String).Trim()
    $evidence = @(
        "Glacier first automation evidence",
        "Installer version: $installerVersion",
        "Bundled Python: $pythonVersion",
        "Template id: $templateId",
        "Run id: $runId",
        "Status: $($run.status)",
        "Elapsed seconds: $elapsed",
        "Output: $expectedRelative"
    ) -join "`n"
    Set-Content -LiteralPath $evidencePath -Value $evidence -Encoding utf8
    Write-Host $evidence
    Write-Host "Windows desktop smoke test passed: installer, token protection, and an offline first automation succeeded."
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $backend.Id -Timeout 10 -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $installRoot) {
        $uninstaller = Join-Path $installRoot "uninstall.exe"
        if (Test-Path -LiteralPath $uninstaller -PathType Leaf) {
            $uninstall = Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait -PassThru
            if ($uninstall.ExitCode -ne 0) { Write-Error "Windows desktop smoke test failed: silent uninstall exited with $($uninstall.ExitCode)"; exit 1 }
        } else {
            Write-Error "Windows desktop smoke test failed: silent uninstaller was not found"
            exit 1
        }
    }
    Remove-Item Env:GLACIER_HOME, Env:GLACIER_LOCAL_MODEL, Env:GLACIER_MAX_PARALLEL_RUNS -ErrorAction SilentlyContinue
}
