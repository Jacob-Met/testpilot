"""Admission of authored local model replies before they can discard run output."""
import http.client
import json
import os
import subprocess
import sys
import threading
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from testpilot.model import ModelError, OpenAICompatClient, Usage, estimate_tokens

MESSAGES = [{"role": "user", "content": "authored protocol boundary"}]
PLAN = "Check the changed step function with an explicit assertion."
FENCE = chr(96) * 3
TEST_SOURCE = "from sample import step\n\ndef test_step():\n    assert step(2) == 4\n"
EDITOR = FENCE + "python path=tests/test_generated_step.py\n" + TEST_SOURCE + FENCE


def reply(content="literal reply", **fields):
    return {"choices": [{"message": {"content": content}}], **fields}


def encoded(content):
    return json.dumps(reply(content, model="fixture-model",
                            usage={"prompt_tokens": 14, "completion_tokens": 6})).encode()


@contextmanager
def local_responses(bodies):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            index = len(calls)
            calls.append({"path": self.path, "payload": payload})
            entry = bodies[index] if index < len(bodies) else b"unexpected extra request"
            status, body, *length = entry if isinstance(entry, tuple) else (200, entry)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(length[0] if length else len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


@pytest.mark.parametrize("body, cause", [
    (b"{not a completion", json.JSONDecodeError),
    (b'{"choices":[{"message":{"content":"\xff"}}]}', UnicodeDecodeError),
])
def test_real_http_decode_failures_are_terminal_model_errors(body, cause):
    delays = []
    with local_responses([body]) as (url, calls):
        client = OpenAICompatClient(base_url=url, api_key="local-fixture", retries=2,
                                   timeout=2, sleep=delays.append)
        with pytest.raises(ModelError, match="decoded as UTF-8 JSON") as caught:
            client.chat("fixture-model", MESSAGES)
        assert isinstance(caught.value.__cause__, cause)
        assert len(calls) == 1
        assert calls[0]["path"] == "/v1/chat/completions"
    assert delays == []


@pytest.mark.parametrize("payload", [
    None, [], 3, "text", {}, {"choices": []},
    reply(False), reply(0), reply([]), reply({}), reply(["text"]),
    reply("\ud800"), reply(model=None), reply(model=[]), reply(model="\udfff"),
    reply(usage=[]), reply(usage=False), reply(usage=1),
    reply(usage={"prompt_tokens": None}),
    reply(usage={"prompt_tokens": "not a count"}),
    reply(usage={"prompt_tokens": 1, "completion_tokens": {}}),
    reply(usage={"prompt_tokens": float("inf")}),
])
def test_unusable_completion_fields_are_model_errors_before_return(payload):
    calls, delays = [], []

    def transport(*args):
        calls.append(args)
        return payload

    client = OpenAICompatClient(api_key="local-fixture", transport=transport,
                               retries=2, sleep=delays.append)
    with pytest.raises(ModelError, match="unexpected response"):
        client.chat("fixture-model", MESSAGES)
    assert len(calls) == 1
    assert delays == []


@pytest.mark.parametrize("payload, content, model, usage", [
    (reply("exact <text> & 雪\r\n", model="returned",
           usage={"prompt_tokens": 17, "completion_tokens": 0}),
     "exact <text> & 雪\r\n", "returned", Usage(17, 0)),
    (reply(None, usage={"prompt_tokens": 0}), "", "requested", Usage(0, 0)),
    (reply("", usage={"prompt_tokens": "12", "completion_tokens": "3"}),
     "", "requested", Usage(12, 3)),
    (reply("numeric compatibility", usage={"prompt_tokens": 12.0, "completion_tokens": 3.0}),
     "numeric compatibility", "requested", Usage(12, 3)),
    (reply("missing usage"), "missing usage", "requested", None),
    (reply("null usage", usage=None), "null usage", "requested", None),
    (reply("empty usage", usage={}), "empty usage", "requested", None),
    (reply("extra metadata", usage={"other": 4}, extra={"retained": True}),
     "extra metadata", "requested", None),
])
def test_valid_text_null_content_usage_and_model_fallback_keep_existing_behavior(
        payload, content, model, usage):
    result = OpenAICompatClient(api_key="local-fixture", transport=lambda *args: payload).chat(
        "requested", MESSAGES)
    assert result.content == content
    assert result.model == model
    expected = usage or Usage(estimate_tokens(MESSAGES[0]["content"]),
                              estimate_tokens(content), estimated=True)
    assert result.usage == expected
    assert result.raw is payload


@pytest.mark.parametrize("error", [
    ValueError("custom transport"), TypeError("custom transport"),
    AssertionError("custom transport"), KeyboardInterrupt(),
])
def test_unrelated_custom_transport_exceptions_remain_exact(error):
    calls, delays = [], []

    def transport(*args):
        calls.append(1)
        raise error

    client = OpenAICompatClient(api_key="local-fixture", transport=transport,
                               retries=2, sleep=delays.append)
    with pytest.raises(type(error)) as caught:
        client.chat("fixture-model", MESSAGES)
    assert caught.value is error
    assert calls == [1] and delays == []


def make_project(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    (repo / "tests").mkdir()
    source = repo / "sample.py"
    existing = repo / "tests" / "test_existing.py"
    source.write_text("def step(value):\n    return value\n", encoding="utf-8")
    existing.write_text("from sample import step\n\ndef test_integer():\n"
                        "    assert isinstance(step(0), int)\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "."],
                 ["-c", "user.name=Protocol Fixture", "-c",
                  "user.email=fixture@example.invalid", "commit", "-qm", "authored baseline"]):
        subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)
    source.write_text("def step(value):\n    return value + 1\n", encoding="utf-8")
    return repo, {source: source.read_bytes(), existing: existing.read_bytes()}


@pytest.mark.parametrize("stage, malformed", [
    (0, b"not JSON"), (1, b"not JSON"), (2, b"not JSON"),
    (2, b"\xff"), (2, (200, b"cut", 30)),
    (2, json.dumps(reply(["not text"])).encode()),
    (2, json.dumps(reply("repair", usage={"prompt_tokens": "unknown"})).encode()),
    (2, json.dumps(reply("\ud800")).encode()),
])
def test_real_cli_saves_completed_work_when_later_response_is_unusable(
        tmp_path, stage, malformed):
    repo, original_bytes = make_project(tmp_path)
    output = tmp_path / "output"
    bodies = [encoded(PLAN), encoded(EDITOR)][:stage] + [malformed]
    env = {k: v for k, v in os.environ.items() if not k.startswith("TESTPILOT_")}
    env.update(NEBIUS_API_KEY="local-fixture", TESTPILOT_PLANNER_MODEL="fixture-model",
               TESTPILOT_EDITOR_MODEL="fixture-model", TESTPILOT_PRICES="{}")
    with local_responses(bodies) as (url, calls):
        process = subprocess.run(
            [sys.executable, "-m", "testpilot", "run", "--repo", str(repo),
             "--git-base", "HEAD", "--backend", "openai", "--base-url", url,
             "--rounds", "1", "--timeout", "30", "--no-coverage", "--out", str(output)],
            cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True,
            text=True, timeout=90,
        )
        assert process.returncode == 1, process.stdout + process.stderr
        assert "Traceback" not in process.stderr
        assert len(calls) == stage + 1, "No replay of an unusable completed response"
    assert {p.name for p in output.iterdir()} == {
        "report.json", "report.md", "report.html", "testpilot.patch"}
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "model_error"
    assert report["plan"] == (PLAN if stage else "")
    assert len(report["ledger"]["entries"]) == stage
    assert report["ledger"]["total_tokens"] == stage * 20
    if stage == 2:
        assert report["tests_written"] == 1
        assert report["test_files"] == {"tests/test_generated_step.py": TEST_SOURCE}
        assert len(report["rounds"]) == 1
        assert report["final"]["failed"] == 1
        assert report["final"]["passed"] == 1
        assert "assert 3 == 4" in calls[2]["payload"]["messages"][-1]["content"]
        patch_check = subprocess.run(["git", "apply", "--check", str(output / "testpilot.patch")],
                                     cwd=repo, capture_output=True, text=True)
        assert patch_check.returncode == 0, patch_check.stderr
    else:
        assert report["test_files"] == {}
        assert report["rounds"] == []
        assert report["final"] is None
    for path, original in original_bytes.items():
        assert path.read_bytes() == original
    assert not (repo / "tests/test_generated_step.py").exists()


def test_malformed_reply_after_retryable_http_error_does_not_replay_again():
    delays = []
    with local_responses([(503, b"temporary fixture failure"), b"{unusable reply"]) as (url, calls):
        client = OpenAICompatClient(base_url=url, api_key="local-fixture", retries=2,
                                   timeout=2, sleep=delays.append)
        with pytest.raises(ModelError, match="decoded as UTF-8 JSON"):
            client.chat("fixture-model", MESSAGES)
        assert len(calls) == 2
        assert calls[0] == calls[1]
    assert delays == [2]


@pytest.mark.parametrize("kind", ["integer-limit", "nesting-limit"])
def test_real_json_decoder_limits_are_terminal_model_errors(kind):
    if kind == "integer-limit":
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            pytest.skip("This interpreter explicitly disables the integer digit limit")
        body, cause = b"7" * (limit + 1), ValueError
    else:
        depth = 4000  # Exercise the native JSON decoder's own nesting limit.
        body, cause = b"[" * depth + b"0" + b"]" * depth, RecursionError
    delays = []
    with local_responses([body]) as (url, calls):
        client = OpenAICompatClient(base_url=url, api_key="local-fixture", retries=2,
                                   timeout=2, sleep=delays.append)
        with pytest.raises(ModelError, match="decoded as UTF-8 JSON") as caught:
            client.chat("fixture-model", MESSAGES)
        assert isinstance(caught.value.__cause__, cause)
        assert len(calls) == 1
    assert delays == []


@pytest.mark.parametrize("status", [200, 400, 503])
def test_truncated_http_body_preserves_terminal_status_and_retry_budget(status):
    delays = []
    expected_calls = 3 if status == 503 else 1
    with local_responses([(status, b"cut", 30)] * expected_calls) as (url, calls):
        client = OpenAICompatClient(base_url=url, api_key="local-fixture", retries=2,
                                   timeout=2, sleep=delays.append)
        with pytest.raises(ModelError, match="response body incomplete") as caught:
            client.chat("fixture-model", MESSAGES)
        assert len(calls) == expected_calls
        assert all(call == calls[0] for call in calls)
        if status == 200:
            assert isinstance(caught.value.__cause__, http.client.IncompleteRead)
        else:
            assert isinstance(caught.value.__cause__, urllib.error.HTTPError)
            assert caught.value.__cause__.code == status
            assert f"HTTP {status}" in str(caught.value)
    assert delays == ([2, 4] if status == 503 else [])
