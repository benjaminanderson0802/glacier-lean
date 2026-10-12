---
id: CLM-2026-10-10-E-PH9-UI-DEPENDENCIES
filed_by: E-PH9
run_id: null
node_id: null
checkpoint: PH9.1
kind: environment
summary: Shared web node_modules lacks pinned TypeScript, blocking PH9 screen checks
evidence: evidence/ph9/i18n.log; evidence/ph9/tsc.log; evidence/ph9/web-build.log
attempts_made: 0
status: resolved
assigned_to: fixer
resolution: Installed the exact committed web lockfile in a private temporary directory; shared dependencies unchanged
resolution_evidence: evidence/ph9/npm-ci.log; evidence/ph9/tsc-isolated.log; evidence/ph9/theme-isolated.log; evidence/ph9/i18n-isolated.log; evidence/ph9/web-build-isolated.log
---

The card's existing node_modules link targets the shared web dependency directory, which has no typescript/package.json. Theme lint passes; translation parity, type checking, and build cannot load TypeScript. No project source or acceptance check was changed.

Known remedy: vault/claims/2026-10-08-w89-ui-dependencies.md recommends installing the committed lockfile in an isolated dependency directory. This card will try that existing remedy without modifying shared dependencies or package pins; the maintenance clone will use that same isolated directory. No paid service or new dependency is involved.

The private install succeeded (203 packages). Type checking, theme lint, translation parity, and the production build then passed. Browser checks are recorded separately. The original failed logs are retained.
