# Per-step sandbox research and current support

Research checked 2026-10-07. This card advances PH7.1 (per-node sandbox with
file and network allowlists), serves P-SECURE, and uses filesystem, network and
exit-status acceptance tests in `glacier/backend/tests/test_sandboxing.py`.
PH7 depends on PH3, which has not exited yet; ORCHESTRATION.yaml assigns PH7.1
to wave 3 and permits assigned cards to start before a dependency exits. The
phase cannot be marked complete here. The system already has ordinary process
execution, but it has no file/network isolation tool wired for command steps.
An OS-enforced sandbox is needed because a shell wrapper alone cannot enforce
these boundaries.

## Options reviewed

| Option | License and maintenance | Privileges / Codespace fit | Assessment |
| --- | --- | --- | --- |
| bubblewrap (`bwrap`) | LGPL-2.0-or-later; active upstream project | Usually unprivileged through Linux user namespaces. This Codespace has bwrap 0.12.0, but namespace creation is denied by the outer container. | Strong filesystem and network namespaces where enabled; unusable in this Codespace. |
| Firejail | GPL-2.0; active project, latest release/security policy describes supported latest version | Common setups use a setuid helper or user namespaces; availability in a nested Codespace is not dependable. | Mature profiles and network controls, but the install/privilege model is a worse fit here. |
| nsjail | Apache-2.0; active Google-hosted repository (not an official Google product) | Namespace/cgroup/seccomp setup commonly requires host capabilities; not installed here and not a reliable nested-container option. | Broad controls, but adds an external runtime and does not solve this environment's namespace restriction. |
| Landlock | Linux kernel facility (no separately bundled dependency); upstream kernel maintained | Unprivileged self-restriction; works inside the current Codespace kernel. | Selected for Linux: current kernel reports ABI 4, enough for filesystem controls and TCP bind/connect denial. No host namespace is needed. |
| Rootless Docker / Podman | Docker Engine is Apache-2.0; Podman is Apache-2.0; both actively maintained | No daemon root for rootless modes, but subordinate UID/GID mappings and host support are required. Nested container runtime support is not available by default in a Codespace. | Capable but larger operational footprint and not an available runtime here. |
| Windows Sandbox | Windows feature, not a redistributable OSS dependency | Requires supported Windows edition, virtualization and enabling the feature; not suitable inside a Linux Codespace. Networking is enabled by default and mapped folders are the sharing boundary. | Useful disposable VM on a user's Windows PC, but too coarse for per-command host allowlists. |
| Windows AppContainer | Windows platform API | Can grant a process specific filesystem access and network capabilities; requires Windows-specific process-token integration, unavailable in this Linux Codespace. | Best Windows direction for a future native implementation; network capabilities are broad categories, not host-name allowlists. |
| Windows Job Objects | Windows platform API | Can be assigned during process creation without administrator rights in ordinary cases; usable on Windows, not in this Codespace. | Useful for child-process lifetime/resource limits, but does not itself confine files or network. It is complementary, not a sandbox by itself. |

Sources: [bubblewrap project and design](https://github.com/containers/bubblewrap),
[Firejail license](https://github.com/netblue30/firejail/blob/master/COPYING),
[Firejail supported releases](https://github.com/netblue30/firejail/security),
[nsjail project](https://github.com/google/nsjail), [nsjail Apache license](https://github.com/google/nsjail/blob/master/LICENSE),
[Linux Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html),
[Docker rootless prerequisites](https://docs.docker.com/engine/security/rootless/),
[Podman rootless setup](https://docs.podman.io/en/latest/markdown/podman.1.html),
[Windows Sandbox requirements](https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/system-requirements),
[Windows Sandbox configuration and networking](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-configure-using-wsb-file),
[AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation),
[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Implementation choice and boundaries

## Using the sandbox

Sandboxing is off by default for now. Set `sandbox: "on"` on a command step,
set `sandbox: "on"` on the flow to apply it to command steps without their own
setting, or set `GLACIER_SANDBOX=on` to require it for all command steps. The
environment setting is a floor: a step cannot turn it off. Only `on` and `off`
are accepted. The step workspace is the only writable folder. Network access
stays blocked by default. A sandboxed step that asks for `network: "allow"`
fails clearly until a filtered proxy is available; it never gets unrestricted
network access.

Codex keeps its own sandbox mode. `GLACIER_CODEX_SANDBOX` supplies the default
for Codex steps that do not choose a mode; an explicit `sandbox` setting on a
Codex step takes precedence.

Linux uses Landlock directly through the standard-library `ctypes` interface.
The wrapper process restricts itself and then replaces itself with `/bin/sh
-c <cmd>`. The work directory is read/write; common system executable and
configuration trees are read-only. Other filesystem locations are denied.
The child receives only `PATH`, `HOME`, `TMPDIR`, and `LANG` by default.
Landlock ABI 6 scopes signal delivery and abstract Unix sockets to the sandbox.
On older ABIs, the bootstrap starts a new session before applying seccomp.
Seccomp rejects `kill`, `tkill`, and `tgkill` when the target is `-1`, and
rejects `pidfd_send_signal`, `rt_sigqueueinfo`, and `rt_tgsigqueueinfo`
outright. Seccomp cannot distinguish other target pids, so below Landlock ABI
6 a command can still signal a specific same-user process if it knows that
process's pid. Landlock ABI 6 scopes signal delivery to the sandbox process
tree. `/dev/urandom` is exposed read-only; `/dev/null`, `/dev/zero`, and
`/dev/tty` (when present) receive file-only read/write and truncate rights.
This fallback cannot isolate abstract Unix sockets from other host processes.
The `TRUNCATE` right on writable devices is needed for shell output
redirection; directory rights cannot be granted on a single device file.
The kernel's TCP connect/bind rights are handled without granting any ports,
so the current implementation blocks network access for every command.
`allow_hosts=[]` is supported. A non-empty `allow_hosts` raises a clear
`NotImplementedError`: hostname allowlisting needs a separately confined,
observable proxy and a way to prevent direct egress while allowing only that
proxy. Implementing that proxy is follow-up work; silently granting network
would violate I-05.

`available()` probes actual Landlock enforcement in a short-lived child, not
just the presence of a library or kernel version. Unsupported kernels and
blocked security syscalls return `False` with the reason; the caller must not
run the command unsandboxed.

Windows is not implemented in this card. The future Windows adapter should
use AppContainer for per-process file/network permissions and a Job Object for
child-process cleanup. It must not claim per-host allowlisting until an
explicit filtering proxy or equivalent enforcement is implemented.

Anti-pattern review: this is a small OS adapter, not a new orchestration or
governance layer. No existing sandbox was present that provided these controls
in the Codespace. The selected kernel feature is already present and maintained
as part of Linux; the custom code is only the glue needed to express Glacier's
per-step policy. No phase status is changed by this card.
