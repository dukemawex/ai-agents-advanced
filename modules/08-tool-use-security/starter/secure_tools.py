"""Module 08 starter: tools that stay safe whatever arguments the model sends."""

import ipaddress
import json
import re
import shlex
import shutil
import socket
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse


class ToolSecurityError(Exception):
    pass


# ---------- files ----------


class SandboxedFiles:
    def __init__(self, root: str | Path, max_bytes: int = 100_000):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes

    def _resolve(self, rel_path: str) -> Path:
        """Turn a model-supplied path into a real path inside the sandbox, or refuse."""
        # TODO 1: refuse empty, absolute, or NUL-containing paths with ToolSecurityError.
        # TODO 2: real = (self.root / rel_path).resolve()   # follows '..' and symlinks
        # TODO 3: refuse if not real.is_relative_to(self.root). Otherwise return real.
        raise NotImplementedError

    def read(self, rel_path: str) -> str:
        path = self._resolve(rel_path)
        if path.stat().st_size > self.max_bytes:
            raise ToolSecurityError("file too large")
        return path.read_text(errors="replace")

    def write(self, rel_path: str, text: str) -> str:
        if len(text.encode()) > self.max_bytes:
            raise ToolSecurityError("content too large")
        path = self._resolve(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return f"wrote {len(text)} characters to {path.relative_to(self.root)}"


# ---------- commands ----------

SAFE_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}


def run_allowed_command(
    command: str | list[str], allowlist: set[str], cwd: str | Path, timeout: float = 10, max_output: int = 4000
) -> str:
    """Run a program from the allowlist with no shell, a timeout and a minimal environment."""
    # TODO 1: argv = shlex.split(command) if it is a string, else list(command). Refuse empty.
    # TODO 2: refuse programs containing "/" or "\\", or not in the allowlist.
    # TODO 3: resolve it with shutil.which(program, path=SAFE_ENV["PATH"]).
    # TODO 4: subprocess.run([...], shell=False, cwd=cwd, env=SAFE_ENV, capture_output=True, text=True,
    #         timeout=timeout). A TimeoutExpired becomes ToolSecurityError.
    # TODO 5: return (stdout + stderr) cut to max_output characters.
    raise NotImplementedError


# ---------- network ----------


def check_url(url: str, allowed_hosts: set[str], resolver: Callable = socket.getaddrinfo) -> tuple[bool, str]:
    """Allow only https URLs to approved hosts whose IP addresses are all public."""
    # TODO 1: scheme must be https; hostname (lower-case) must be in allowed_hosts.
    # TODO 2: resolve with resolver(host, port or 443); an OSError means "did not resolve".
    # TODO 3: every resolved address (info[4][0]) must be ipaddress.ip_address(...).is_global.
    # Return (True, "ok") or (False, "<reason>").
    raise NotImplementedError


# ---------- audit ----------

REDACT = [(re.compile(r"(sk-|gsk_|ghp_)[A-Za-z0-9_-]{8,}"), r"\1[REDACTED]")]


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def record(self, tool: str, args: dict, decision: str, detail: str = "") -> None:
        text = json.dumps(args, default=str)
        for pattern, repl in REDACT:
            text = pattern.sub(repl, text)
        entry = {"ts": time.time(), "tool": tool, "args": text, "decision": decision, "detail": detail[:200]}
        with self.path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")

    def entries(self) -> list[dict]:
        return [json.loads(line) for line in self.path.read_text().splitlines()] if self.path.exists() else []


def guarded_call(audit: AuditLog, tool: str, func: Callable, **args) -> str:
    """Run a tool, turning security errors into messages for the model and logging every decision."""
    try:
        result = str(func(**args))
    except ToolSecurityError as exc:
        audit.record(tool, args, "blocked", str(exc))
        return f"error: blocked: {exc}"
    except Exception as exc:
        audit.record(tool, args, "error", type(exc).__name__)
        return f"error: {type(exc).__name__}"
    audit.record(tool, args, "allowed")
    return result


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        box = SandboxedFiles(Path(tmp) / "sandbox")
        audit = AuditLog(Path(tmp) / "audit.jsonl")
        print(guarded_call(audit, "write", box.write, rel_path="notes/todo.txt", text="buy seeds"))
        for attack in ["../../etc/passwd", "/etc/passwd", "notes/../../secret.txt"]:
            print(attack, "->", guarded_call(audit, "read", box.read, rel_path=attack))
        cmd = {"allowlist": {"echo", "ls"}, "cwd": tmp}
        print(guarded_call(audit, "run", run_allowed_command, command="echo hello; rm -rf /", **cmd))
        print(guarded_call(audit, "run", run_allowed_command, command="rm -rf /", **cmd))
        hosts = {"docs.python.org"}
        print(check_url("http://169.254.169.254/latest/meta-data/", hosts))
        print(check_url("https://evil.example/", hosts))
        print("audit entries:", len(audit.entries()))
