"""Per-domain advisory lock: safe for unattended long-hours operation.

Prevents two gate invocations from racing the same domain (cron overlap,
fleet card + human tick). Crash-safe by design:
  - lock file holds pid + hostname + timestamp
  - if the owning process no longer exists, the lock is STALE and stolen
  - always released in a finally block
"""
from __future__ import annotations

import errno
import json
import os
import socket
import time
from pathlib import Path


class DomainBusy(Exception):
    def __init__(self, info: dict):
        self.info = info
        super().__init__(f"domain locked by pid {info.get('pid')} "
                         f"since {info.get('acquired')}")


def _alive(pid: int) -> bool:
    """Windows-safe liveness probe."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            out = subprocess_alive(pid)
            return out
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True     # exists but owned by someone else
    except ProcessLookupError:
        return False
    except OSError:
        return True     # can't tell -> assume alive (safety)


def subprocess_alive(pid: int) -> bool:
    try:
        import ctypes
        k32 = ctypes.windll.kernel32          # type: ignore[attr-defined]
        h = k32.OpenProcess(0x100000, False, pid)   # PROCESS_QUERY_LIMITED
        if not h:
            return False
        k32.CloseHandle(h)
        return True
    except Exception:
        return True   # cannot tell -> assume alive


def acquire(domain_dir: Path, timeout_s: float = 0) -> Path:
    lock = Path(domain_dir) / ".lock"
    Path(domain_dir).mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout_s

    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "acquired": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }).encode())
            os.close(fd)
            return lock
        except FileExistsError:
            pass
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        # examine the existing lock
        try:
            info = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            info = {}
        owner_pid = int(info.get("pid", -1))
        if not _alive(owner_pid):
            # STALE -> steal it (crashed owner)
            lock.unlink(missing_ok=True)
            continue

        if time.time() >= deadline:
            raise DomainBusy(info)

        time.sleep(1.0)


def release(lock: Path) -> None:
    try:
        lock.unlink(missing_ok=True)
    except OSError:
        pass


class domain_lock:
    """Context manager: with domain_lock(Path('domains/coding')) as lk: ..."""

    def __init__(self, domain_dir: Path, timeout_s: float = 0):
        self.dir = Path(domain_dir)
        self.timeout_s = timeout_s
        self.lock_path: Path | None = None

    def __enter__(self) -> Path:
        self.lock_path = acquire(self.dir, self.timeout_s)
        return self.lock_path

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.lock_path:
            release(self.lock_path)
        return False
