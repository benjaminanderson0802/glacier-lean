# B-PIN-INVENTORY acceptance freeze

Frozen 2026-10-11 by an independent spec-only evaluator. The evaluator did not inspect implementation code or tests.

## Acceptance checks

1. Health report includes a read-only venture dependency inventory; inventory generation does not install or upgrade dependencies or modify manifests, lockfiles, or dependency state.
2. Discovery includes requirements manifests and npm lockfiles at nested venture paths. Each entry identifies its owning venture and source manifest path.
3. Python fixtures classify `pkg==1.2.3`, `pkg>=1.2`, and `pkg` as exact pin, range, and unpinned, preserving the source declaration.
4. npm fixtures report direct and transitive lock entries with locked versions, provenance, owning venture path, and source lockfile.
5. Missing expected manifests are reported with path and owning venture.

## File-expectation rule

The venture directory tree does not say that every venture must have a Python requirements file. An adjacent `package.json` is the concrete signal that `package-lock.json` is expected. A missing lock is reported, and its package declarations remain visible with no locked version. Existing manifests are scanned recursively; the inventory does not infer new requirements files.

## Scope notes

The inventory covers npm's nested `dependencies` lock structure (version 1) and `packages` lock structure (versions 2/3). A venture dependency absent from every existing manifest or lock cannot be inferred by this inventory. These checks provide card-level evidence only and do not claim a PH11.1 phase exit.
