# Install a Glacier build for review

Open PowerShell and run this line, replacing the path with the downloaded NSIS installer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/install_review_build.ps1 -Installer C:\Users\Ben\Downloads\Glacier_0.2.0_x64-setup.exe
```

The command closes Glacier and saves copies of `settings.json` and `sidecar.json`
beside its app data folder. It installs the build silently and starts Glacier.
Then it checks that the engine is ready, the installed version matches the
installer, and engine and route details are available. It checks that the
memory note count has not changed when a pre-install count was available, and
that the vault folder is unchanged. It prints a short pass/fail table and does
not remove user data.

To print the steps without running them:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/install_review_build.ps1 -Installer C:\Users\Ben\Downloads\Glacier_0.2.0_x64-setup.exe -DryRun
```
