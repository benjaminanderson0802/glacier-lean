---
id: CLM-2026-10-11-C-ROOM-VISUAL-TESTER-PINNED-WEB-DEPENDENCIES-MISSING
filed_by: C-ROOM-VISUAL-TESTER
run_id: card/gf-C-ROOM-VISUAL-TESTER
node_id: null
checkpoint: PH5.4 / PH12.1
kind: environment
summary: Web dependencies are absent from the card worktree, blocking the requested build and room captures
evidence: "glacier/web: `npm run build` exits 127 (`sh: 1: tsc: not found`); `npm ls typescript vite playwright --depth=0` reports an empty tree; `node_modules/.bin` does not exist. `package.json` declares pinned TypeScript 6.0.3, Vite 8.3.3, and Playwright 1.63.0. No lockfile was changed."
attempts_made: 0
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

The worktree has an untracked `glacier/web/node_modules` directory, but it contains no installed packages. The requested `npm run build` was used to reproduce the issue; package inspection confirmed that the local dependency tree is empty. No install or lockfile edit was attempted. The independent evaluator spec has been added, but it cannot be built or executed until the pinned dependencies are restored in this worktree.
