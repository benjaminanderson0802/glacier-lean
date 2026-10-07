# Public release checklist

Complete this checklist before the owner makes the repository public or announces a usable release. The owner gives the final sign-off; preparing this list does not authorize publishing.

## License and source

- [ ] `LICENSE` contains the approved Apache-2.0 license text; source and redistributed assets have clear license and attribution notices where required.
- [ ] Dependency and bundled-component licenses are reviewed against North Star invariant I-10; no unapproved restrictive or non-redistributable component is bundled.
- [ ] The public repository contents and release notes match the approved scope and do not expose private work or user data.

## Secrets and security

- [ ] Scan the repository and its full Git history for credentials, tokens, private keys, and other secrets with [Gitleaks](https://github.com/gitleaks/gitleaks), an open-source scanner. From the repository root, run `gitleaks git --redact`; review findings, rotate any exposed credential, and remove it from history before publication.
- [ ] Confirm secrets are handled through the documented secret store and are absent from prompts, logs, claims, and memory.
- [ ] Run the prompt-injection / lethal-trifecta security benchmark. Confirm M-SECURITY is at 100% and there are zero unauthenticated listeners.
- [ ] Confirm private vulnerability reporting and the reporting instructions in [`../SECURITY.md`](../SECURITY.md) are ready for public use.

## Product and documentation

- [ ] The backend, UI, end-to-end, and release-specific test suites pass. Record the exact commands and results with release evidence.
- [ ] All three benchmarks (verification, security, and survival) are green and their results are recorded.
- [ ] User documentation, setup instructions, supported-version policy, governance, contribution steps, and release notes are current and their relative links resolve.
- [ ] State the desktop app status clearly: the current Tauri build is a scaffold and is not ready for users; describe which platforms have a usable installer, which are unsupported or experimental, and any known limitations using [`DESKTOP.md`](DESKTOP.md) as the current status reference. Do not imply that an unfinished desktop build is ready.
- [ ] Confirm the release meets applicable North Star exit criteria; do not claim a phase is complete without linked evidence.

## Approval

- [ ] The owner adds a real security contact to [`../SECURITY.md`](../SECURITY.md) and a real conduct contact to [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) before the repository goes public.
- [ ] The owner reviewed the license, security results, test and benchmark evidence, documentation, and desktop status.
- [ ] The owner explicitly signs off on making the repository public and on the release announcement.
