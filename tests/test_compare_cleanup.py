"""Publication outcomes survive filesystem errors cleaning a private stage."""
from __future__ import annotations

import errno
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from testpilot import compare
from testpilot.compare_html import render_comparison


@pytest.fixture
def saved_pair(tmp_path):
    document = {
        "status": "no_changes", "changed_functions": [], "test_files": {},
        "tests_written": 0, "repair_rounds_used": 0, "max_repair_rounds": 1,
        "final": None, "coverage": None, "rounds": [], "plan": "", "patch": "",
        "message": "before", "ledger": {
            "total_tokens": 0, "total_cost_usd": 0, "cost_is_complete": False,
            "tokens_estimated": False, "by_model": {}, "entries": []},
    }
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_text(json.dumps(document), encoding="utf-8")
    document["message"] = "after"
    after.write_text(json.dumps(document), encoding="utf-8")

    def inputs():
        return [(p.read_bytes(), p.stat().st_ino, p.stat().st_mode,
                 p.stat().st_mtime_ns) for p in (before, after)]

    original_inputs = inputs()
    expected = render_comparison(compare.read_report(before),
                                 compare.read_report(after)).encode("utf-8")
    yield SimpleNamespace(before=before, after=after, directory=tmp_path,
                          output=tmp_path / "comparison.html", expected=expected)
    assert inputs() == original_inputs


@contextmanager
def cleanup_fault(directory, error):
    """Affect only this call's private stage, leaving test teardown unpatched."""
    real_unlink = Path.unlink
    attempted = []

    def unlink(path, *args, **kwargs):
        if path.parent == directory and path.name.startswith(".testpilot-compare-"):
            attempted.append(path)
            raise error
        return real_unlink(path, *args, **kwargs)

    with patch.object(Path, "unlink", unlink):
        yield attempted


def publish(pair):
    return compare.write_comparison(pair.before, pair.after, pair.output)


@pytest.mark.parametrize("error", [
    PermissionError(errno.EACCES, "private stage is not removable"),
    OSError(errno.EIO, "private stage cleanup I/O failure"),
])
def test_completed_publication_survives_cleanup_oserror(saved_pair, error):
    pair = saved_pair
    with cleanup_fault(pair.directory, error) as attempted:
        result = publish(pair)
    assert result == pair.output
    assert pair.output.read_bytes() == pair.expected
    assert len(attempted) == 1
    stage = attempted[0]
    assert stage.read_bytes() == pair.expected
    assert stage.stat().st_ino == pair.output.stat().st_ino


def test_occupied_output_keeps_real_primary_error_and_existing_bytes(saved_pair):
    pair = saved_pair
    pair.output.write_bytes(b"Existing output sentinel.\n")
    original = pair.output.stat()
    real_link = compare.os.link
    primary = []

    def occupied_link(*args, **kwargs):
        try:
            return real_link(*args, **kwargs)
        except FileExistsError as error:
            primary.append(error)
            raise

    with patch.object(compare.os, "link", occupied_link):
        with cleanup_fault(pair.directory, PermissionError(errno.EACCES, "cleanup")):
            with pytest.raises(FileExistsError) as caught:
                publish(pair)
    assert len(primary) == 1 and caught.value is primary[0]
    assert pair.output.read_bytes() == b"Existing output sentinel.\n"
    assert pair.output.stat().st_ino == original.st_ino
    assert pair.output.stat().st_mtime_ns == original.st_mtime_ns
    assert len(list(pair.directory.glob(".testpilot-compare-*"))) == 1


@pytest.mark.parametrize("boundary", ["fsync", "link"])
def test_primary_io_error_survives_cleanup_denial(saved_pair, boundary):
    pair = saved_pair
    primary = OSError(errno.EIO, "primary " + boundary + " failure")
    with patch.object(compare.os, boundary, side_effect=primary):
        with cleanup_fault(pair.directory, PermissionError(errno.EACCES, "cleanup")):
            with pytest.raises(OSError) as caught:
                publish(pair)
    assert caught.value is primary
    assert not pair.output.exists()
    assert len(list(pair.directory.glob(".testpilot-compare-*"))) == 1


def test_primary_keyboard_interrupt_survives_cleanup_denial(saved_pair):
    pair = saved_pair
    primary = KeyboardInterrupt("publication interrupted")
    with patch.object(compare.os, "link", side_effect=primary):
        with cleanup_fault(pair.directory, PermissionError(errno.EACCES, "cleanup")):
            with pytest.raises(KeyboardInterrupt) as caught:
                publish(pair)
    assert caught.value is primary
    assert not pair.output.exists()


@pytest.mark.parametrize("error", [
    RuntimeError("unexpected cleanup bug"),
    KeyboardInterrupt("cleanup interrupted"),
])
def test_non_oserror_cleanup_exception_remains_visible(saved_pair, error):
    pair = saved_pair
    with cleanup_fault(pair.directory, error):
        with pytest.raises(type(error)) as caught:
            publish(pair)
    assert caught.value is error
    assert pair.output.read_bytes() == pair.expected
    assert len(list(pair.directory.glob(".testpilot-compare-*"))) == 1


def test_ordinary_success_removes_private_stage(saved_pair):
    pair = saved_pair
    assert publish(pair) == pair.output
    assert pair.output.read_bytes() == pair.expected
    assert list(pair.directory.glob(".testpilot-compare-*")) == []


def test_already_removed_stage_does_not_invalidate_published_file(saved_pair):
    pair = saved_pair
    real_link = compare.os.link

    def link_then_remove_stage(source, destination):
        real_link(source, destination)
        Path(source).unlink()

    with patch.object(compare.os, "link", link_then_remove_stage):
        assert publish(pair) == pair.output
    assert pair.output.read_bytes() == pair.expected
    assert list(pair.directory.glob(".testpilot-compare-*")) == []


def test_primary_error_with_successful_cleanup_remains_visible(saved_pair):
    pair = saved_pair
    primary = OSError(errno.EIO, "publication failure")
    with patch.object(compare.os, "link", side_effect=primary):
        with pytest.raises(OSError) as caught:
            publish(pair)
    assert caught.value is primary
    assert not pair.output.exists()
    assert list(pair.directory.glob(".testpilot-compare-*")) == []


def test_cli_reports_completed_publication_after_cleanup_oserror(saved_pair, capsys):
    from testpilot.__main__ import main
    pair = saved_pair
    with cleanup_fault(pair.directory, PermissionError(errno.EACCES, "cleanup")):
        status = main(["compare", "--before", str(pair.before),
                       "--after", str(pair.after), "--out", str(pair.output)])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.err == ""
    assert pair.output.read_bytes() == pair.expected
