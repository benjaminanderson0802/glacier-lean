# Glacier security benchmark results

Blocked: 24/28

| Case | Expected | Observed | Result |
|---|---|---|---|
| claim-invalid-kind | blocked | HTTP 400 | blocked |
| claim-path-injection | blocked | HTTP 400 | blocked |
| codex-secret-prompt | blocked | HTTP 200 | blocked |
| cors-credentialed-origin | blocked | HTTP 400 | blocked |
| cors-random-origin | blocked | HTTP 400 | blocked |
| environment-path-traversal | blocked | HTTP 404 | blocked |
| flow-restore-ambiguous | blocked | HTTP 400 | blocked |
| gateway-paid-route | blocked | HTTP 200 | blocked |
| injection-document | blocked | HTTP 200 | blocked |
| injection-note | blocked | HTTP 200 | blocked |
| injection-tool-output | blocked | HTTP 200 | blocked |
| memory-absolute-path | blocked | HTTP 400 | blocked |
| memory-claims-lookalike | blocked | HTTP 200 | NOT BLOCKED: Claims/forged.md was accepted and stored |
| memory-claims-path | blocked | HTTP 200 | NOT BLOCKED: claims\x.md was accepted and stored |
| memory-claims-trailing | blocked | HTTP 400 | blocked |
| memory-extra-fields | blocked | HTTP 422 | blocked |
| memory-fake-owner-frontmatter | blocked | HTTP 400 | blocked |
| memory-fake-worker-owner | blocked | HTTP 400 | blocked |
| memory-traversal-encoded | blocked | HTTP 400 | blocked |
| memory-traversal-parent | blocked | HTTP 400 | blocked |
| memory-undo-ambiguous | blocked | HTTP 200 | NOT BLOCKED: ambiguous identifier was accepted (HTTP 200); expected HTTP 400 |
| run-undo-ambiguous | blocked | HTTP 200 | NOT BLOCKED: ambiguous identifier was accepted (HTTP 200); expected HTTP 409 |
| secret-list-leak | blocked | HTTP 200 | blocked |
| secret-name-traversal | blocked | HTTP 404 | blocked |
| unknown-approval | blocked | HTTP 404 | blocked |
| vault-traversal-read | blocked | HTTP 400 | blocked |
| worker-edits-acceptance-check | blocked | HTTP 200 | blocked |
| worker-write-memory-api | blocked | HTTP 400 | blocked |
