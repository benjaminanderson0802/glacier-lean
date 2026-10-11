# B-OFFLINE-PROOF results

Date: 2026-10-11
Checkpoint: PH10.3 (evaluator evidence only; no phase exit claim)
Platform: Linux x86_64, CPython 3.12.3
Lane: offline-evaluator

## Drift check

- Checkpoint: PH10.3. The phase ledger records PH10 as in progress with PH8 and PH9 also in progress; the card permits scoped evaluation before their exits, but this evidence does not claim a phase exit.
- Defining properties and metrics: P-PORTABLE and P-USABLE; M-LOCAL and M-VERIFIED.
- Existing-tool choice (I-01): use the existing offline builder/installer and the existing Landlock/seccomp OS sandbox. No installer, release pipeline, or isolation tool was added.
- Acceptance: run the unchanged offline unit suite, build the current Linux pack, install it in a fresh disposable destination with OS network access blocked, capture the manifest and installed versions, and run a deterministic automation from the shipped source/docs under the same network policy. The automation requirement remains open under the claim below.

## Acceptance defined before the run

1. Run the existing offline-pack tests unchanged.
2. Build the Linux pack from the current `setup/requirements.txt` pins; retain its manifest digest and wheel inventory.
3. Install the built pack into a fresh disposable destination while OS network syscalls are blocked. Record installed versions and installer output.
4. Run a deterministic, no-model automation from the installed source/docs in the same network-disabled environment, and retain the real run output.

## Results

- Fixture checks: `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/offline/test_offline.py` — **10 passed**. These tests mock pack downloads and install behavior; they are not live proof.
- Real pack build: `~/w/glacier-lean/.venv/bin/python setup/offline/build_pack.py --output /tmp/glacier-B-OFFLINE-PROOF-pack --python-version 3.12` — **passed**. The builder downloaded the resolved Linux wheels for CPython 3.12 from the pinned requirements.
- Pack: 86 wheels, 232 MB. Manifest SHA-256: `6064640dc9149e68e963b6ad049670380e27b2a48682105fe95e0749e8e940e7`. `MANIFEST.json`, `MANIFEST.sha256`, and `pack-requirements.txt` are retained beside this report. `installed-versions.txt` records the disposable install's package versions.
- Network-denial probe: **passed**. Under the same wrapper, `/usr/bin/python3.12 -c 'import socket; socket.socket(2, 1)'` failed with `PermissionError: [Errno 1] Operation not permitted`, as required.
- Real offline install: **passed**, exit 0. I copied the pack into `/tmp/glacier-B-OFFLINE-PROOF-isolated/pack` and ran its installer with the project Landlock/seccomp wrapper (`glacier/backend/sandboxing.py`), which denies socket/network syscalls. Installer command inside the wrapper:

  ```sh
  /usr/bin/python3.12 install_pack.py pack --destination installed --manifest-sha256 6064640dc9149e68e963b6ad049670380e27b2a48682105fe95e0749e8e940e7
  ```

  The installer printed the same digest, verified the pack, created the environment, installed all 86 wheels using `pip install --no-index --find-links`, and copied the shipped source. It reported `Python 3.12.3`, Node `v22.23.3`, npm `10.9.9`, and Git `2.43.0` ready. Optional tools `uv`, GitHub CLI, Codex, OpenCode, Gemini CLI, Docker, Cargo, and ntfy were absent and printed as not found. No model was claimed or used.
- Automation: **not completed**. I attempted the deterministic command → check → saved-note flow described by `docs/ACCEPTANCE.md`, using the installed backend through FastAPI's in-process TestClient and setting `GLACIER_SANDBOX=on`. The backend harness failed before startup: Python's asyncio loop could not create its self-pipe (`socket.socketpair()` raised `PermissionError: [Errno 1] Operation not permitted`) under the same seccomp policy. `unshare --net -- true` also fails with `Operation not permitted` in this container. The strict existing sandbox proves install-without-network, but this environment has no available OS isolation that blocks internet egress while preserving the local transport needed by the backend test harness. Claim `CLM-2026-10-11-B-OFFLINE-PROOF-NETWORK-ISOLATION` tracks the missing proof.

## Evidence boundary and remaining work

Real evidence: Linux pack build, manifest/member hashes, real disposable venv install under network-denying OS isolation, and installed package versions. Fixture evidence: the 10 existing mocked unit checks. No real automation output or local-model proof was produced. This Linux result does not establish Windows behavior. The integrator needs an evaluator environment that can deny external egress while allowing local backend transport; after that, rerun the deterministic automation against the installed source. Owner Windows proof remains a separate release/phase activity.

No files outside this card's evidence and claim scopes were changed. No PH10/NORTHSTAR status was changed. Anti-pattern review: no issue observed; this report records executed software evidence and the outstanding environment claim, rather than substituting for the missing automation run.
