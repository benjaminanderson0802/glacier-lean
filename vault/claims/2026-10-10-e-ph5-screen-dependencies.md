---
id: CLM-2026-10-10-E-PH5-SCREEN-DEPS
filed_by: E-PH5
run_id: null
node_id: null
checkpoint: PH5.1
kind: environment
summary: Shared web node_modules lacks TypeScript, blocking required screen checks
evidence: null
attempts_made: 0
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

`glacier/web/node_modules` is a pre-existing symlink to
`/home/glacier/w/glacier-lean/glacier/web/node_modules`. Its `.bin/tsc` is absent.
`npx tsc -b` prints "This is not the tsc command you are looking for";
`node scripts/check-i18n.mjs --fail` fails with ERR_MODULE_NOT_FOUND for typescript.
Theme lint passes (52 files). Build/browser verification needs the pinned dependencies
restored by the environment lane. E-PH5 did not replace the shared dependency tree or
edit the lockfile. See evidence/E-PH5/typescript.log.
