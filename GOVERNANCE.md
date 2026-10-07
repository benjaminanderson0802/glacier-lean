# Governance

Glacier's direction is set by [`NORTHSTAR.yaml`](NORTHSTAR.yaml). The project owner is the final decision-maker and approves changes to the mission, defining properties, invariants, non-goals, and phase exit criteria.

## North Star amendments

Anyone may propose a change. Record a diff in [`docs/AMENDMENTS.md`](docs/AMENDMENTS.md), with evidence (data or sources) and the metric it is expected to improve. The project owner reviews the proposal and must approve it before it takes effect. After approval, update `NORTHSTAR.yaml` and bump `last_amended`. A proposal does not take effect before approval. Workers may update checkpoint `status` and `evidence` after verification, and may add checkpoints that serve an existing phase exit; they may not change protected direction fields. All 15 invariants (I-01 through I-15) can change only by an approved amendment; I-14 also forbids agents from loosening safety rules.

## Maintainers and decisions

The project owner maintains the roadmap and makes owner decisions. The repository is public but the launcher has not been announced. The project uses Apache-2.0. Other current decisions are one app with Build and Run views, a Tauri desktop shell, and free-only defaults with a $0 monthly paid cap. The integrator coordinates assigned work, reviews changes, and merges only after the required checks pass. Maintainers help review and maintain the project within the North Star. Contributors propose changes and provide evidence; they do not make owner decisions.

The owner adds a maintainer by recording the appointment and scope in the project governance record. The owner may remove a maintainer by recording the change there. Maintainers may step down by telling the owner, who records the change. A maintainer cannot approve their own appointment or expand their own authority.

Decisions follow the evidence-over-opinion and smallest-step rules in `NORTHSTAR.yaml`. The owner resolves open decisions; maintainers coordinate work and reviews; contributors raise proposals and questions. Decisions that change protected North Star direction require the amendment process above.

## AI worker contributions

An AI worker may work only from an assigned card, on its named branch and listed paths. The card's acceptance test is written first. A worker does not edit, disable, or bypass the check that judges its work (I-03, I-04). Work is reviewed independently; the worker's report is not evidence. Merge requires review and passing CI and sandbox checks. Workers never weaken invariants, and gaps or out-of-lane problems are filed as claims under the North Star escalation rules (I-11, I-14, I-15, I-16).
