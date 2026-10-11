---
id: CLM-2026-10-11-B-OFFLINE-PROOF-NETWORK-ISOLATION
filed_by: B-OFFLINE-PROOF
run_id: null
node_id: null
checkpoint: PH10.3
kind: environment
summary: This Linux container can run the pack installer under strict network denial, but cannot run the backend automation harness under that same policy because asyncio requires socketpair, and unshare network namespaces are denied.
evidence: evidence/backlog/B-OFFLINE-PROOF/RESULTS.md
attempts_made: 1
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

The offline pack was built and installed successfully with the existing Landlock/seccomp sandbox denying socket/network syscalls. To exercise a real deterministic flow from the installed source, I started an in-process FastAPI TestClient harness while retaining the same network-deny policy. Its asyncio event loop could not create its self-pipe: `socket.socketpair()` failed with `PermissionError: [Errno 1] Operation not permitted` before backend startup. A network namespace alternative is unavailable here: `unshare --net -- true` exits with `Operation not permitted`. The container has no installed bubblewrap, Firejail, nftables, or iptables executable to provide an egress-only policy while retaining loopback transport.

This is a harness/environment limitation, not evidence that the offline pack is broken. The live automation acceptance remains unproven. Resolve by running the evaluator in an OS environment that blocks external egress while allowing the backend's required local transport, then execute the no-model command/check/note flow documented in `evidence/backlog/B-OFFLINE-PROOF/RESULTS.md`. No product or check was modified.
