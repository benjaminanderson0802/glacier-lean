# Property tax appeals progress

PH12.17 remains in progress. The Cook County representation question is addressed for this narrow product scope: the Assessor allows pro se filing, and an individual taxpayer may represent themselves before the Board of Review for property titled in their own name. See [DECISION.md](DECISION.md) for the comparison of self-file assist, an attorney partner, and Assessor-only scope.

The packet script now sets `filing_mode` to `homeowner_self_file` and generates a separate `*-filing-guide.md` alongside the packet. The guide points to the current Assessor and Board portals and township calendar, limits Board pro se instructions to individually titled property, and leaves review, choice, signatures, submission, and follow-up to the homeowner. No account, payment, signature, county filing, or mailing is automated.

Customer-facing launch has two core steps: provide the notice and valuation evidence; review the packet and guide, then personally file if desired. Texas work and postcard mailing are optional future actions; Texas remains disabled and live mailing stays disabled. Paid checkout also stays disabled until the owner confirms pricing.

Fixture test coverage verifies the self-file packet/guide behavior. Existing live evidence is narrower: a single public parcel row was normalized, and an earlier incomplete case smoke run returned `uncertain — please check`. The full roll is not synced, no customer documents were available, and the real Glacier packet flow has not succeeded because the runner failed before script execution; see claim `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT`. Refer to [PROOF.md](PROOF.md) for commands and evidence boundaries.
