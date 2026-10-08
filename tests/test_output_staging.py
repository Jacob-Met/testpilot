# SPDX-License-Identifier: Apache-2.0
"""Preserve a saved review when new output cannot be prepared or staged."""
from __future__ import annotations

import copy
import errno
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from testpilot import loop
from testpilot.loop import Ledger, LoopResult, render_report, write_outputs
from testpilot.html_report import render_html_report
from testpilot.model import RoutingConfig


NAMES = {
    "patch": "testpilot.patch", "json": "report.json",
    "md": "report.md", "html": "report.html",
}


def result(patch="NEW review\n", *, status="no_tests"):
    return LoopResult(
        status=status, changed_functions=[], repair_rounds_used=0, max_repair_rounds=0,
        test_files={}, tests_written=0, final=None, patch=patch, coverage=None,
        ledger=Ledger(RoutingConfig()).to_dict(), rounds=[],
        plan="Authored output fixture; no model call or test-execution claim.",
        message="Literal café / 雪 / e\u0301 / <report> & review.",
    )


def snapshot(folder):
    return {name: (folder / name).read_bytes() for name in NAMES.values()}


def saved(folder):
    write_outputs(result("OLD saved review\n"), folder)
    (folder / "keep.txt").write_bytes(b"unrelated file")
    return snapshot(folder)


def assert_preserved(folder, before):
    assert snapshot(folder) == before
    assert (folder / "keep.txt").read_bytes() == b"unrelated file"
    assert set(p.name for p in folder.iterdir()) == {*NAMES.values(), "keep.txt"}


def legacy_outputs(res, folder):
    """Independent compatibility reference: the pre-staging writer's file operations."""
    folder.mkdir(parents=True)
    paths = {key: folder / name for key, name in NAMES.items()}
    paths["patch"].write_text(res.patch, encoding="utf-8")
    paths["json"].write_text(json.dumps(res.to_dict(), indent=2), encoding="utf-8")
    paths["md"].write_text(render_report(res), encoding="utf-8")
    paths["html"].write_text(
        render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()),
        encoding="utf-8",
    )
    return snapshot(folder)


@pytest.mark.parametrize("patch", [
    "", "ordinary\nsecond line\n", "mixed\r\nnewlines\rand bare\n",
    "literal café / 雪 / 🦉 / \u2028 / <script> & content\n",
])
@pytest.mark.parametrize("status", ["no_tests", "failed"])
def test_replacement_preserves_successful_bytes_and_return_mapping(tmp_path, patch, status):
    out = tmp_path / "saved"
    before = saved(out)
    res = result(patch, status=status)
    unchanged_result = copy.deepcopy(res.to_dict())
    expected = legacy_outputs(res, tmp_path / "reference")
    returned = write_outputs(res, out)
    assert returned == {key: out / name for key, name in NAMES.items()}
    assert list(returned) == list(NAMES)
    assert snapshot(out) == expected
    assert snapshot(out) != before
    assert res.to_dict() == unchanged_result
    assert (out / "keep.txt").read_bytes() == b"unrelated file"
    assert set(p.name for p in out.iterdir()) == {*NAMES.values(), "keep.txt"}


def test_new_nested_output_directory_has_the_same_artifact_bytes(tmp_path):
    res = result()
    out = tmp_path / "nested" / "new-review"
    expected = legacy_outputs(res, tmp_path / "reference")
    paths = write_outputs(res, str(out))
    assert paths == {key: out / name for key, name in NAMES.items()}
    assert snapshot(out) == expected
    assert set(p.name for p in out.iterdir()) == set(NAMES.values())


def test_unencodable_patch_does_not_truncate_a_previous_review(tmp_path):
    out = tmp_path / "saved"
    before = saved(out)
    with pytest.raises(UnicodeEncodeError):
        write_outputs(result("unencodable \ud800 patch"), out)
    assert_preserved(out, before)


def test_markdown_preparation_failure_keeps_all_previous_outputs(tmp_path):
    out = tmp_path / "saved"
    before = saved(out)
    res = result()
    res.coverage = {"total_before": 0.0}
    with pytest.raises(KeyError, match="total_after"):
        write_outputs(res, out)
    assert_preserved(out, before)


def test_html_preparation_failure_keeps_all_previous_outputs(tmp_path, monkeypatch):
    out = tmp_path / "saved"
    before = saved(out)

    def unavailable_renderer(*_args):
        raise ValueError("authored renderer failure")

    monkeypatch.setattr(loop, "render_html_report", unavailable_renderer)
    with pytest.raises(ValueError, match="authored renderer failure"):
        write_outputs(result(), out)
    assert_preserved(out, before)


@pytest.mark.parametrize("name", NAMES.values())
def test_directory_final_is_admitted_before_any_output_changes(tmp_path, name):
    out = tmp_path / "saved"
    saved(out)
    target = out / name
    target.unlink()
    target.mkdir()
    (target / "keep").write_bytes(b"directory contents")
    regular = {n: (out / n).read_bytes() for n in NAMES.values() if n != name}
    with pytest.raises(OSError) as error:
        write_outputs(result(), out)
    assert error.value.errno == errno.EINVAL
    assert error.value.filename == str(target)
    assert target.is_dir()
    assert (target / "keep").read_bytes() == b"directory contents"
    assert {n: (out / n).read_bytes() for n in regular} == regular
    assert set(p.name for p in out.iterdir()) == {*NAMES.values(), "keep.txt"}


@pytest.mark.skipif(os.name != "posix", reason="native POSIX symlink control")
@pytest.mark.parametrize("dangling", [False, True])
def test_late_symlink_final_and_its_target_remain_untouched(tmp_path, dangling):
    out = tmp_path / "saved"
    before = saved(out)
    linked = tmp_path / "linked-report"
    if not dangling:
        linked.write_bytes(b"independent linked file")
    target = out / "report.html"
    target.unlink()
    target.symlink_to(linked)
    with pytest.raises(OSError) as error:
        write_outputs(result(), out)
    assert error.value.errno == errno.EINVAL
    assert target.is_symlink() and target.readlink() == linked
    assert {n: (out / n).read_bytes() for n in NAMES.values() if n != "report.html"} == {
        n: b for n, b in before.items() if n != "report.html"
    }
    if dangling:
        assert not linked.exists()
    else:
        assert linked.read_bytes() == b"independent linked file"
    assert set(p.name for p in out.iterdir()) == {*NAMES.values(), "keep.txt"}


@pytest.mark.skipif(os.name != "posix", reason="native POSIX permission bits")
@pytest.mark.parametrize("mode", [0o600, 0o640])
def test_replacement_keeps_existing_output_permission_bits(tmp_path, mode):
    out = tmp_path / "saved"
    saved(out)
    for name in NAMES.values():
        (out / name).chmod(mode)
    write_outputs(result(), out)
    assert all(stat.S_IMODE((out / name).stat().st_mode) == mode for name in NAMES.values())


_LIMIT_CHILD = r"""
import errno, json, resource, signal, sys
from pathlib import Path
from testpilot.loop import LoopResult, write_outputs
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
data.pop("ok")
res = LoopResult(**data)
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))
try:
    write_outputs(res, sys.argv[2])
except OSError as error:
    print(json.dumps({"errno": error.errno, "type": type(error).__name__}))
    raise SystemExit(72)
raise SystemExit(0)
"""


def child_env():
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(loop.__file__).resolve().parent.parent)}


@pytest.mark.skipif(os.name != "posix", reason="native POSIX file-size limit")
@pytest.mark.parametrize("patch", ["large patch\n" * 1000, "NEW review\n"], ids=["patch", "html"])
def test_real_file_size_error_preserves_the_previous_four_outputs(tmp_path, patch):
    out = tmp_path / "saved"
    before = saved(out)
    request = tmp_path / "request.json"
    request.write_text(json.dumps(result(patch).to_dict()), encoding="utf-8")
    child = subprocess.run(
        [sys.executable, "-B", "-c", _LIMIT_CHILD, str(request), str(out)],
        text=True, capture_output=True, timeout=10, env=child_env(),
    )
    assert child.returncode == 72, (child.stdout, child.stderr)
    assert json.loads(child.stdout)["errno"] == errno.EFBIG
    assert_preserved(out, before)


@pytest.mark.skipif(os.name != "posix", reason="native POSIX FIFO control")
def test_fifo_final_is_rejected_without_opening_it(tmp_path):
    out = tmp_path / "saved"
    before = saved(out)
    fifo = out / "report.html"
    fifo.unlink()
    os.mkfifo(fifo)
    code = r"""
import errno, json, sys
from pathlib import Path
from testpilot.loop import LoopResult, write_outputs
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
data.pop("ok")
try:
    write_outputs(LoopResult(**data), sys.argv[2])
except OSError as error:
    print(error.errno)
    raise SystemExit(73)
"""
    request = tmp_path / "request.json"
    request.write_text(json.dumps(result().to_dict()), encoding="utf-8")
    child = subprocess.run(
        [sys.executable, "-B", "-c", code, str(request), str(out)],
        text=True, capture_output=True, timeout=5, env=child_env(),
    )
    assert child.returncode == 73, (child.stdout, child.stderr)
    assert child.stdout.strip() == str(errno.EINVAL)
    assert stat.S_ISFIFO(fifo.lstat().st_mode)
    assert {n: (out / n).read_bytes() for n in NAMES.values() if n != "report.html"} == {
        n: b for n, b in before.items() if n != "report.html"
    }


def test_later_replacement_error_propagates_without_a_whole_set_rollback(tmp_path, monkeypatch):
    out = tmp_path / "saved"
    before = saved(out)
    res = result()
    expected = legacy_outputs(res, tmp_path / "reference")
    replace = Path.replace

    def deny_markdown(source, target):
        if target == out / "report.md":
            raise OSError(errno.EACCES, "authored late replacement refusal", str(target))
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", deny_markdown)
    with pytest.raises(OSError) as error:
        write_outputs(res, out)
    assert error.value.errno == errno.EACCES
    after = snapshot(out)
    assert after["testpilot.patch"] == expected["testpilot.patch"]
    assert after["report.json"] == expected["report.json"]
    assert after["report.md"] == before["report.md"]
    assert after["report.html"] == before["report.html"]
    assert set(p.name for p in out.iterdir()) == {*NAMES.values(), "keep.txt"}
