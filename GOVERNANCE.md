# Governance

Glacier's direction is set by [`NORTHSTAR.yaml`](NORTHSTAR.yaml). The project owner is the final decision-maker and approves changes to the mission, defining properties, invariants, non-goals, and phase exit criteria.

## North Star amendments

Anyone may propose a change. Record the proposed diff in [`docs/AMENDMENTS.md`](docs/AMENDMENTS.md), with evidence (data or sources) and the metric it is expected to improve. The owner decides whether to approve it. After approval, update `NORTHSTAR.yaml` and bump `last_amended`. Do not make a proposed policy change effective before approval. Workers may update checkpoint `status` and `evidence` after verification, and may add checkpoints that serve an existing phase exit; they may not change the protected direction fields. Invariants can never be weakened to make work pass (I-14).

## Maintainers and decisions

The project owner maintains the roadmap and makes owner decisions. The integrator coordinates assigned work, reviews changes, and merges only after the required checks pass. A maintainer may help with review and upkeep, but cannot override the North Star or an owner decision. Open decisions stay with the owner; contributors record questions rather than deciding them.

## AI worker contributions

An AI worker may work only from an assigned card, on its named branch and listed paths. The card's acceptance test is written first. A worker does not edit, disable, or bypass the check that judges its work (I-03, I-04). Work is reviewed independently; the worker's report is not evidence. Merge requires review and passing CI and sandbox checks. Workers never weaken invariants, and gaps or out-of-lane problems are filed as claims under the North Star escalation rules (I-11, I-14, I-15, I-16).
