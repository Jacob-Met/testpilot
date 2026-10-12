"""Independent lifetime receiving with real loopback HTTP and captured HTTPError handles."""
from __future__ import annotations
import hashlib
import http.server
import importlib.util
import json
from pathlib import Path
import sys
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
SUCCESS = json.dumps({"choices": [{"message": {"content": "fixture-ok"}}], "model": "served-fixture", "usage": {"prompt_tokens": 3, "completion_tokens": 5}}).encode()
ERROR = ("local diagnostic: observation only. " * 100).encode()
MESSAGES = [{"role": "user", "content": "independent local fixture"}]


class InterruptedBackoff(Exception):
    pass


def load(name):
    file = ROOT / name / "model.py"
    spec = importlib.util.spec_from_file_location("received_testpilot_" + name, file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_case(module, name, statuses, *, interrupt=False):
    requests, errors, snapshots, waits, entry_checks = [], [], [], [], []

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append({"path": self.path, "body": body.decode(), "authorization": self.headers.get("Authorization"), "content_type": self.headers.get("Content-Type")})
            status = statuses[len(requests) - 1]
            data = SUCCESS if status == 200 else ERROR
            self.send_response(status)
            self.send_header("Content-Type", "application/json" if status == 200 else "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    class Server(http.server.ThreadingHTTPServer):
        daemon_threads = True

        def handle_error(self, *_):
            pass  # Closing an unread fixture error can reset this owned socket.

    server = Server(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    base_url = "http://127.0.0.1:" + str(server.server_port) + "/"

    def transport(url, headers, body, timeout):
        assert url == base_url + "chat/completions"
        if errors:
            entry_checks.append([entry["error"].closed for entry in errors])
        try:
            return module._urllib_transport(url, headers, body, timeout)
        except urllib.error.HTTPError as error:
            entry = {"error": error, "reads": []}
            original_read = error.read

            def recorded_read(*args, **kwargs):
                entry["reads"].append({"args": list(args), "kwargs": kwargs})
                return original_read(*args, **kwargs)

            error.read = recorded_read
            errors.append(entry)
            raise

    interruption = InterruptedBackoff("independent backoff interrupted")

    def backoff(delay):
        waits.append(delay)
        snapshots.append([{"status": entry["error"].code, "closed": entry["error"].closed, "underlying_closed": entry["error"].fp.closed, "reads": list(entry["reads"])} for entry in errors])
        if interrupt:
            raise interruption

    client = module.OpenAICompatClient(base_url=base_url, api_key="local-fixture-no-provider-credential", retries=2, timeout=2, transport=transport, sleep=backoff)
    response = caught = None
    try:
        try:
            response = client.chat("requested-fixture", MESSAGES, temperature=0.3, max_tokens=11)
        except Exception as error:
            caught = error
        result = {"name": name, "requests": requests, "backoff_delays": waits, "response_state_during_backoff": snapshots,
                  "prior_responses_closed_at_next_post": entry_checks,
                  "terminal_error": None if caught is None else {"type": type(caught).__name__, "message": str(caught)},
                  "error_reads": [entry["reads"] for entry in errors],
                  "response": None if response is None else {"content": response.content, "model": response.model, "prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "estimated": response.usage.estimated}}
        failures = []

        def expect(value, description):
            if not value:
                failures.append(description)

        expect(len(requests) == len(statuses), "Exact expected POST count")
        expected_payload = {"model": "requested-fixture", "messages": MESSAGES, "temperature": 0.3, "max_tokens": 11}
        expect(all(request["path"] == "/chat/completions" and json.loads(request["body"]) == expected_payload for request in requests), "Request path and payload preserved")
        expect(len({request["body"] for request in requests}) == 1, "Identical request bytes across retries")
        expect(all(request["authorization"] == "Bearer local-fixture-no-provider-credential" and request["content_type"] == "application/json" for request in requests), "Local fixture headers preserved")
        if snapshots:
            expect(all(item["closed"] and item["underlying_closed"] and item["reads"] == [] for snapshot in snapshots for item in snapshot), "Unread error response must be closed before backoff")
            expect(all(all(snapshot) for snapshot in entry_checks), "Previous error response must be closed before next POST")
        if interrupt:
            expect(caught is interruption and response is None and waits == [2], "Same interruption escapes first backoff with no retry POST")
        elif statuses[-1] == 200:
            expect(caught is None and result["response"] == {"content": "fixture-ok", "model": "served-fixture", "prompt_tokens": 3, "completion_tokens": 5, "estimated": False}, "Success response and exact usage preserved")
            expect(waits == ([2, 4] if len(statuses) == 3 else []), "Retry delays preserved")
        else:
            expect(isinstance(caught, module.ModelError) and str(caught) == f"HTTP 401 from {base_url}chat/completions: " + ERROR.decode()[:500], "Terminal diagnostic text preserved")
            expect(waits == [] and len(errors) == 1 and errors[0]["reads"] == [{"args": [2000], "kwargs": {}}] and errors[0]["error"].closed, "Terminal bounded diagnostic read and close preserved")
        result["status"] = "passed" if not failures else "failed"
        result["failures"] = failures
        return result
    finally:
        for entry in errors:
            entry["error"].close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), "Owned HTTP server did not stop"


contract = json.loads((ROOT / "frozen-contract.json").read_text())
summaries = []
for source in contract["sources"]:
    name = source["name"]
    file = ROOT / name / "model.py"
    assert hashlib.sha256(file.read_bytes()).hexdigest() == source["sha256"]
    module = load(name)
    cases = [run_case(module, "two-unread-retries-then-success", [503, 429, 200]),
             run_case(module, "unread-response-before-interrupted-backoff", [503], interrupt=True),
             run_case(module, "terminal-401-diagnostic-control", [401]),
             run_case(module, "immediate-success-control", [200])]
    assert hashlib.sha256(file.read_bytes()).hexdigest() == source["sha256"]
    receipt = {"schema": "testpilot.http-close-independent-receiving.v1", "source": source,
               "python": sys.version.split()[0], "actual_loopback_http": True, "provider_requests": 0,
               "source_unchanged": True, "cases": cases, "passed": sum(case["status"] == "passed" for case in cases), "total": len(cases)}
    (ROOT / (name + "-receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    summaries.append({"source": name, "passed": receipt["passed"], "total": receipt["total"]})
print(json.dumps(summaries))
assert summaries == [{"source": "original", "passed": 2, "total": 4}, {"source": "candidate", "passed": 4, "total": 4}], "Independent before/after contract did not hold"
