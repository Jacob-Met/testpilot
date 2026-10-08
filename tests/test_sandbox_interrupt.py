"""Real POSIX interrupt cleanup, including descendants and retained output pipes."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

import testpilot.sandbox as sandbox


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cancellation")

WORKER = """\
import json, os, pathlib, subprocess, sys, time
role, mode, folder = sys.argv[1:]
root = pathlib.Path(folder)
deadline = time.monotonic() + 8
info = {"pid": os.getpid(), "pgid": os.getpgrp(), "role": role}
(root / (role + ".json")).write_text(json.dumps(info))
if role == "leader":
    child = subprocess.Popen(
        [sys.executable, __file__, "child", mode, folder],
        start_new_session=mode.startswith("escape"),
    )
    while not (root / "child.json").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    (root / "ready").write_text("Both fixture processes have started")
    print("leader-ready", flush=True)
    if mode.endswith("exit"):
        raise SystemExit(0)
while time.monotonic() < deadline:
    time.sleep(0.01)
"""

RUNNER = """\
import json, os, pathlib, sys
from testpilot.sandbox import _run, clean_env
root = pathlib.Path(sys.argv[1])
try:
    result = _run([sys.executable, str(root / "worker.py"), "leader",
                   sys.argv[2], str(root)], root, clean_env(root), 12)
except KeyboardInterrupt:
    info = json.loads((root / "leader.json").read_text())
    try:
        waited = os.waitpid(info["pid"], os.WNOHANG)
        # A live child returns (0, 0); a zombie reaped here was not reaped by _run.
        reaped = False
    except ChildProcessError:
        waited, reaped = None, True
    receipt = {"kind": "KeyboardInterrupt", "leader_reaped_before_return": reaped,
               "waitpid_probe": waited}
else:
    receipt = {"kind": "returned_result", "result": result}
(root / "interrupt.json").write_text(json.dumps(receipt))
"""


def command_if_running(pid):
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat=", "-o", "command="],
        capture_output=True, text=True, timeout=1,
    )
    fields = result.stdout.strip().split(None, 1)
    if result.returncode or not fields or fields[0].startswith("Z"):
        return None
    return fields[1] if len(fields) == 2 else ""


def fixture_processes(root):
    result = []
    for role in ("leader", "child"):
        path = root / (role + ".json")
        try:
            result.append(json.loads(path.read_text()))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return result


def is_owned_running(info, root):
    command = command_if_running(info["pid"])
    return command is not None and str(root / "worker.py") in command


def finish_fixture(root, runner):
    # Never signal a reused PID or anything outside this unique fixture. A
    # startup failure gets a ten-second cleanup deadline: workers self-exit at
    # eight seconds even if they never reach the complete readiness record.
    if runner.poll() is None:
        os.killpg(runner.pid, signal.SIGKILL)
        runner.wait(timeout=2)
    deadline = time.monotonic() + 10
    infos = fixture_processes(root)
    while True:
        infos = fixture_processes(root)
        for info in infos:
            if is_owned_running(info, root):
                try:
                    assert os.getpgid(info["pid"]) == info["pgid"]
                    assert info["pgid"] not in (os.getpgrp(), runner.pid)
                    os.killpg(info["pgid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if len(infos) == 2 and all(not is_owned_running(i, root) for i in infos):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.02)
    assert all(not is_owned_running(i, root) for i in infos), "owned fixture process survived cleanup"


def interrupt_run(tmp_path, mode):
    (tmp_path / "worker.py").write_text(WORKER)
    (tmp_path / "runner.py").write_text(RUNNER)
    env = {**os.environ, "PYTHONPATH": str(Path(sandbox.__file__).resolve().parent.parent),
           "PYTHONDONTWRITEBYTECODE": "1"}
    with (tmp_path / "runner.stdout").open("wb") as stdout, (tmp_path / "runner.stderr").open("wb") as stderr:
        runner = subprocess.Popen(
            [sys.executable, str(tmp_path / "runner.py"), str(tmp_path), mode],
            cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, stdout=stdout,
            stderr=stderr, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not (tmp_path / "ready").exists():
                assert runner.poll() is None, (tmp_path / "runner.stderr").read_text()
                assert time.monotonic() < deadline, "native fixture never became ready"
                time.sleep(0.01)
            infos = fixture_processes(tmp_path)
            assert len(infos) == 2
            leader, child = infos
            assert leader["pgid"] == leader["pid"] and leader["pid"] != runner.pid
            assert child["pgid"] == (child["pid"] if mode.startswith("escape") else leader["pid"])
            started = time.monotonic()
            runner.send_signal(signal.SIGINT)  # Only this test's own _run caller.
            assert runner.wait(timeout=4) == 0, (tmp_path / "runner.stderr").read_text()
            elapsed = time.monotonic() - started
            receipt = json.loads((tmp_path / "interrupt.json").read_text())
            observed = {"receipt": receipt, "elapsed_s": elapsed,
                        "leader_running": is_owned_running(leader, tmp_path),
                        "child_running": is_owned_running(child, tmp_path),
                        "mode": mode, "processes": infos}
            (tmp_path / "observed.json").write_text(json.dumps(observed, indent=2) + "\n")
            return observed
        finally:
            finish_fixture(tmp_path, runner)


@pytest.mark.parametrize("mode", ["group-wait", "group-exit"])
def test_interrupt_stops_same_group_descendant_and_reaps_leader(tmp_path, mode):
    observed = interrupt_run(tmp_path, mode)
    assert observed["receipt"]["kind"] == "KeyboardInterrupt"
    assert observed["receipt"]["leader_reaped_before_return"], observed
    assert not observed["leader_running"], observed
    assert not observed["child_running"], observed
    assert observed["elapsed_s"] < 2.5, observed


@pytest.mark.parametrize("mode", ["escape-wait", "escape-exit"])
def test_interrupt_does_not_drain_a_detached_helpers_pipe(tmp_path, mode):
    observed = interrupt_run(tmp_path, mode)
    assert observed["receipt"]["kind"] == "KeyboardInterrupt"
    assert observed["receipt"]["leader_reaped_before_return"], observed
    assert not observed["leader_running"], observed
    assert observed["child_running"], "escaped-session containment is outside this contract"
    assert observed["elapsed_s"] < 2.5, observed
