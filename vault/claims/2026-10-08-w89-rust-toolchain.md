---
id: CLM-2026-10-08-W89-RUST-TOOLCHAIN
filed_by: W89-declutter-shell
run_id: null
node_id: null
checkpoint: PH8.1
kind: environment
summary: Rust window capability test cannot run because Cargo is unavailable in this worker environment
evidence: "cargo test default_capability_allows_minimize_and_close_window_controls --lib returned cargo: command not found; searched /home/glacier, /usr/local, and /opt for an executable bin/cargo with no result"
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The Rust/config acceptance test has been added, but this worker has no Rust toolchain. Cargo is not on `PATH`, and no executable Cargo binary was found in the standard worker locations. The config permissions are still checked by the UI bridge test only for command calls, not by the Rust test. Run `cargo test default_capability_allows_minimize_and_close_window_controls --lib` in an environment with the Rust toolchain before closing this claim.
