"""Review-directory exports preserve recorded bytes and never execute tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot import export_tests as export

ROOT = Path(__file__).resolve().parents[1]


def report(path, tests=None, **metadata):
    value = {"test_files": tests if tests is not None else {
        "tests/test_bytes.py": "# café\r\nvalue = 'λ'\r# last line"
    }, **metadata}
    path.write_bytes((json.dumps(value, indent=3, ensure_ascii=False) + "\r\n").encode("utf-8"))
    return path


def stage_names(parent):
    return sorted(p.name for p in parent.glob(".testpilot-export-*"))


def invoke(source, out):
    return subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", "export-tests",
         "--report", str(source), "--out", str(out)],
        cwd=ROOT, capture_output=True, timeout=10,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                 TESTPILOT_BACKEND="export-must-not-call-model"),
    )


def test_final_bytes_and_historical_provenance_without_execution(tmp_path):
    canary = tmp_path / "must-not-exist"
    payload = {
        "tests/test_z.py": f"open({str(canary)!r}, 'w').write('executed')\r\n",
        "tests/group/test_a.py": "# λ\r\n# bare\r# LF\n# no final newline",
        "tests/test_empty.py": "",
    }
    source = report(tmp_path / "source.json", payload, status="suspected_code_bug",
                    rounds=[{"test_files": {"tests/test_old.py": "raise RuntimeError()"}}],
                    rejected={"note": "retained only as metadata"})
    raw = source.read_bytes()
    out = tmp_path / "review"
    result = invoke(source, out)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    summary = json.loads(result.stdout)
    manifest = json.loads((out / "export-manifest.json").read_bytes())
    assert summary["files"] == 3
    assert manifest["source_report"] == {
        "path": str(source), "sha256": hashlib.sha256(raw).hexdigest(),
        "recorded_status": "suspected_code_bug", "copy": "source-report.json"}
    assert manifest["test_runs"] == manifest["model_calls"] == 0
    assert manifest["status"] == "exported_for_review"
    assert (out / "source-report.json").read_bytes() == source.read_bytes() == raw
    assert [row["path"] for row in manifest["test_files"]] == sorted(payload)
    for row in manifest["test_files"]:
        data = payload[row["path"]].encode("utf-8")
        assert (out / row["path"]).read_bytes() == data
        assert row == {"path": row["path"], "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()}
    assert not (out / "tests/test_old.py").exists()
    assert not canary.exists()
    assert stage_names(tmp_path) == []


@pytest.mark.parametrize("kind", ["directory", "file", "broken_symlink", "parent_symlink", "traversal"])
def test_conflicting_destinations_are_untouched(tmp_path, kind):
    source = report(tmp_path / "source.json")
    out = tmp_path / "review"
    if kind == "directory":
        out.mkdir()
        (out / "sentinel").write_bytes(b"old")
    elif kind == "file":
        out.write_bytes(b"old")
    elif kind == "broken_symlink":
        out.symlink_to(tmp_path / "missing")
    elif kind == "parent_symlink":
        (tmp_path / "real").mkdir()
        (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
        out = tmp_path / "link" / "review"
    else:
        (tmp_path / "child").mkdir()
        out = tmp_path / "child" / ".." / "review"
    raw = source.read_bytes()
    result = invoke(source, out)
    assert result.returncode == 2 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert source.read_bytes() == raw
    if kind == "directory":
        assert (out / "sentinel").read_bytes() == b"old"
    elif kind == "file":
        assert out.read_bytes() == b"old"
    elif kind == "broken_symlink":
        assert out.is_symlink() and os.readlink(out) == str(tmp_path / "missing")
    else:
        assert not out.exists()
    assert stage_names(tmp_path) == []


@pytest.mark.parametrize("raw", [
    b'{"test_files":{"tests/test_a.py":"one","tests/test_a.py":"two"}}',
    b'{"test_files":{"../escape.py":"bad"}}',
    b'{"test_files":{"tests/test_A.py":"one","tests/test_a.py":"two"}}',
    b'{"test_files":{"tests/A/test_a.py":"one","tests/a/test_b.py":"two"}}',
    b'{"test_files":{}}', b'{"test_files":{"tests/test_a.py":23}}',
    b'{"test_files":{"tests/test_a.py":"\xff"}}',
])
def test_admission_refusals_leave_no_directory(tmp_path, raw):
    source = tmp_path / "source.json"
    source.write_bytes(raw)
    out = tmp_path / "review"
    result = invoke(source, out)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["ok"] is False
    assert source.read_bytes() == raw
    assert not out.exists()
    assert stage_names(tmp_path) == []


def test_interrupted_write_cleans_private_stage(tmp_path, monkeypatch):
    source = report(tmp_path / "source.json")
    out = tmp_path / "review"
    real_write = export._write_bytes

    def fail_after_test(path, data):
        if path.name == "source-report.json":
            raise OSError("simulated full device")
        return real_write(path, data)

    monkeypatch.setattr(export, "_write_bytes", fail_after_test)
    with pytest.raises(export.ExportTestsError, match="simulated full device"):
        export.export_saved_tests(source, out)
    assert not out.exists()
    assert stage_names(tmp_path) == []


def test_changed_source_before_publication_refuses(tmp_path, monkeypatch):
    source = report(tmp_path / "source.json")
    out = tmp_path / "review"
    real_write = export._write_bytes

    def replace_source(path, data):
        real_write(path, data)
        if path.name == "export-manifest.json":
            source.write_bytes(b'{"changed":true}')

    monkeypatch.setattr(export, "_write_bytes", replace_source)
    with pytest.raises(export.ExportTestsError, match="changed after admission"):
        export.export_saved_tests(source, out)
    assert source.read_bytes() == b'{"changed":true}'
    assert not out.exists() and stage_names(tmp_path) == []


def test_destination_created_after_staging_is_not_replaced(tmp_path, monkeypatch):
    source = report(tmp_path / "source.json")
    out = tmp_path / "review"
    real_write = export._write_bytes

    def introduce_destination(path, data):
        real_write(path, data)
        if path.name == "export-manifest.json":
            out.mkdir()

    monkeypatch.setattr(export, "_write_bytes", introduce_destination)
    with pytest.raises(export.ExportTestsError):
        export.export_saved_tests(source, out)
    assert out.is_dir() and list(out.iterdir()) == []
    assert stage_names(tmp_path) == []


def test_unsupported_platform_refuses_before_read(tmp_path, monkeypatch):
    monkeypatch.setattr(export.sys, "platform", "unsupported-platform")
    with pytest.raises(export.ExportTestsError, match="supported on Linux"):
        export.export_saved_tests(tmp_path / "absent.json", tmp_path / "review")
    assert list(tmp_path.iterdir()) == []


def test_console_failure_does_not_claim_rollback(tmp_path, monkeypatch):
    source = report(tmp_path / "source.json")
    out = tmp_path / "review"
    calls = []

    def broken_console(stream, text):
        calls.append((stream, text))
        return stream is not sys.stdout

    monkeypatch.setattr(export, "_write_console", broken_console)
    from types import SimpleNamespace
    assert export.run_export_tests_command(SimpleNamespace(report=source, out=out)) == 2
    assert (out / "export-manifest.json").is_file()
    assert "export was published" in calls[-1][1]


def test_help_does_not_read_missing_report(tmp_path):
    result = subprocess.run([sys.executable, "-B", "-m", "testpilot", "export-tests",
                             "--report", str(tmp_path / "missing"), "--help"],
                            cwd=ROOT, capture_output=True, timeout=10)
    assert result.returncode == 0 and b"--out" in result.stdout and not result.stderr
    assert list(tmp_path.iterdir()) == []
