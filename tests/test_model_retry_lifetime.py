"""Receive HTTP-error ownership through real, authored localhost responses."""
import json
import threading
import unittest
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from testpilot.model import ModelError, OpenAICompatClient, _urllib_transport


MESSAGES = [{"role": "user", "content": "local response lifetime fixture"}]


@contextmanager
def responses(statuses):
    requests = []
    errors = []
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            index = len(requests)
            requests.append((self.path, request))
            status = statuses[index] if index < len(statuses) else 400
            data = ({"choices": [{"message": {"content": "received"}}], "model": "fixture",
                     "usage": {"prompt_tokens": 3, "completion_tokens": 5}}
                    if status == 200 else {"error": "authored HTTP failure"})
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            # Keep failed HTTP/1.1 connections available while the client decides
            # whether to retry. The receiver observes closure before backoff.
            if status != 200:
                release.wait(3)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()

    def transport(*args):
        try:
            return _urllib_transport(*args)
        except urllib.error.HTTPError as error:
            errors.append(error)
            raise

    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", transport, requests, errors
    finally:
        for error in errors:
            error.close()
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class RetryResponseLifetimeTests(unittest.TestCase):
    def test_each_retry_closes_its_response_before_backoff(self):
        with responses([429, 503, 200]) as (url, transport, requests, errors):
            backoffs = []
            client = OpenAICompatClient(url, "local-fixture-key", retries=2, transport=transport,
                sleep=lambda delay: backoffs.append((delay, [error.closed for error in errors])))
            result = client.chat("requested-model", MESSAGES, temperature=0.1, max_tokens=17)
            self.assertEqual(result.content, "received")
            self.assertEqual(result.usage.total_tokens, 8)
            self.assertEqual(backoffs, [(2, [True]), (4, [True, True])])
            self.assertEqual([error.closed for error in errors], [True, True])
            self.assertEqual(requests, [("/v1/chat/completions", {
                "model": "requested-model", "messages": MESSAGES,
                "temperature": 0.1, "max_tokens": 17,
            })] * 3)

    def test_retry_exhaustion_closes_all_responses_and_keeps_terminal_error(self):
        with responses([500, 502, 504]) as (url, transport, requests, errors):
            backoffs = []
            client = OpenAICompatClient(url, "local-fixture-key", retries=2, transport=transport,
                                       sleep=backoffs.append)
            with self.assertRaisesRegex(ModelError, "HTTP 504.*authored HTTP failure") as caught:
                client.chat("fixture", MESSAGES)
            self.assertIs(caught.exception.__cause__, errors[-1])
            self.assertEqual(backoffs, [2, 4])
            self.assertEqual(len(requests), 3)
            self.assertEqual([error.closed for error in errors], [True, True, True])

    def test_nonretryable_error_is_one_closed_response(self):
        with responses([400]) as (url, transport, requests, errors):
            backoffs = []
            client = OpenAICompatClient(url, "local-fixture-key", retries=2, transport=transport,
                                       sleep=backoffs.append)
            with self.assertRaisesRegex(ModelError, "HTTP 400.*authored HTTP failure") as caught:
                client.chat("fixture", MESSAGES)
            self.assertIs(caught.exception.__cause__, errors[0])
            self.assertEqual(backoffs, [])
            self.assertEqual(len(requests), 1)
            self.assertTrue(errors[0].closed)

    def test_zero_retries_closes_one_retryable_terminal_error(self):
        with responses([503]) as (url, transport, requests, errors):
            backoffs = []
            client = OpenAICompatClient(url, "local-fixture-key", retries=0, transport=transport,
                                       sleep=backoffs.append)
            with self.assertRaisesRegex(ModelError, "HTTP 503.*authored HTTP failure"):
                client.chat("fixture", MESSAGES)
            self.assertEqual(backoffs, [])
            self.assertEqual(len(requests), 1)
            self.assertTrue(errors[0].closed)


if __name__ == "__main__":
    unittest.main()
