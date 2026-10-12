"""Retry-After receiving through the public client and real local HTTP/CLI paths."""
import io
import json
import threading
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from testpilot import model as model_module
from testpilot.model import ModelError, OpenAICompatClient, Usage
from test_model_timeouts import (BAD, GOOD, PLAN, assert_originals_and_patch,
                                changed_repo, run_cli)

MESSAGES = [{"role": "user", "content": "synthetic retry receiving"}]
NOW = 1_700_000_000.0  # 2023-11-14 22:13:20 UTC
RESPONSE = {"choices": [{"message": {"content": "recovered"}}],
            "model": "fixture", "usage": {"prompt_tokens": 7, "completion_tokens": 3}}


class RetryBody(io.BytesIO):
    def read(self, *args):
        raise AssertionError("retry response body must not be read")


def recovering_client(value, *, status=429):
    bodies, requests, delays = [], [], []

    def transport(url, headers, body, timeout):
        requests.append((url, dict(headers), body, timeout))
        if len(requests) == 1:
            failed = RetryBody(b"unneeded diagnostic")
            bodies.append(failed)
            raise urllib.error.HTTPError(url, status, "synthetic throttle",
                                         {"Retry-After": value}, failed)
        return RESPONSE

    def sleep(delay):
        assert all(body.closed for body in bodies)
        delays.append(delay)

    return OpenAICompatClient(api_key="synthetic", transport=transport,
                               sleep=sleep), requests, delays, bodies


@pytest.mark.parametrize("value, expected", [("0", 2), ("00017", 17), ("119", 119), ("120", 120)])
def test_integer_guidance_never_shortens_backoff_or_changes_the_request(value, expected):
    client, requests, delays, bodies = recovering_client(value)
    result = client.chat("fixture", MESSAGES, max_tokens=23)
    assert delays == [expected]
    assert requests[0] == requests[1]
    assert result.content == "recovered" and result.usage == Usage(7, 3)
    assert bodies[0].closed


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_all_existing_retryable_statuses_use_guidance(status):
    client, requests, delays, _ = recovering_client("8", status=status)
    assert client.chat("fixture", MESSAGES).content == "recovered"
    assert delays == [8] and len(requests) == 2


@pytest.mark.parametrize("value", [None, "", "junk", "-1", "+4", "1.5", "NaN", "Inf", "\u0661\u0662", "3, 4"])
def test_absent_or_invalid_guidance_keeps_existing_backoff(value):
    client, _, delays, _ = recovering_client(value)
    client.chat("fixture", MESSAGES)
    assert delays == [2]


@pytest.mark.parametrize("value", [
    "Tue, 14 Nov 2023 22:13:30 GMT",
    "Tuesday, 14-Nov-23 22:13:30 GMT",
    "Tue Nov 14 22:13:30 2023",
])
def test_http_date_formats_use_the_utc_clock(value, monkeypatch):
    monkeypatch.setattr(model_module.time, "time", lambda: NOW)
    client, _, delays, _ = recovering_client(value)
    client.chat("fixture", MESSAGES)
    assert delays == [10]


def test_past_http_date_keeps_backoff(monkeypatch):
    monkeypatch.setattr(model_module.time, "time", lambda: NOW)
    client, _, delays, _ = recovering_client("Tue, 14 Nov 2023 22:13:19 GMT")
    client.chat("fixture", MESSAGES)
    assert delays == [2]


@pytest.mark.parametrize("value", ["121", "9" * 5000, "Tue, 14 Nov 2023 22:15:21 GMT"])
def test_excessive_provider_wait_refuses_without_early_retry_or_body_read(value, monkeypatch):
    monkeypatch.setattr(model_module.time, "time", lambda: NOW)
    client, requests, delays, bodies = recovering_client(value)
    with pytest.raises(ModelError, match="Retry-After.*120") as caught:
        client.chat("fixture", MESSAGES)
    assert isinstance(caught.value.__cause__, urllib.error.HTTPError)
    assert len(requests) == 1 and delays == [] and bodies[0].closed


def test_obsolete_year_uses_the_rolling_fifty_year_window(monkeypatch):
    now = datetime(2026, 10, 12, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr(model_module.time, "time", lambda: now)
    client, requests, delays, bodies = recovering_client("Tuesday, 01-Jan-69 00:00:00 GMT")
    with pytest.raises(ModelError, match="Retry-After.*120"):
        client.chat("fixture", MESSAGES)
    assert len(requests) == 1 and not delays and bodies[0].closed


@pytest.mark.parametrize("status, retries", [(400, 2), (429, 0)])
def test_terminal_and_exhausted_errors_ignore_retry_guidance(status, retries):
    calls, delays, bodies = [], [], []

    def transport(url, *args):
        calls.append(1)
        body = io.BytesIO(b"terminal detail")
        bodies.append(body)
        raise urllib.error.HTTPError(url, status, "synthetic terminal",
                                     {"Retry-After": "121"}, body)

    client = OpenAICompatClient(api_key="synthetic", transport=transport,
                               sleep=delays.append, retries=retries)
    with pytest.raises(ModelError, match=f"HTTP {status}.*terminal detail"):
        client.chat("fixture", MESSAGES)
    assert calls == [1] and not delays and bodies[0].closed


@contextmanager
def local_replies(replies):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, raw))
            index = len(requests) - 1
            status, retry_after, text = replies[index] if index < len(replies) else (400, None, "unexpected retry")
            payload = json.loads(raw)
            body = json.dumps({"model": payload["model"], "choices": [{"message": {"content": text}}],
                               "usage": {"prompt_tokens": 7, "completion_tokens": 3}}).encode()
            self.send_response(status)
            if retry_after is not None:
                self.send_header("retry-after", retry_after)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_real_http_recovery_reaches_the_existing_cli_and_passing_outputs(tmp_path, monkeypatch):
    repo, diff, source, existing = changed_repo(tmp_path)
    output, delays = tmp_path / "output", []
    with local_replies([(429, "7", "throttled"), (200, None, PLAN), (200, None, GOOD)]) as (url, requests):
        client = OpenAICompatClient(base_url=url, api_key="synthetic", timeout=1, sleep=delays.append)
        assert run_cli(monkeypatch, repo, diff, output, client) == 0
        assert len(requests) == 3 and requests[0] == requests[1]
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "passed" and report["final"]["passed"] == 3
    assert report["ledger"]["total_tokens"] == 20 and len(report["ledger"]["entries"]) == 2
    assert delays == [7]
    assert_originals_and_patch(repo, output, source, existing)


def test_real_http_long_wait_retains_completed_work_in_cli_error_outputs(tmp_path, monkeypatch):
    repo, diff, source, existing = changed_repo(tmp_path)
    output, delays = tmp_path / "output", []
    with local_replies([(200, None, PLAN), (200, None, BAD), (503, "121", "unavailable")]) as (url, requests):
        client = OpenAICompatClient(base_url=url, api_key="synthetic", timeout=1, sleep=delays.append)
        assert run_cli(monkeypatch, repo, diff, output, client) == 1
        assert len(requests) == 3
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "model_error" and "Retry-After" in report["message"]
    assert report["final"]["failed"] == 1 and report["ledger"]["total_tokens"] == 20
    assert len(report["ledger"]["entries"]) == 2 and not delays
    assert "== 5" in (output / "testpilot.patch").read_text()
    assert (output / "report.md").is_file() and (output / "report.html").is_file()
    assert_originals_and_patch(repo, output, source, existing)
