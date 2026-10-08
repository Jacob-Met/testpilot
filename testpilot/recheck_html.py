"""Passive offline view of one completed native saved-test recheck.

The supplied bytes are the JSON artifact, not an execution request. Rendering
never rechecks tests, follows file paths, calls a model or applies a patch.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json


def _text(value: object) -> str:
    text = str(value)
    # HTML cannot faithfully retain NUL, CR or isolated surrogate code points.
    # Make those visible in the reading view; the download retains exact bytes.
    text = "".join(
        f"\\u{ord(char):04x}" if (
            ord(char) < 32 and char not in "\n\t"
            or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        ) else char for char in text
    )
    return html.escape(text, quote=True)


def _value(value: object) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    return _text(value)


def _facts(items: list[tuple[str, object]]) -> str:
    return '<dl class="facts">' + "".join(
        f"<dt>{_text(label)}</dt><dd>{_value(value)}</dd>" for label, value in items
    ) + "</dl>"


_STYLE = """
:root{font:16px/1.55 system-ui,sans-serif;color:#172635;background:#f2f5f8}
*{box-sizing:border-box}body{margin:0}main{max-width:1080px;margin:auto;padding:36px 24px 64px}
h1{font-size:clamp(1.8rem,5vw,2.8rem);line-height:1.15;margin:.35em 0}
h2{font-size:1.4rem;margin:0 0 .8rem}h3{font-size:1.05rem;margin:.25em 0}
p{max-width:78ch}.eyebrow{font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#466273}
nav{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0}a{color:#075c86;text-underline-offset:3px}
nav a,.download{display:inline-block;border:1px solid #9bb2c3;border-radius:6px;padding:9px 13px;background:white}
a:focus-visible,summary:focus-visible{outline:3px solid #db8700;outline-offset:4px}
section{background:white;border:1px solid #cad7e0;border-radius:10px;padding:24px;margin:20px 0}
.status{font-size:1.35rem;font-weight:750}.note{border-left:4px solid #9bb2c3;padding:8px 14px;color:#374f60}
.facts{display:grid;grid-template-columns:minmax(140px,1fr) minmax(0,3fr);gap:9px 20px;margin:16px 0}
dt{font-weight:650}dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}
.table-scroll{overflow:auto;border:1px solid #d5dfe6;border-radius:6px}
table{border-collapse:collapse;width:100%;text-align:left}th,td{padding:9px 12px;border-bottom:1px solid #d5dfe6;vertical-align:top}
th{background:#edf3f7}td:first-child{font-weight:600}tr:last-child td{border-bottom:0}
details{border:1px solid #cbd8e2;border-radius:7px;padding:12px 16px;margin:12px 0}
summary{cursor:pointer;font-weight:650;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#f3f6f9;border:1px solid #d6e0e8;border-radius:6px;padding:15px;font:13px/1.6 ui-monospace,monospace}
code{font-family:ui-monospace,monospace;overflow-wrap:anywhere}.muted{color:#4f6879}
@media(max-width:580px){main{padding:20px 12px 40px}section{padding:17px 14px}.facts{grid-template-columns:minmax(0,1fr);gap:3px}dd{margin-bottom:10px}details{padding:12px}th,td{padding:8px}}
@media print{:root{color:black;background:white}main{max-width:none;padding:0}section{border-radius:0;break-inside:avoid}nav,.download{display:none}details{break-inside:avoid}pre{background:white}a{color:inherit}}
"""


def render_recheck_html(raw: bytes) -> str:
    """Render the native recheck JSON and embed that exact artifact for download."""
    if not isinstance(raw, bytes):
        raise TypeError("recheck HTML requires the serialized JSON bytes")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "testpilot.recheck/1":
        raise ValueError("recheck HTML requires the native testpilot.recheck/1 result")
    final = data["final"]
    source = data["source_report"]
    retained = data["retained_tests"]
    observed = final["junit_available"]
    encoded = base64.b64encode(raw).decode("ascii")
    sections = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>TestPilot saved-test recheck</title>',
        f"<style>{_STYLE}</style></head><body><main>",
        '<header><p class="eyebrow">TestPilot · saved-test recheck</p>',
        '<h1>Inspect the current test result</h1>',
        '<p>The saved tests were checked against the selected checkout. This page reads that completed result; opening it runs no tests or model calls.</p>',
        f'<a class="download" download="recheck.json" href="data:application/json;base64,{encoded}">Download exact recheck JSON</a></header>',
        '<nav aria-label="Report sections"><a href="#result">Current result</a><a href="#cases">Test cases</a><a href="#retained">Retained source</a><a href="#origin">Run identity</a><a href="#output">Recorded output</a></nav>',
        '<section id="result" aria-labelledby="result-title"><h2 id="result-title">Current result</h2>',
        f'<p class="status" id="current-status">{_text(data["status"])}</p>',
        _facts([
            ("Native success", data["ok"]), ("Native run summary", final["summary"]),
            ("Return code", final["returncode"]), ("Timed out", final["timed_out"]),
            ("Duration (seconds)", final["duration_s"]), ("Timeout (seconds)", final["timeout_s"]),
            ("JUnit available", observed), ("New model calls", data["model_calls"]),
        ]),
        '<p class="note">A passing selected suite alone does not qualify the retained tests: the native result also requires a retained case to pass. Historical status is shown separately below.</p>',
    ]
    if observed:
        generated = final["generated"]
        sections.append('<div class="table-scroll"><table><caption>Recorded case counts</caption><thead><tr><th scope="col">Scope</th><th scope="col">Passed</th><th scope="col">Failed</th><th scope="col">Errors</th><th scope="col">Skipped</th><th scope="col">Collected</th></tr></thead><tbody>')
        all_counts = [final[key] for key in ("passed", "failed", "errors", "skipped")]
        sections.append('<tr><th scope="row">Selected suite</th>' + "".join(f"<td>{_value(x)}</td>" for x in [*all_counts, len(final["cases"])]))
        sections.append('</tr><tr><th scope="row">Retained tests</th>' + "".join(
            f"<td>{_value(generated.get(key) if generated is not None else None)}</td>"
            for key in ("passed", "failed", "error", "skipped", "collected")
        ) + "</tr></tbody></table></div>")
    else:
        sections.append('<p class="note" id="unavailable-counts">Case counts are unavailable because this run has no complete JUnit result. Empty recorded case lists and zero count fields are not evidence that no tests ran or that tests passed.</p>')
    sections.extend([
        '</section><section id="cases" aria-labelledby="cases-title"><h2 id="cases-title">Recorded test cases</h2>',
        '<p>Cases remain in recorded order. Native retained-file attribution is shown independently of each case name.</p>',
    ])
    for index, case in enumerate(final["cases"], 1):
        sections.extend([
            f'<details><summary>{index}. {_text(case["outcome"])} · {_text(case["nodeid"])}</summary>',
            _facts([("Recorded node ID", case["nodeid"]), ("Outcome", case["outcome"]),
                    ("Retained-file attribution", case.get("generated_file"))]),
            f'<h3>Recorded diagnostic</h3><pre>{_text(case["message"])}</pre>' if case["message"] else '<p>No diagnostic text was recorded for this case.</p>',
            '</details>',
        ])
    if not final["cases"]:
        sections.append('<p>No individual case records are available in this result.</p>')
    sections.extend([
        '</section><section id="retained" aria-labelledby="retained-title"><h2 id="retained-title">Exact retained test source</h2>',
        '<p>Source below is reading text. Nothing here applies files to a checkout or runs Python. Placement describes the original recheck; the JSON download retains the exact source characters.</p>',
    ])
    for index, item in enumerate(retained, 1):
        sections.extend([
            f'<details><summary>{index}. {_text(item["path"])}</summary>',
            _facts([("Path", item["path"]), ("Placement", item["placement"]),
                    ("UTF-8 bytes", item["bytes"]), ("SHA-256", item["sha256"])]),
            f'<pre>{_text(data["test_files"][item["path"]])}</pre></details>',
        ])
    sections.extend([
        '</section><section id="origin" aria-labelledby="origin-title"><h2 id="origin-title">Run and source identity</h2>',
        _facts([
            ("Schema", data["schema"]), ("Selected checkout path", data["repo"]),
            ("Selected Python", data["python"]), ("Started at", data["started_at"]),
            ("Finished at", data["finished_at"]), ("Source report path", source["path"]),
            ("Source report SHA-256", source["sha256"]),
            ("Historical source status (not this result)", source["recorded_status"]),
            ("This recheck JSON SHA-256", hashlib.sha256(raw).hexdigest()),
            ("Native scope", data["scope"]),
        ]),
        '<p class="note">The source report status remains historical. This recheck adds no model diagnosis, comparison with historical coverage, repository commit identity or guarantee against concurrent checkout changes.</p>',
        '</section><section id="output" aria-labelledby="output-title"><h2 id="output-title">Recorded pytest output tail</h2>',
        '<p>This is the output tail retained by the native result (up to its last 3,000 characters), not a complete log.</p>',
        f'<pre>{_text(final["output"])}</pre>',
        '</section><footer><p class="muted">All report content is local. Reading text visibly escapes HTML-incompatible controls and isolated surrogates; the exact JSON download remains unchanged. Expand source and diagnostics before printing the sections you need.</p></footer>',
        '</main></body></html>\n',
    ])
    return "".join(sections)
