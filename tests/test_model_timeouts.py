"""Native response-timeout receiving for the public chat client and CLI.

All HTTP replies and repositories are authored local fixtures. A stalled body
is released by the fixture's finalizer; no provider or external address is used.
"""
import io
import json
import subprocess
import threading
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from testpilot import __main__ as cli
from testpilot.model import ModelError, OpenAICompatClient, Usage

MESSAGES = [{"role": "user", "content": "authored timeout control"}]
FENCE = chr(96) * 3
PLAN = "Pin double(2) == 4 and double(-2) == -4."
GOOD = (FENCE + "python path=tests/test_generated_double.py\n"
        "from sample import double\n\n"
        "def test_positive():\n    assert double(2) == 4\n\n"
        "def test_negative():\n    assert double(-2) == -4\n" + FENCE)
BAD = (FENCE + "python path=tests/test_generated_double.py\n"
       "from sample import double\n\n"
       "def test_positive():\n    assert double(2) == 5\n" + FENCE)


@contextmanager
def local_chat(replies):
    """None sends valid headers and then stalls the body until finalization."""
    release = threading.Event()
    lock = threading.Lock()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with lock:
                index = len(requests)
                requests.append({"path": self.path, "payload": request})
                content = replies[index] if index < len(replies) else None
            body = json.dumps({
                "model": request["model"],
                "choices": [{"message": {"content": content or "stalled fixture"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.flush()
            if content is None:
                release.wait(10)
                return
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.02}, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", requests
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        assert not worker.is_alive()


def local_client(url, delays, retries=1):
    return OpenAICompatClient(base_url=url, api_key="offline-fixture",
                              timeout=0.25, retries=retries, sleep=delays.append)


def test_retries_a_real_response_body_timeout_then_returns_usage():
    delays = []
    with local_chat([None, "recovered response"]) as (url, requests):
        result = local_client(url, delays).chat("fixture-model", MESSAGES, max_tokens=19)
        assert result.content == "recovered response"
        assert result.usage == Usage(7, 3)
        assert delays == [2]
        assert len(requests) == 2
        assert requests[0] == requests[1]
        assert requests[1]["path"] == "/v1/chat/completions"
        assert requests[1]["payload"]["max_tokens"] == 19


@pytest.mark.parametrize("retries", [0, 2])
def test_real_timeout_exhaustion_becomes_model_error_with_bounded_attempts(retries):
    delays = []
    with local_chat([]) as (url, requests):
        with pytest.raises(ModelError, match="timed out") as caught:
            local_client(url, delays, retries).chat("fixture-model", MESSAGES)
        assert isinstance(caught.value.__cause__, TimeoutError)
        assert len(requests) == retries + 1
        assert delays == [2 ** i for i in range(1, retries + 1)]


def test_http_and_direct_timeout_failures_share_the_existing_retry_budget():
    attempts, delays = [], []

    def transport(url, headers, body, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(url, 503, "authored unavailable", {},
                                         io.BytesIO(b"retry fixture"))
        raise TimeoutError("authored timeout")

    client = OpenAICompatClient(api_key="offline-fixture", retries=2,
                               transport=transport, sleep=delays.append)
    with pytest.raises(ModelError, match="authored timeout"):
        client.chat("fixture-model", MESSAGES)
    assert len(attempts) == 3
    assert delays == [2, 4]


def test_unrelated_transport_error_is_not_retried_or_reclassified():
    attempts, delays = [], []
    original = ValueError("authored invalid response")

    def transport(*args):
        attempts.append(1)
        raise original

    client = OpenAICompatClient(api_key="offline-fixture", retries=2,
                               transport=transport, sleep=delays.append)
    with pytest.raises(ValueError) as caught:
        client.chat("fixture-model", MESSAGES)
    assert caught.value is original
    assert len(attempts) == 1
    assert delays == []


def test_terminal_http_error_still_fails_without_retry():
    attempts, delays = [], []

    def transport(url, *args):
        attempts.append(1)
        raise urllib.error.HTTPError(url, 400, "authored bad request", {},
                                     io.BytesIO(b"invalid fixture"))

    client = OpenAICompatClient(api_key="offline-fixture", retries=2,
                               transport=transport, sleep=delays.append)
    with pytest.raises(ModelError, match="HTTP 400"):
        client.chat("fixture-model", MESSAGES)
    assert len(attempts) == 1
    assert delays == []


def changed_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "sample.py"
    source.write_text("def double(value):\n    return value\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    existing = tests / "test_existing.py"
    existing.write_text("from sample import double\n\ndef test_zero():\n    assert double(0) == 0\n",
                        encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=Authored Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "authored baseline"],
                   cwd=repo, check=True, capture_output=True)
    source.write_text("def double(value):\n    return value * 2\n", encoding="utf-8")
    diff = subprocess.run(["git", "diff", "--", "*.py"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout
    path = tmp_path / "change.diff"
    path.write_text(diff, encoding="utf-8")
    return repo, path, source.read_bytes(), existing.read_bytes()


def run_cli(monkeypatch, repo, diff, output, client):
    # Inject only the local endpoint/deadline; exercise the unmodified real CLI.
    monkeypatch.setattr(cli, "make_client", lambda *args, **kwargs: client)
    monkeypatch.setenv("TESTPILOT_PLANNER_MODEL", "fixture-plan")
    monkeypatch.setenv("TESTPILOT_EDITOR_MODEL", "fixture-editor")
    monkeypatch.setenv("TESTPILOT_PRICES", "{}")
    return cli.main(["run", "--repo", str(repo), "--diff", str(diff),
                     "--backend", "openai", "--rounds", "1", "--timeout", "30",
                     "--out", str(output)])


def assert_originals_and_patch(repo, output, source, existing):
    assert (repo / "sample.py").read_bytes() == source
    assert (repo / "tests/test_existing.py").read_bytes() == existing
    assert not (repo / "tests/test_generated_double.py").exists()
    result = subprocess.run(["git", "apply", "--check", str(output / "testpilot.patch")],
                            cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_real_cli_recovers_and_writes_passing_tests_and_reports(tmp_path, monkeypatch):
    repo, diff, source, existing = changed_repo(tmp_path)
    output, delays = tmp_path / "output", []
    with local_chat([None, PLAN, GOOD]) as (url, requests):
        exit_code = run_cli(monkeypatch, repo, diff, output, local_client(url, delays))
        assert exit_code == 0
        assert len(requests) == 3
        assert requests[0] == requests[1]
        assert requests[2]["payload"]["model"] == "fixture-editor"
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "passed"
    assert report["tests_written"] == 2
    assert report["final"]["passed"] == 3
    assert len(report["ledger"]["entries"]) == 2
    assert report["ledger"]["total_tokens"] == 20
    assert "passed" in (output / "report.md").read_text()
    assert delays == [2]
    assert_originals_and_patch(repo, output, source, existing)


def test_real_cli_repair_timeout_retains_failing_patch_and_writes_error_report(tmp_path, monkeypatch):
    repo, diff, source, existing = changed_repo(tmp_path)
    output, delays = tmp_path / "output", []
    with local_chat([PLAN, BAD, None, None]) as (url, requests):
        exit_code = run_cli(monkeypatch, repo, diff, output, local_client(url, delays))
        assert exit_code == 1
        assert len(requests) == 4
        assert requests[2] == requests[3]
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "model_error"
    assert "timed out" in report["message"]
    assert report["tests_written"] == 1
    assert report["final"]["failed"] == 1
    assert len(report["ledger"]["entries"]) == 2
    assert report["ledger"]["total_tokens"] == 20
    assert "model_error" in (output / "report.md").read_text()
    assert "== 5" in (output / "testpilot.patch").read_text()
    assert delays == [2]
    assert_originals_and_patch(repo, output, source, existing)
