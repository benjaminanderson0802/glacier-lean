# C-PH1-AUDIT-TESTER acceptance plan

## Drift check

1. **Checkpoint:** PH1 exit; the exit requires M-AUDIT = 100% for runtime side effects.
2. **Dependency:** PH1 depends on PH0, which NORTHSTAR.yaml marks done. This is assigned independent exit evidence work; it does not change checkpoint status.
3. **Properties and metrics:** P-CONTROL and P-VERIFY; M-AUDIT and M-RECOVER.
4. **Existing tools:** the event log, DBOS durable steps, SQLite and pytest already exist. No new audit system is proposed.
5. **Acceptance, written before implementation:** for each local command effect, the command must be able to observe its durable correlated start before writing its temporary marker; each known success/failure and retry attempt must have a correlated outcome; interruption after an effect must be explicitly interrupted or unknown; unavailable audit storage must be visible and must not appear as fully audited success.

The fake command writes only under pytest's temporary directory. Audit reads are read-only. No runtime implementation, existing acceptance check, shared contract, NORTHSTAR status, or other path was changed.
