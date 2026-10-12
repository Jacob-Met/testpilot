"""Independent public-API review of TestPilot's bounded Retry-After contract.

Run against a reviewed model.py path. No provider connection or real sleeping is
performed. The fake transport returns tracked HTTPError bodies or a fixed JSON
response. This review file is outside the source owner's candidate directory.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import Message
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import urllib.error
from unittest.mock import patch


NOW = datetime(2026, 10, 12, 21, 0, 0, tzinfo=timezone.utc).timestamp()
RESPONSE = {
    "choices": [{"message": {"content": "independent review response"}}],
    "model": "review-returned-model",
    "usage": {"prompt_tokens": 4, "completion_tokens": 6},
}
MESSAGES = [{"role": "user", "content": "Review input with Unicode: λ"}]


class TrackedBody(io.BytesIO):
    def __init__(self, events: list, label: str):
        super().__init__(b"review diagnostic")
        self.events = events
        self.label = label
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        self.events.append(["read", self.label, size])
        return super().read(size)

    def close(self):
        if not self.closed:
            self.events.append(["close", self.label])
        return super().close()


def http(value=None, status=429):
    return {"kind": "http", "value": value, "status": status}


def case(name, errors, delays=(), *, retries=None, outcome="success", now=NOW):
    return {
        "name": name,
        "errors": errors,
        "expected_delays": list(delays),
        "retries": len(errors) if retries is None else retries,
        "expected_outcome": outcome,
        "now": now,
    }


def cases():
    result = [case("missing_header", [http()], [2])]
    for value, expected in [("0", 2), ("1", 2), ("2", 2), ("119", 119), ("120", 120),
                            ("00010", 10), (" \t10\t ", 10)]:
        result.append(case("seconds_" + repr(value), [http(value)], [expected]))
    result.append(case("many_leading_zeros_at_cap", [http("0" * 5000 + "120")], [120]))
    for value in ["121", "000121", "9" * 10000]:
        label = value if len(value) < 20 else "10000_digits"
        result.append(case("refuse_seconds_" + label, [http(value)], outcome="refusal"))
    for value in ["", " ", "+10", "-10", "10.0", "1e2", "NaN", "Inf", "١٠", "²", "10, 20", "tomorrow"]:
        result.append(case("malformed_" + repr(value), [http(value)], [2]))

    for label, value in [
        ("imf_fixdate", "Mon, 12 Oct 2026 21:00:10 GMT"),
        ("rfc850", "Monday, 12-Oct-26 21:00:10 GMT"),
        ("asctime_utc", "Mon Oct 12 21:00:10 2026"),
    ]:
        result.append(case(label, [http(value)], [10]))
    result.extend([
        case("past_date", [http("Mon, 12 Oct 2026 20:59:59 GMT")], [2]),
        case("date_at_cap", [http("Mon, 12 Oct 2026 21:02:00 GMT")], [120]),
        case("date_over_cap", [http("Mon, 12 Oct 2026 21:02:01 GMT")], outcome="refusal"),
        case("fractional_clock_within_cap", [http("Mon, 12 Oct 2026 21:02:00 GMT")], [119.75], now=NOW + 0.25),
        case("fractional_clock_over_cap", [http("Mon, 12 Oct 2026 21:02:01 GMT")], outcome="refusal", now=NOW + 0.25),
        case("invalid_date_falls_back", [http("Mon, 99 Oct 2026 21:00:10 GMT")], [2]),
        case("invalid_hour_falls_back", [http("Mon, 12 Oct 2026 25:00:10 GMT")], [2]),
    ])
    future_2069 = datetime(2069, 1, 1, tzinfo=timezone.utc).strftime("%A, %d-%b-%y %H:%M:%S GMT")
    future_2068 = datetime(2068, 1, 1, tzinfo=timezone.utc).strftime("%A, %d-%b-%y %H:%M:%S GMT")
    result.extend([
        case("rfc850_future_within_50_years", [http(future_2069)], outcome="refusal"),
        case("rfc850_68_future_within_50_years", [http(future_2068)], outcome="refusal"),
        case("rfc850_80_is_past_after_50_year_rule", [http("Tuesday, 01-Jan-80 00:00:00 GMT")], [2]),
    ])
    for status in [429, 500, 502, 503, 504]:
        result.append(case(f"retry_status_{status}", [http("7", status)], [7]))
    for status in [400, 404, 501]:
        result.append(case(f"terminal_status_{status}", [http("121", status)], outcome="terminal"))
    result.extend([
        case("zero_retries_terminal_even_with_header", [http("121")], retries=0, outcome="terminal"),
        case("exhausted_retry_terminal", [http("3"), http("121")], [3], retries=1, outcome="terminal"),
        case("retry_sequence_max_each_attempt", [http("1"), http("5"), http("3")], [2, 5, 8]),
        case("provider_cap_does_not_cap_existing_backoff", [http("0")] * 7, [2, 4, 8, 16, 32, 64, 128]),
        case("connection_fallback", [{"kind": "url_error"}], [2]),
        case("timeout_fallback", [{"kind": "timeout"}, {"kind": "timeout"}], [2, 4]),
        case("mixed_connection_and_http", [{"kind": "url_error"}, http("3")], [2, 4]),
    ])
    return result


@contextmanager
def frozen_clock(module, now):
    # The source owner may expose a clock constructor parameter. If not, the
    # module's ordinary time.time seam is patched within this isolated process.
    with patch.object(module.time, "time", return_value=now):
        yield


def run_case(module, item):
    events, requests, bodies, errors, sleeps = [], [], [], [], []
    for index, spec in enumerate(item["errors"]):
        if spec["kind"] == "http":
            headers = Message()
            if spec["value"] is not None:
                headers["rEtRy-AfTeR"] = spec["value"]
            body = TrackedBody(events, str(index))
            error = urllib.error.HTTPError("https://review.invalid/v1/chat/completions", spec["status"], "review", headers, body)
            bodies.append((index, body))
        elif spec["kind"] == "url_error":
            error = urllib.error.URLError("independent review connection failure")
        else:
            error = TimeoutError("independent review timeout")
        errors.append(error)

    def transport(url, headers, body, timeout):
        index = len(requests)
        requests.append((url, dict(headers), body, timeout))
        events.append(["transport", index])
        if index < len(errors):
            raise errors[index]
        return RESPONSE

    def sleep(delay):
        for index, body in bodies:
            if index < len(requests):
                assert body.closed, "failed HTTP response remained open while waiting"
                assert body.read_sizes == [], "retry path consumed diagnostic body"
        sleeps.append(delay)
        events.append(["sleep", delay])

    client_args = {"base_url": "https://review.invalid/v1/", "api_key": "review-placeholder",
                   "timeout": 17.0, "retries": item["retries"], "transport": transport, "sleep": sleep}
    parameters = inspect.signature(module.OpenAICompatClient).parameters
    if "clock" in parameters:
        client_args["clock"] = lambda: item["now"]

    caught, response = None, None
    with frozen_clock(module, item["now"]):
        client = module.OpenAICompatClient(**client_args)
        try:
            response = client.chat("review-request-model", MESSAGES, temperature=0.375, max_tokens=13)
        except module.ModelError as error:
            caught = error

    expected_outcome = item["expected_outcome"]
    assert sleeps == item["expected_delays"], f"delays {sleeps!r} != {item['expected_delays']!r}"
    expected_requests = len(errors) + (expected_outcome == "success")
    assert len(requests) == expected_requests, f"request count {len(requests)} != {expected_requests}"
    if expected_outcome == "success":
        assert caught is None, f"unexpected ModelError: {caught}"
        assert response.content == RESPONSE["choices"][0]["message"]["content"]
        assert response.model == RESPONSE["model"]
        assert (response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.total_tokens,
                response.usage.estimated) == (4, 6, 10, False)
    else:
        assert isinstance(caught, module.ModelError), "expected ModelError was not raised"
        if expected_outcome == "refusal":
            assert "retry-after" in str(caught).lower(), f"refusal did not identify provider guidance: {caught}"
        else:
            assert f"HTTP {item['errors'][-1]['status']}" in str(caught), f"terminal status lost: {caught}"
    expected_body = json.dumps({"model": "review-request-model", "messages": MESSAGES,
                                "temperature": 0.375, "max_tokens": 13}).encode("utf-8")
    expected_request = ("https://review.invalid/v1/chat/completions",
                        {"Content-Type": "application/json", "Accept": "application/json", "Authorization": "Bearer review-placeholder"},
                        expected_body, 17.0)
    assert all(request == expected_request for request in requests), "request content changed across retries"
    for index, body in bodies:
        assert body.closed, f"HTTP body {index} was not closed"
        expected_reads = [2000] if expected_outcome == "terminal" and index == len(errors) - 1 else []
        assert body.read_sizes == expected_reads, f"unexpected body reads: {body.read_sizes!r}"
    return {"status": "passed", "delays": sleeps, "requests": len(requests), "events": events,
            "observed_error": str(caught) if caught else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    source_bytes = source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    spec = importlib.util.spec_from_file_location("independent_testpilot_review_model", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_tz = os.environ.get("TZ")
    os.environ["TZ"] = "EST5"
    time.tzset()
    started = time.perf_counter()
    outcomes = []
    try:
        for item in cases():
            try:
                outcome = run_case(module, item)
            except Exception as error:
                outcome = {"status": "failed", "error": str(error), "exception": type(error).__name__,
                           "traceback": traceback.format_exc(limit=5)}
            outcomes.append({"name": item["name"], **outcome})
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()
    assert source.read_bytes() == source_bytes, "source changed during review"
    report = {"source": str(source), "source_sha256": source_hash,
              "python": sys.version, "platform": platform.platform(), "test_timezone": "EST5",
              "base_clock_utc": "2026-10-12T21:00:00Z", "no_network": True, "no_real_sleep": True,
              "duration_seconds": time.perf_counter() - started, "cases": cases(), "outcomes": outcomes,
              "passed": sum(o["status"] == "passed" for o in outcomes),
              "failed": sum(o["status"] == "failed" for o in outcomes)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha256": source_hash, "cases": len(outcomes), "passed": report["passed"],
                      "failed": report["failed"], "report": str(args.report.resolve()),
                      "failed_cases": [o["name"] for o in outcomes if o["status"] == "failed"]}))
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
