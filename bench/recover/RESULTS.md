# Recovery benchmark results

Local backend, fake Codex executable, HTTP API requests. Recovery latency starts immediately before the undo/restore request and ends after independent file-state verification.

Audit coverage: 100.00% (66/66 expected side effects found)

| Scenario | Recovery time | Restored state | Audit entries expected/found | Result |
|---|---:|---|---:|---|
| run_notes | 0.488 s | PASS | 51/51 | PASS |

run_notes detail: one run; vault snapshot compared; 50 note files removed; run audit paths=50; undo commits=1
| flow_restore | 0.024 s | PASS | 11/11 | PASS |

flow_restore detail: restored exact original bytes; vault snapshot compared; edits=10; restore commits=1; edited hash fbc4d2143353 -> 8ddd8d33dfd2
| memory_undo | 0.020 s | PASS | 2/2 | PASS |

memory_undo detail: restored exact prior hash d2c1b924982a; vault snapshot compared; undo commits=1
| isolated_code_undo | 0.188 s | PASS | 2/2 | PASS |

isolated_code_undo detail: workspace changed files=1; git audit paths=1; workspace undo commits=1; workspace hash 9160d4be34c8 -> 7b9a72466d39 -> 9160d4be34c8

Threshold: each recovery <= 120 s; total audit coverage 100%.
Overall: PASS
