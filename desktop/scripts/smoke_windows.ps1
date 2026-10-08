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

function Stop-Smoke([string] $Message) {
    throw "Windows desktop smoke test failed: $Message"
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
    $env:GLACIER_LOCAL_MODEL = "qwen3:0.6b"
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

    Write-Host "Windows desktop smoke test passed: installer, backend readiness, and token checks succeeded."
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
