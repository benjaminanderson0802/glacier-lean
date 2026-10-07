# Recovery benchmark results

Local backend, fake Codex executable, HTTP API requests. Recovery latency starts immediately before the undo/restore request and ends after independent file-state verification.

Audit coverage: 98.39% (61/62 expected side effects found)

| Scenario | Recovery time | Restored state | Audit entries expected/found | Result |
|---|---:|---|---:|---|
| run_notes | 0.404 s | PASS | 50/50 | PASS |

run_notes detail: one run; 50 note files hashed and removed; audit paths=50
| flow_restore | 0.022 s | PASS | 10/10 | PASS |

flow_restore detail: restored hash 4bd69d7a0f68 -> 053f3c227302 content=original
| memory_undo | 0.022 s | PASS | 1/1 | PASS |

memory_undo detail: restored exact prior hash e639d260ce27
| isolated_code_undo | 0.200 s | FAIL | 1/0 | FAIL |

isolated_code_undo detail: workspace changed files=1; API audit changes=0; workspace hash 9160d4be34c8 -> 7b9a72466d39 -> 7b9a72466d39; recovery error: Glacier API POST /api/runs/8256bf00b193/undo returned 404: {"detail":"No saved changes were found for run 8256bf00b193."}

Threshold: each recovery <= 120 s; total audit coverage 100%.
Overall: FAIL
