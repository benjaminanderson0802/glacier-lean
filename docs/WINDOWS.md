# Running Glacier on Windows

The Glacier backend suite runs on Windows with Python 3.13. The backend uses
Windows process groups to stop timed-out commands and a file lock to serialize
verified workspace merges. Git, Python, and the Python packages in
`setup/requirements.txt` must be available.

## Linux-only features

Per-step OS sandboxing uses Linux Landlock and seccomp. A command step configured
to use that sandbox cannot run sandboxed on Windows; Glacier reports this as a
step failure with a plain-language explanation. Linux-only sandbox enforcement
tests are skipped on Windows with a reason. POSIX process-group signal tests
are also Linux-only. Windows process-tree termination uses the built-in
`taskkill` command; `psutil` is not required.

## Run the backend tests

From a PowerShell prompt in the repository root:

```powershell
py -3.13 -m pip install -r setup/requirements.txt
git config --global user.email "ci@glacier.local"
git config --global user.name "glacier-ci"
Set-Location glacier/backend
py -3.13 -m pytest -q tests
```

The same test command runs in the `backend-windows` GitHub Actions job.

## CI failure triage (run 37622660999, 2026-10-07)

The unmasked Windows run reported **66 failed, 239 passed, 13 skipped**. Failures grouped by their first differing traceback/assertion are below. Groups may overlap when one root cause (for example, POSIX shell syntax) causes cascading workflow assertions.

| Count | First differing failure | Root cause / treatment |
|---:|---|---|
| 18 | `error: [WinError 193] %1 is not a valid Win32 application` and missing fake-agent outputs | Python test fixtures invoke extensionless `.py` fake Codex/ACP scripts as native Windows executables. Use `sys.executable` for Python fixtures, or make the product launch its configured command through the platform interpreter where that is the contract. |
| 14 | `$((...))`, `mkdir -p`, `sh` command assertions; downstream run/verification/alert failures | Tests and sample command flows assume a POSIX shell. Make portable test commands use Python/PowerShell on Windows; retain POSIX cases only where explicitly Linux-only and explain the skip. |
| 9 | `sqlite3.OperationalError: not authorized` | SQLite extension/vector-index authorization differs on Windows; isolate the unsupported extension path while retaining plain SQLite search behavior. |
| 8 | `notes\\...`, `runs\\...` compared with `notes/...`, `runs/...` | Path separators leak into vault/API identifiers and generated note links. Normalize logical vault paths to `/` at the boundary while using native paths for disk access. |
| 5 | `The step sandbox needs Linux; this step can't run sandboxed on Windows` where tests expect validation/errors | Linux-only Landlock/seccomp sandbox path masks earlier input-validation and network-policy outcomes. Preserve validation order and clearly skip enforcement-only tests on Windows; report a plain Windows limitation for actual sandbox execution. |
| 3 | Fake worker returns `cancelled`/502 or lacks assistant stream events | Fake worker process launch/response is failing under Windows; inspect its process invocation before treating assistant behavior as a separate issue. |
| 2 | `AttributeError: os.sysconf` and fake Ollama lookup failure | System check assumes POSIX memory APIs/path lookup; add Windows equivalents while preserving Linux behavior. |
| 2 | `CalledProcessError` for vault note containing `[run:abc]`; missing nested Windows-named file | Windows path/filename handling in vault operations needs a portable representation and native parent-directory creation. |
| 1 | Template manifest SHA mismatch | Content/hash drift, not an OS portability symptom; outside this card unless the file differs due to Windows line endings (verify before changing). |
| 1 | `assert 3 == 4` in vault compatibility report | A compatibility check expected a seeded Windows-specific issue but did not report it; inspect path handling and fixture setup. |
| 1 | Claim research expected proposal/routing but got different status | No clear OS symptom in the traceback; defer as non-portability unless a Windows-only failure is reproduced. |
| 1 | `KeyError: 'x'` in Codex route test | Downstream fake Codex launch/result failure; likely covered by the subprocess group. |

Linux-only behavior remains limited to OS sandbox enforcement and POSIX process-group signals. Windows must receive a plain explanation when the user requests a Linux-only sandbox. The workflow keeps `continue-on-error` until two consecutive Windows backend runs pass.
