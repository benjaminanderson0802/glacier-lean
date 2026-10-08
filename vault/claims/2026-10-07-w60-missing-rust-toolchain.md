---
id: W60-RUST-TOOLCHAIN
filed_by: W60-auto-update
run_id: W60-auto-update
node_id: null
checkpoint: PH8.1
kind: environment
summary: Rust/Cargo is absent from the W60 worktree environment, preventing updater lockfile generation and native compilation.
evidence: ["command -v rustc and command -v cargo returned no path", "search of /home/glacier and /usr/local found no executable cargo or rustc"]
attempts_made: 1
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

The updater crate was added to `desktop/src-tauri/Cargo.toml`, but this environment has no Rust toolchain. Cargo.lock therefore cannot be regenerated, and the Tauri changes cannot be compiled here. A Rust-enabled environment should run `cargo update` (or build the desktop app, which resolves dependencies) in `desktop/src-tauri`, review the lockfile diff, and run the desktop build.
