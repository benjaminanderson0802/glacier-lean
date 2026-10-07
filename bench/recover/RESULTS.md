# Recovery benchmark results

Local backend, fake Codex executable, HTTP API requests. Recovery latency starts immediately before the undo/restore request and ends after independent file-state verification.

Audit coverage: 98.48% (65/66 expected side effects found)

| Scenario | Recovery time | Restored state | Audit entries expected/found | Result |
|---|---:|---|---:|---|
| run_notes | 0.414 s | PASS | 51/51 | PASS |

run_notes detail: one run; vault snapshot compared; 50 note files removed; run audit paths=50; undo commits=1
| flow_restore | 0.024 s | PASS | 11/11 | PASS |

flow_restore detail: restored exact original bytes; vault snapshot compared; edits=10; restore commits=1; edited hash ba8d2ae34719 -> 7f16c994e80b
| memory_undo | 120.000 s | FAIL | 2/2 | FAIL |

memory_undo detail: restored exact prior hash 5a9fa3932179; vault snapshot compared; undo commits=1; recovery error: undo overwritten memory note: timed out after 120.000 s waiting for restored state
| isolated_code_undo | 120.000 s | FAIL | 2/1 | FAIL |

isolated_code_undo detail: workspace changed files=1; git audit paths=1; undo commits=0; undo endpoint audits vault only; workspace hash 9160d4be34c8 -> 7b9a72466d39 -> 7b9a72466d39; recovery error: Glacier API POST /api/runs/e84651851f27/undo returned 404: {"detail":"No saved changes were found for run e84651851f27."}; undo isolated coding run: timed out after 120.000 s waiting for restored state

Threshold: each recovery <= 120 s; total audit coverage 100%.
Overall: FAIL
