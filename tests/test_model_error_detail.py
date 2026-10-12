"""Terminal HTTP diagnostics stop after a bounded prefix of the error body.

The real HTTP fixtures serve only authored localhost responses. Their trailing
body stays unavailable until teardown, so a useful diagnostic must not depend
on draining the provider's complete error response.
"""
import io
import json
import threading
import unittest
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from testpilot.model import ModelError, OpenAICompatClient


@contextmanager
def partial_error_response(status, prefix):
    release = threading.Event()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, json.loads(body)))
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(prefix) + 1024 * 1024))
            self.end_headers()
            self.wfile.write(prefix)
            self.wfile.flush()
            release.wait(5)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/", requests, release
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


class ErrorDetailTests(unittest.TestCase):
    def test_real_terminal_errors_keep_available_prefix_and_retry_policy(self):
        prefix = b"authored provider diagnostic: " + b"x" * 2000
        for status, retries, expected_count, expected_delays in [
            (400, 2, 1, []),
            (503, 2, 3, [2, 4]),
        ]:
            with self.subTest(status=status):
                delays = []
                with partial_error_response(status, prefix) as (url, requests, release):
                    client = OpenAICompatClient(base_url=url, api_key="offline-fixture",
                                               timeout=0.25, retries=retries,
                                               sleep=delays.append)
                    with self.assertRaises(ModelError) as caught:
                        client.chat("fixture-model", [{"role": "user", "content": "fixture"}])
                    self.assertIsInstance(caught.exception.__cause__, urllib.error.HTTPError)
                    self.assertEqual(caught.exception.__cause__.code, status)
                    self.assertEqual(str(caught.exception),
                                     f"HTTP {status} from {url}chat/completions: "
                                     + prefix.decode("utf-8")[:500])
                    self.assertFalse(release.is_set(), "the unavailable tail was never supplied")
                    self.assertEqual(len(requests), expected_count)
                    self.assertEqual(delays, expected_delays)
                    self.assertTrue(all(request == requests[0] for request in requests))

    def test_existing_utf8_character_limit_and_short_diagnostics_are_preserved(self):
        for body in [b"short diagnostic", ("🧪" * 501).encode("utf-8"),
                     b"invalid byte: \xff followed by readable text", b""]:
            with self.subTest(body_prefix=body[:30]):
                stream = io.BytesIO(body)

                def transport(url, *args):
                    raise urllib.error.HTTPError(url, 400, "authored rejection", {}, stream)

                client = OpenAICompatClient(base_url="http://fixture.invalid/v1/",
                                           api_key="offline-fixture", retries=0,
                                           transport=transport)
                with self.assertRaises(ModelError) as caught:
                    client.chat("fixture-model", [])
                self.assertEqual(str(caught.exception),
                                 "HTTP 400 from http://fixture.invalid/v1/chat/completions: "
                                 + body.decode("utf-8", "replace")[:500])
                self.assertTrue(stream.closed)

    def test_short_unfinished_prefix_keeps_existing_timeout_and_retry_policy(self):
        # A bounded read can still wait for its byte target or EOF. This repair
        # does not claim prompt delivery when the supplied prefix is shorter.
        for status, expected_count, expected_delays in [(400, 1, []), (503, 3, [2, 4])]:
            with self.subTest(status=status):
                delays = []
                with partial_error_response(status, b"short unfinished prefix") as (url, requests, _):
                    client = OpenAICompatClient(base_url=url, api_key="offline-fixture",
                                               timeout=0.25, retries=2, sleep=delays.append)
                    with self.assertRaises(ModelError) as caught:
                        client.chat("fixture-model", [])
                    self.assertEqual(str(caught.exception),
                                     f"HTTP {status} from {url}chat/completions: response body timed out")
                    self.assertEqual(len(requests), expected_count)
                    self.assertEqual(delays, expected_delays)


if __name__ == "__main__":
    unittest.main()
