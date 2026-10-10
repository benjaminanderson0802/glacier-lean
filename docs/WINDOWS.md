# Running Glacier on Windows

The Glacier backend suite runs on Windows with Python 3.13. The backend uses
Windows process groups to stop timed-out commands and a file lock to serialize
verified workspace merges. Git, Python, and the Python packages in
`setup/requirements.txt` must be available.

Configured command steps and command acceptance checks use Git Bash
(`bash` on `PATH`, or `C:\Program Files\Git\bin\bash.exe`). If Git Bash is
missing, Glacier reports a clear error so the command can be retried after Git
for Windows is installed. The Windows CI job also invokes the backend suite
through Git Bash and reports an explicit setup error if Bash is missing. Vault
paths returned by the API use `/` separators.

## Linux-only features

Per-step OS sandboxing uses Linux Landlock and seccomp. A command step configured
to use that sandbox cannot run sandboxed on Windows; Glacier reports this as a
step failure with a plain-language explanation. Linux-only sandbox enforcement
tests are skipped on Windows with a reason. POSIX process-group signal tests
are also Linux-only. Windows process-tree termination uses the built-in
`taskkill` command; `psutil` is not required.

Meaning search uses an optional SQLite vector extension. If SQLite denies
loading it, meaning search falls back to keyword results with a plain message;
extension-dependent meaning-index tests skip with the load error. Keyword
search remains available.

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

The unmasked Windows run reported **66 failed, 239 passed, 13 skipped**. Portability fixes for the grouped failures are:

| Count | First differing failure | Root cause / treatment |
|---:|---|---|
| 18 | `error: [WinError 193] %1 is not a valid Win32 application` and missing fake-agent outputs | Fake Python commands run through the current interpreter on Windows. ACP fixtures use `sys.executable`; POSIX wrappers remain in use on Linux. |
| 14 | `$((...))`, `mkdir -p`, `sh` command assertions; downstream run/verification/alert failures | Command steps and acceptance checks use Git Bash on Windows. They report a clear error if it is unavailable. Linux keeps its existing shell. |
| 9 | `sqlite3.OperationalError: not authorized` | Meaning search falls back to keyword results with a plain message; vector-dependent tests skip with the SQLite load error when the extension cannot load. |
| 8 | `notes\\...`, `runs\\...` compared with `notes/...`, `runs/...` | Windows vault input paths are normalized and logical paths use `/`. |
| 5 | `The step sandbox needs Linux; this step can't run sandboxed on Windows` where tests expect validation/errors | Landlock enforcement tests skip on Windows with a reason; sandbox requests retain their existing plain-language limitation. |
| 3 | Fake worker returns `cancelled`/502 or lacks assistant stream events | Covered by launching Python fake commands through the active interpreter. |
| 2 | `AttributeError: os.sysconf` and fake Ollama lookup failure | Windows RAM detection uses `GlobalMemoryStatusEx`; fake Ollama uses a Python fixture on Windows. |
| 2 | `CalledProcessError` for vault note containing `[run:abc]`; missing nested Windows-named file | Windows vault input paths are normalized and listed paths use `/`; compatibility fixtures seed restricted names through extended Windows paths. |
| 1 | Template manifest SHA mismatch | Repository text files use LF checkout rules so reviewed hashes remain identical on Windows and Linux. |
| 1 | `assert 3 == 4` in vault compatibility report | Re-evaluated after vault path normalization. |
| 1 | Claim research expected proposal/routing but got different status | Covered by launching the Python fake researcher through the active interpreter. |
| 1 | `KeyError: 'x'` in Codex route test | Covered by launching Python fakes through the active interpreter. |

Linux-only behavior remains limited to OS sandbox enforcement and POSIX process-group signals. Windows must receive a plain explanation when the user requests a Linux-only sandbox. The earlier Linux acceptance run passed **311 tests with 1 skip** on 2026-10-07. Two consecutive Windows backend runs passed on GitHub on 2026-10-07 (396 passed, 0 failed), so the Windows job is now blocking.

Compatibility tests account for Windows filename rules: backslashes in links resolve to nested notes, and events may include memory changes alongside node changes, so node-event checks select messages with `node_id`.
# Keep the source checkout running at sign-in

For the from-source development copy that uses `C:\Users\benja\glacier-dev-run.ps1` to launch
`glacier/web/scripts/live.mjs`, copy `setup/register_dev_logon.ps1` into the checkout or run it
from the repository root. It registers a Task Scheduler task for the current Windows user only;
it does not need administrator access. The task starts at the next sign-in and ignores a second
start if the first copy is still running.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup\register_dev_logon.ps1
```

To remove it, open Task Scheduler, select **Task Scheduler Library → Glacier Dev Backend**, and
choose **Delete**. This keeps the development copy independent of the installer's startup setting.
