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
