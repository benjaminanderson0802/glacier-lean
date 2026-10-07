"""OS-enforced command sandboxing for individual Glacier steps.

Linux uses Landlock for filesystem access and seccomp to deny socket use. This
module intentionally fails closed when the kernel cannot enforce that policy.
"""

import ctypes
import errno
import os
import platform
import subprocess
import sys


_LANDLOCK_CREATE_RULESET = 444
_LANDLOCK_ADD_RULE = 445
_LANDLOCK_RESTRICT_SELF = 446
_LANDLOCK_RULE_PATH_BENEATH = 1
_LANDLOCK_ACCESS_FS = {
    "execute": 1 << 0,
    "write_file": 1 << 1,
    "read_file": 1 << 2,
    "read_dir": 1 << 3,
    "remove_dir": 1 << 4,
    "remove_file": 1 << 5,
    "make_char": 1 << 6,
    "make_dir": 1 << 7,
    "make_reg": 1 << 8,
    "make_sock": 1 << 9,
    "make_fifo": 1 << 10,
    "make_block": 1 << 11,
    "make_sym": 1 << 12,
    "refer": 1 << 13,
    "truncate": 1 << 14,
}
_LANDLOCK_ACCESS_NET_BIND_TCP = 1 << 0
_LANDLOCK_ACCESS_NET_CONNECT_TCP = 1 << 1
_PR_SET_NO_NEW_PRIVS = 38
_PR_SET_SECCOMP = 22
_SECCOMP_MODE_FILTER = 2
_SECCOMP_RET_ALLOW = 0x7FFF0000
_SECCOMP_RET_ERRNO = 0x00050000
_BPF_LD_W_ABS = 0x20
_BPF_JMP_JEQ_K = 0x15
_BPF_RET_K = 0x06


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64), ("handled_access_net", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
        ("reserved", ctypes.c_uint32),
    ]


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(_SockFilter))]


def _syscall(number, *args):
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(number, *args)
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def _landlock_abi():
    # Linux assigns these syscall numbers consistently across its supported
    # generic syscall architectures.
    return _syscall(_LANDLOCK_CREATE_RULESET, None, 0, 1)


def _filesystem_rights(abi):
    names = list(_LANDLOCK_ACCESS_FS)
    if abi < 2:
        names.remove("refer")
    if abi < 3:
        names.remove("truncate")
    return sum(_LANDLOCK_ACCESS_FS[name] for name in names)


def _add_path_rule(ruleset_fd, path, rights):
    path_fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    try:
        attr = _PathBeneathAttr(rights, path_fd, 0)
        _syscall(_LANDLOCK_ADD_RULE, ruleset_fd, _LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(attr), 0)
    finally:
        os.close(path_fd)


def _install_seccomp_network_deny():
    """Deny all socket and network syscalls, including UDP and raw sockets."""
    machine = platform.machine().lower()
    syscall_numbers = {
        "x86_64": (41, 42, 43, 44, 45, 46, 47, 49, 50, 53, 288, 299, 307, 425),
        "amd64": (41, 42, 43, 44, 45, 46, 47, 49, 50, 53, 288, 299, 307, 425),
        "aarch64": (198, 203, 202, 206, 207, 211, 212, 200, 201, 199, 242, 269, 243, 425),
        "arm64": (198, 203, 202, 206, 207, 211, 212, 200, 201, 199, 242, 269, 243, 425),
    }
    denied = syscall_numbers.get(machine)
    if denied is None:
        raise RuntimeError(f"socket blocking is not configured for Linux architecture {machine}")

    instructions = [_SockFilter(_BPF_LD_W_ABS, 0, 0, 0)]  # seccomp_data.nr
    for number in denied:
        instructions.append(_SockFilter(_BPF_JMP_JEQ_K, 0, 1, number))
        instructions.append(_SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM))
    instructions.append(_SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ALLOW))
    filter_array = (_SockFilter * len(instructions))(*instructions)
    program = _SockFprog(len(instructions), filter_array)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(_PR_SET_SECCOMP, _SECCOMP_MODE_FILTER, ctypes.byref(program), 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _apply_policy(workdir):
    abi = _landlock_abi()
    if abi < 4:
        raise RuntimeError(f"Landlock ABI {abi} lacks TCP network restrictions (need ABI 4)")

    fs_rights = _filesystem_rights(abi)
    net_rights = _LANDLOCK_ACCESS_NET_BIND_TCP | _LANDLOCK_ACCESS_NET_CONNECT_TCP
    attr = _RulesetAttr(fs_rights, net_rights)
    ruleset_fd = _syscall(_LANDLOCK_CREATE_RULESET, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    try:
        readonly = (
            _LANDLOCK_ACCESS_FS["execute"]
            | _LANDLOCK_ACCESS_FS["read_file"]
            | _LANDLOCK_ACCESS_FS["read_dir"]
        )
        writable = readonly | _LANDLOCK_ACCESS_FS["write_file"]
        for name in ("remove_dir", "remove_file", "make_char", "make_dir", "make_reg", "make_sock", "make_fifo", "make_block", "make_sym", "refer", "truncate"):
            if name in _LANDLOCK_ACCESS_FS and (abi >= (2 if name == "refer" else 3 if name == "truncate" else 1)):
                writable |= _LANDLOCK_ACCESS_FS[name]

        workdir = os.path.realpath(workdir)
        if not os.path.isdir(workdir):
            raise ValueError(f"work directory does not exist: {workdir}")
        _add_path_rule(ruleset_fd, workdir, fs_rights)

        # Expose only common OS/runtime trees, and only for reads and execution.
        for path in ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/opt", "/dev"):
            if os.path.exists(path):
                _add_path_rule(ruleset_fd, path, readonly)

        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        _syscall(_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0)
    finally:
        os.close(ruleset_fd)

    _install_seccomp_network_deny()


def _exec_command(command, workdir):
    _apply_policy(workdir)
    os.chdir(os.path.realpath(workdir))
    os.execvpe("/bin/sh", ["/bin/sh", "-c", command], os.environ.copy())


def _probe():
    """Probe enforcement in a child because Landlock restrictions are permanent."""
    if not sys.platform.startswith("linux"):
        return False, "per-step sandbox is not implemented on this operating system"
    if not hasattr(os, "O_PATH"):
        return False, "this Python build does not expose Linux O_PATH"
    bootstrap = (
        "import importlib.util,os; "
        f"s=importlib.util.spec_from_file_location('glacier_sandbox_probe',{os.path.abspath(__file__)!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "m._apply_policy(os.getcwd())"
    )
    result = subprocess.run(
        [sys.executable, "-c", bootstrap],
        cwd=os.getcwd(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        reason = detail[-1] if detail else "kernel refused required security syscalls"
        return False, f"kernel refused Landlock filesystem or seccomp network restrictions: {reason}"
    return True, "Linux Landlock and seccomp restrictions are available"


def available():
    """Return whether this host can enforce the sandbox and a plain reason."""
    try:
        return _probe()
    except (OSError, RuntimeError, ValueError) as exc:
        return False, str(exc)


def wrap(cmd: str, workdir: str, allow_hosts: list[str]) -> list[str]:
    """Return argv that executes a shell command with OS-enforced restrictions.

    Host allowlisting requires a filtered proxy and is deliberately rejected
    until that proxy is implemented. This avoids accidentally granting egress.
    """
    if not isinstance(cmd, str) or not cmd:
        raise ValueError("command must be a non-empty string")
    if allow_hosts:
        raise NotImplementedError("allowed-host networking needs an allowlisting proxy; direct network stays blocked")
    if not isinstance(workdir, str) or not workdir:
        raise ValueError("work directory must be a non-empty path")
    available_now, reason = available()
    if not available_now:
        raise RuntimeError(f"OS sandbox unavailable: {reason}")

    module_path = os.path.abspath(__file__)
    bootstrap = (
        "import importlib.util,sys; "
        f"s=importlib.util.spec_from_file_location('glacier_sandboxing',{module_path!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "m._exec_command(sys.argv[1],sys.argv[2])"
    )
    return [sys.executable, "-c", bootstrap, cmd, os.path.abspath(workdir)]
