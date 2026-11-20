import os
import shutil
import socket

import pytest

from course_testing import load

m = load("08-tool-use-security", "secure_tools.py")


def fake_resolver(mapping):
    def resolve(host, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in mapping[host]]

    return resolve


@pytest.fixture
def box(tmp_path):
    return m.SandboxedFiles(tmp_path / "sandbox", max_bytes=100)


def test_files_inside_sandbox_work(box):
    box.write("a/b.txt", "hello")
    assert box.read("a/b.txt") == "hello"


@pytest.mark.parametrize("bad", ["../secret.txt", "/etc/passwd", "a/../../x", "", "a\x00b"])
def test_traversal_is_refused(box, bad):
    with pytest.raises(m.ToolSecurityError):
        box.read(bad)


def test_symlink_escape_is_refused(box, tmp_path):
    (tmp_path / "outside.txt").write_text("secret")
    os.symlink(tmp_path / "outside.txt", box.root / "link.txt")
    with pytest.raises(m.ToolSecurityError):
        box.read("link.txt")


def test_size_limit(box):
    with pytest.raises(m.ToolSecurityError):
        box.write("big.txt", "x" * 1000)


@pytest.mark.skipif(not shutil.which("echo") or os.name == "nt", reason="needs a POSIX echo")
def test_commands_have_no_shell(tmp_path):
    out = m.run_allowed_command("echo hello; rm -rf /", {"echo"}, tmp_path)
    assert out.strip() == "hello; rm -rf /"  # printed as text, never run


def test_command_allowlist(tmp_path):
    for bad in ["rm -rf /", "/bin/echo hi", "", "../echo hi"]:
        with pytest.raises(m.ToolSecurityError):
            m.run_allowed_command(bad, {"echo"}, tmp_path)


@pytest.mark.skipif(not shutil.which("printenv") or os.name == "nt", reason="needs printenv")
def test_child_process_cannot_see_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "super-secret-value")
    assert "super-secret-value" not in m.run_allowed_command(["printenv"], {"printenv"}, tmp_path)


def test_url_checks():
    hosts = {"docs.example.org", "rebind.example.org"}
    resolver = fake_resolver({"docs.example.org": ["93.184.215.14"], "rebind.example.org": ["127.0.0.1"]})
    assert m.check_url("https://docs.example.org/page", hosts, resolver) == (True, "ok")
    assert not m.check_url("http://docs.example.org/", hosts, resolver)[0]
    assert not m.check_url("https://169.254.169.254/latest/meta-data/", hosts, resolver)[0]
    assert "non-public" in m.check_url("https://rebind.example.org/", hosts, resolver)[1]
    assert "allowlist" in m.check_url("https://evil.example/", hosts, resolver)[1]


def test_audit_log_redacts_and_records(tmp_path, box):
    audit = m.AuditLog(tmp_path / "audit.jsonl")
    m.guarded_call(audit, "write", box.write, rel_path="ok.txt", text="token sk-" + "abcdefghijklmnop")
    assert m.guarded_call(audit, "read", box.read, rel_path="../x").startswith("error: blocked")
    entries = audit.entries()
    assert [e["decision"] for e in entries] == ["allowed", "blocked"]
    assert "abcdefghijklmnop" not in entries[0]["args"]
