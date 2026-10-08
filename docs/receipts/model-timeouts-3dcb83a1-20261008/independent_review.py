"""Independent native receiving for stalled terminal HTTP error bodies.

Replay: python3 independent_review.py SOURCE_DIR RECEIPT_JSON
Only localhost HTTP and authored temporary Git fixtures are used. The unchanged
CLI receives a client with an explicit local endpoint and short read deadline.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE = Path(sys.argv[1]).resolve()
RECEIPT = Path(sys.argv[2]).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE))
from testpilot import __main__ as cli
from testpilot.model import ModelError, OpenAICompatClient

observations = {}


@contextlib.contextmanager
def error_server(statuses):
    """Each (status, stall) sends real headers and a bounded, authored body."""
    release = threading.Event()
    requests = []
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with lock:
                index = len(requests)
                status, stall = statuses[min(index, len(statuses) - 1)]
                requests.append({"path": self.path, "payload": request, "status": status,
                                 "stalled": stall})
            body = b'{"error":"authored terminal diagnostic"}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body[:1] if stall else body)
            self.wfile.flush()
            if stall:
                release.wait(5)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", requests
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError("authored HTTP fixture failed to stop")


def client(url, delays, retries):
    return OpenAICompatClient(base_url=url, api_key="offline-authored-fixture",
                              timeout=0.2, retries=retries, sleep=delays.append)


def exception_record(exc):
    return {"type": type(exc).__name__, "message": str(exc),
            "cause_type": type(exc.__cause__).__name__ if exc.__cause__ else None,
            "context_type": type(exc.__context__).__name__ if exc.__context__ else None}


def run_chat(statuses, retries):
    delays = []
    with error_server(statuses) as (url, requests):
        caught = None
        try:
            client(url, delays, retries).chat(
                "authored-model", [{"role": "user", "content": "local receiving fixture"}],
                max_tokens=13)
        except Exception as exc:
            caught = exc
        observation = {"exception": exception_record(caught) if caught else None,
                       "requests": list(requests), "delays": delays}
    return caught, observation


class TerminalBodyReceiving(unittest.TestCase):
    def check_http_boundary(self, name, statuses, retries, expected_status, expected_requests,
                            expected_delays):
        caught, observation = run_chat(statuses, retries)
        observations[name] = observation
        self.assertEqual(len(observation["requests"]), expected_requests)
        self.assertEqual(observation["delays"], expected_delays)
        self.assertIsInstance(caught, ModelError, observation)
        self.assertIn(f"HTTP {expected_status}", str(caught))
        self.assertIsInstance(caught.__cause__, urllib.error.HTTPError)
        if len(observation["requests"]) > 1:
            self.assertEqual(observation["requests"][0]["payload"],
                             observation["requests"][1]["payload"])

    def test_complete_terminal_400_remains_model_error_without_retry(self):
        self.check_http_boundary("complete_400", [(400, False)], 2, 400, 1, [])

    def test_stalled_terminal_400_remains_model_error_without_retry(self):
        self.check_http_boundary("stalled_400", [(400, True)], 2, 400, 1, [])

    def test_stalled_final_503_respects_exhausted_retry_budget(self):
        self.check_http_boundary("stalled_final_503", [(503, False), (503, True)],
                                 1, 503, 2, [2])

    def test_current_cli_writes_report_for_stalled_http_400(self):
        with tempfile.TemporaryDirectory(prefix="testpilot-terminal-review-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            source = repo / "sample.py"
            source.write_text("def double(value):\n    return value\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "sample.py"], cwd=repo, check=True, capture_output=True)
            source.write_text("def double(value):\n    return value * 2\n", encoding="utf-8")
            original = source.read_bytes()
            diff = subprocess.run(["git", "diff", "--", "sample.py"], cwd=repo,
                                  check=True, capture_output=True, text=True).stdout
            self.assertIn("return value * 2", diff)
            diff_path = root / "change.diff"
            diff_path.write_text(diff, encoding="utf-8")
            output = root / "out"
            delays = []
            stdout, stderr = io.StringIO(), io.StringIO()
            prior_factory = cli.make_client
            env = {"TESTPILOT_PLANNER_MODEL": "authored-plan",
                   "TESTPILOT_EDITOR_MODEL": "authored-edit", "TESTPILOT_PRICES": "{}"}
            prior_env = {name: os.environ.get(name) for name in env}
            caught = None
            exit_code = None
            with error_server([(400, True)]) as (url, requests):
                cli.make_client = lambda *args, **kwargs: client(url, delays, 2)
                os.environ.update(env)
                try:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        exit_code = cli.main([
                            "run", "--repo", str(repo), "--diff", str(diff_path),
                            "--backend", "openai", "--python", sys.executable,
                            "--rounds", "0", "--out", str(output)])
                except Exception as exc:
                    caught = exc
                finally:
                    cli.make_client = prior_factory
                    for name, previous in prior_env.items():
                        if previous is None:
                            os.environ.pop(name, None)
                        else:
                            os.environ[name] = previous
                report_path = output / "report.json"
                report = json.loads(report_path.read_text()) if report_path.exists() else None
                unchanged = source.read_bytes() == original
                output_names = sorted(p.name for p in output.iterdir()) if output.exists() else []
                observations["current_cli"] = {
                    "exception": exception_record(caught) if caught else None,
                    "exit_code": exit_code, "report": report,
                    "requests": list(requests), "delays": delays,
                    "source_unchanged": unchanged, "output_names": output_names,
                    "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
                    "python_argument": sys.executable}
            self.assertTrue(unchanged)
            self.assertEqual(len(observations["current_cli"]["requests"]), 1)
            self.assertEqual(delays, [])
            self.assertIsNone(caught, observations["current_cli"])
            self.assertEqual(exit_code, 1)
            self.assertIsNotNone(report)
            self.assertEqual(report["status"], "model_error")
            self.assertIn("HTTP 400", report["message"])
            self.assertEqual(report["tests_written"], 0)
            self.assertEqual(output_names, ["report.json", "report.md", "testpilot.patch"])
            self.assertEqual((output / "testpilot.patch").read_text(), "")


def pin(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
            "bytes": len(data)}


suite = unittest.defaultTestLoader.loadTestsFromTestCase(TerminalBodyReceiving)
result = unittest.TextTestRunner(verbosity=2).run(suite)
receipt = {
    "source": str(SOURCE), "python": sys.version,
    "harness": pin(Path(__file__)),
    "package": {str(path.relative_to(SOURCE)): pin(path)
                for path in sorted((SOURCE / "testpilot").glob("*.py"))},
    "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
    "skips": len(result.skipped), "successful": result.wasSuccessful(),
    "observations": observations,
}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(RECEIPT), "tests_run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors),
                  "successful": result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() else 1)
