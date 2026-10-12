"""Receive POSIX cancellation through the owned process and child file barriers.

The child process API and procfs need not expose the same PID namespace. These
tests therefore observe behavior without looking up or signalling recorded PIDs.
Adapted from the independent receiver by the 7cb7e049e2c0 delivery_context worker.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import pytest

import testpilot.sandbox as sandbox


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cancellation")

WORKER = r'''
import json, os, pathlib, stat, subprocess, sys, time
role, mode, folder, token = sys.argv[1:]
root = pathlib.Path(folder)
expires = time.monotonic() + 10

def publish(name, payload):
    path = root / name
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(json.dumps(payload))
    pending.replace(path)

info = {"pid": os.getpid(), "pgid": os.getpgrp(), "role": role,
        "token": token, "stdout_is_pipe": stat.S_ISFIFO(os.fstat(1).st_mode)}
publish(role + ".json", info)
if role == "leader":
    subprocess.Popen([sys.executable, __file__, "child", mode, folder, token],
                     start_new_session=mode.startswith("escape"))
    while not (root / "child.before.ack").exists() and time.monotonic() < expires:
        time.sleep(.005)
    if mode.endswith("exit"):
        (root / "leader.exiting").write_text(token)
        raise SystemExit(0)
else:
    # Drain enough actual output to exercise collection before cancellation.
    block = b"interrupt-receiving\n" * 2048
    for _ in range(16):
        view = memoryview(block)
        while view:
            sent = os.write(1, view)
            view = view[sent:]
seen = set()
while time.monotonic() < expires:
    if (root / "stop").exists():
        (root / (role + ".stopped")).write_text(token)
        break
    for stage in ("before", "after"):
        gate = root / (stage + ".gate")
        if stage not in seen and gate.exists() and gate.read_text() == token:
            publish(role + "." + stage + ".ack",
                    {**info, "stage": stage, "at_monotonic": time.monotonic()})
            seen.add(stage)
    time.sleep(.005)
else:
    (root / (role + ".expired")).write_text(token)
'''

RUNNER = r'''
import json, os, pathlib, subprocess, sys, time
from testpilot.sandbox import _run, clean_env
root = pathlib.Path(sys.argv[1])
cmd = [sys.executable, str(root / "worker.py"), "leader",
       sys.argv[2], str(root), sys.argv[3]]
try:
    if sys.argv[4] == "no-cleanup-control":
        # An intentionally deficient receiver control, independent of _run:
        # propagate an interrupt without stopping or reaping its owned child.
        child = subprocess.Popen(cmd, cwd=root, env=clean_env(root),
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        child.communicate(timeout=12)
        result = None
    else:
        result = _run(cmd, root, clean_env(root), 12)
except KeyboardInterrupt:
    leader = json.loads((root / "leader.json").read_text())
    try:
        waited = os.waitpid(leader["pid"], os.WNOHANG)
    except ChildProcessError:
        waited, reaped = None, True
    else:
        reaped = False
    receipt = {"kind": "KeyboardInterrupt", "leader_reaped_before_return": reaped,
               "waitpid_probe": waited, "returned_at_monotonic": time.monotonic()}
else:
    receipt = {"kind": "returned_result", "result": result}
pending = root / "interrupt.json.tmp"
pending.write_text(json.dumps(receipt))
pending.replace(root / "interrupt.json")
'''


def wait_for(path: Path, timeout: float, runner=None):
    deadline = time.monotonic() + timeout
    while not path.exists():
        if runner is not None and runner.poll() is not None:
            raise AssertionError(f"runner exited before {path.name}: {runner.returncode}")
        if time.monotonic() >= deadline:
            raise AssertionError(f"no {path.name} within {timeout}s")
        time.sleep(.005)


def interrupt_run(root, mode, *, cleanup=True):
    token = uuid.uuid4().hex
    (root / "worker.py").write_text(WORKER)
    (root / "runner.py").write_text(RUNNER)
    (root / "before.gate").write_text(token)
    env = {**os.environ, "PYTHONPATH": str(Path(sandbox.__file__).resolve().parent.parent),
           "PYTHONDONTWRITEBYTECODE": "1"}
    accepted = False
    with (root / "runner.stdout").open("wb") as stdout, (root / "runner.stderr").open("wb") as stderr:
        runner = subprocess.Popen(
            [sys.executable, str(root / "runner.py"), str(root), mode, token,
             "normal" if cleanup else "no-cleanup-control"],
            cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=stdout,
            stderr=stderr, start_new_session=True,
        )
        try:
            wait_for(root / "child.before.ack", 4, runner)
            wait_for(root / ("leader.exiting" if mode.endswith("exit") else "leader.before.ack"),
                     2, runner)
            child = json.loads((root / "child.before.ack").read_text())
            leader = json.loads((root / "leader.json").read_text())
            assert child["token"] == token and child["stdout_is_pipe"]
            assert leader["pgid"] == leader["pid"] and leader["pid"] != runner.pid
            assert child["pgid"] == (child["pid"] if mode.startswith("escape") else leader["pgid"])
            started = time.monotonic()
            runner.send_signal(signal.SIGINT)  # This Popen-owned caller only.
            assert runner.wait(timeout=3) == 0, (root / "runner.stderr").read_text()
            elapsed = time.monotonic() - started
            receipt = json.loads((root / "interrupt.json").read_text())
            assert receipt["kind"] == "KeyboardInterrupt", receipt
            assert receipt["leader_reaped_before_return"], "direct child was not reaped before return"
            assert elapsed < 2.5, elapsed
            barrier_at = time.monotonic()
            (root / "after.gate").write_text(token)
            if mode.startswith("escape"):
                wait_for(root / "child.after.ack", .75)
                after = json.loads((root / "child.after.ack").read_text())
                assert after["token"] == token and after["at_monotonic"] >= barrier_at
            else:
                # This child already answered the same challenge before SIGINT.
                deadline = time.monotonic() + .75
                while time.monotonic() < deadline:
                    assert not (root / "child.after.ack").exists(), "same-group child continued after return"
                    time.sleep(.01)
                after = None
            assert not (root / "leader.after.ack").exists(), "leader continued after return"
            observed = {"receipt": receipt, "elapsed_s": elapsed, "mode": mode,
                        "leader": leader, "child_before": child, "child_after": after,
                        "same_group_observation_s": .75 if after is None else None}
            (root / "observed.json").write_text(json.dumps(observed, indent=2) + "\n")
            accepted = True
            return observed
        finally:
            (root / "stop").write_text(token)
            if runner.poll() is None:
                runner.kill()  # Never a PID loaded from a receipt or procfs.
                runner.wait(timeout=2)
            if (mode.startswith("escape") or not cleanup) and (root / "child.before.ack").exists():
                # A surviving fixture exits through its own control file.
                # On an existing failure, retain that failure as the diagnosis.
                try:
                    wait_for(root / "child.stopped", 1)
                except AssertionError:
                    if accepted:
                        raise


@pytest.mark.parametrize("mode", ["group-wait", "group-exit"])
def test_interrupt_stops_same_group_descendant_and_reaps_leader(tmp_path, mode):
    observed = interrupt_run(tmp_path, mode)
    assert observed["child_after"] is None
    assert observed["same_group_observation_s"] == .75


@pytest.mark.parametrize("mode", ["escape-wait", "escape-exit"])
def test_interrupt_does_not_drain_a_detached_helpers_pipe(tmp_path, mode):
    observed = interrupt_run(tmp_path, mode)
    assert observed["child_after"]["stage"] == "after"


def test_receiver_rejects_an_interrupted_caller_that_leaves_its_child_running(tmp_path):
    with pytest.raises(AssertionError, match="direct child was not reaped before return"):
        interrupt_run(tmp_path, "group-wait", cleanup=False)
