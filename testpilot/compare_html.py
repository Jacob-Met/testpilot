"""Portable, script-free comparison of two admitted TestPilot reports."""
from __future__ import annotations

import base64
import difflib
import html
import unicodedata
from typing import Any

from .compare import SavedReport, context_relation, file_changes, target_groups

MAX_DIFF_CHARS = 200_000
MAX_DIFF_LINES = 2_000

_STYLE = """
:root{color-scheme:light;--ink:#1c2d3b;--muted:#536573;--line:#cbd7dc;--paper:#fff;--wash:#f3f6f7;--accent:#17616b}
*{box-sizing:border-box}html{scroll-padding-top:1.5rem}body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--accent);text-underline-offset:.18em}a:hover{text-decoration-thickness:2px}:focus-visible{outline:3px solid #a45100;outline-offset:4px}
.shell{width:min(1160px,100%);margin:auto;padding:2.5rem 1.5rem 4rem}.eyebrow{font-size:.76rem;letter-spacing:.15em;font-weight:750;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(2rem,5vw,3.1rem);line-height:1.1;letter-spacing:-.03em;margin:.8rem 0 1rem}h2{font-size:1.35rem;margin:0 0 1rem}h3{font-size:1.03rem;overflow-wrap:anywhere}
p{margin:.65rem 0}.lead{font-size:1.1rem;max-width:74ch}.note,.meta{font-size:.88rem;color:var(--muted)}.meta{overflow-wrap:anywhere}
.columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.columns>*{min-width:0}.panel,section{background:var(--paper);border:1px solid var(--line);border-radius:.55rem;min-width:0;padding:1.3rem}
section{margin:1.25rem 0}.panel .role{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:750}
.outcome{display:inline-block;font-size:1.15rem;font-weight:700;margin:.7rem 0 .2rem;padding:.2rem .6rem;background:#eaf2f3;border-radius:.25rem}
.context{border-left:4px solid var(--accent);background:#e9f3f2;padding:1rem 1.2rem;margin:1.2rem 0}.context strong{display:block}
nav,.actions{display:flex;gap:.7rem 1rem;flex-wrap:wrap;margin:1.4rem 0}nav{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:1rem 0}
.button{padding:.6rem .85rem;border:1px solid var(--accent);border-radius:.35rem;text-decoration:none;font-weight:650;background:white}
.skip{position:absolute;top:-120px;left:1rem;background:white;padding:.8rem}.skip:focus{top:1rem;z-index:1}
.scroll{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;min-width:28rem;font-size:.9rem;text-align:left}
th,td{border-bottom:1px solid var(--line);padding:.6rem .7rem;vertical-align:top;overflow-wrap:anywhere}th{color:var(--muted);font-weight:650}th:first-child{width:32%}caption{text-align:left;color:var(--muted);font-size:.86rem;padding:0 0 .5rem}
code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace}code{overflow-wrap:anywhere}
pre{background:#f7f9fa;border:1px solid var(--line);padding:.85rem;font-size:.83rem;line-height:1.5;overflow:auto;max-width:100%;tab-size:4;white-space:pre;margin:.7rem 0}
details{border:1px solid var(--line);border-radius:.35rem;margin:.8rem 0;min-width:0}summary{padding:.8rem;cursor:pointer;font-weight:650;overflow-wrap:anywhere}
details[open]>summary{border-bottom:1px solid var(--line);background:#f1f5f6}.detail{padding:.2rem .85rem .8rem;min-width:0}.pill{display:inline-block;padding:.08rem .4rem;margin-right:.4rem;border:1px solid var(--line);border-radius:.2rem;font-size:.75rem;font-weight:650}
.prose{white-space:pre-wrap;overflow-wrap:anywhere}ul,ol{padding-left:1.3rem}.empty{padding:.8rem;background:var(--wash)}footer{color:var(--muted);font-size:.84rem;margin-top:2rem}
@media(max-width:650px){.shell{padding:1.5rem .8rem 2.5rem}.columns{grid-template-columns:minmax(0,1fr)}.panel,section{padding:1rem}nav{font-size:.9rem}.actions .button{flex:1;text-align:center}th:first-child{width:30%}}
@media print{body{background:white;font-size:10pt}.shell{padding:0;width:100%}nav,.actions,.skip{display:none}.columns{display:block}.panel{margin:.7rem 0}section,.panel,details{border-color:#aaa}h2,h3,summary{break-after:avoid}
pre{white-space:pre-wrap;overflow-wrap:anywhere;overflow:visible}.scroll{overflow:visible}table{min-width:0;font-size:8pt}details::details-content{content-visibility:visible}details>:not(summary){display:block!important}}
"""

_LABELS = {
    "passed": "Passed",
    "failed": "Needs review",
    "suspected_code_bug": "Possible code bug",
    "no_changes": "No selected changes",
    "no_tests": "No qualified generated tests",
    "budget_exhausted": "Token budget reached",
    "model_error": "Model request failed",
}


def _text(value: Any) -> str:
    value = "Unavailable" if value is None else str(value)
    visible = "".join(
        ch.encode("unicode_escape").decode("ascii")
        if (0xD800 <= ord(ch) <= 0xDFFF
            or (unicodedata.category(ch) in {"Cc", "Zl", "Zp"} and ch not in "\n\t"))
        else ch for ch in value
    )
    return html.escape(visible, quote=True)


def _pre(value: str, label: str = "Saved text") -> str:
    return '<pre tabindex="0" aria-label="' + _text(label) + '"><code>' + _text(value) + "</code></pre>"


def _details(title: str, body: str, *, opened: bool = False, identity: str = "") -> str:
    return ('<details' + (' open' if opened else '') + (' id="' + identity + '"' if identity else '')
            + '><summary>' + title + '</summary><div class="detail">' + body + "</div></details>")


def _table(headers: list[str], rows: list[list[Any]], caption: str) -> str:
    return ('<div class="scroll" tabindex="0" role="region" aria-label="' + _text(caption)
            + '"><table><caption>' + _text(caption) + "</caption><thead><tr>"
            + "".join('<th scope="col">' + _text(x) + "</th>" for x in headers)
            + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join("<td>" + _text(cell) + "</td>" for cell in row) + "</tr>" for row in rows)
            + "</tbody></table></div>")


def _junit(report: SavedReport) -> str:
    final = report.data["final"]
    if final is None:
        return "No test result recorded"
    flag = final.get("junit_available")
    return ("Available" if flag is True else "Unavailable" if flag is False
            else "Availability was not recorded")


def _suite_counts(report: SavedReport) -> str:
    final = report.data["final"]
    if final is None or final.get("junit_available") is not True:
        return "Unavailable as complete execution evidence"
    return ", ".join(str(final[k]) + " " + k for k in ("passed", "failed", "errors", "skipped"))


def _generated_counts(report: SavedReport) -> str:
    final = report.data["final"]
    if final is None or final.get("junit_available") is not True or final.get("generated") is None:
        return "Unavailable as complete execution evidence"
    counts = final["generated"]
    return ", ".join(str(counts[k]) + " " + k for k in ("collected", "passed", "failed", "error", "skipped"))


def _cost(report: SavedReport) -> str:
    ledger = report.data["ledger"]
    return "USD " + str(ledger["total_cost_usd"]) if ledger["cost_is_complete"] else "Unpriced / incomplete"


def _physical_lines(text: str) -> list[str]:
    parts = text.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def source_diff(before: str, after: str, path: str) -> str | None:
    if len(before) + len(after) > MAX_DIFF_CHARS:
        return None
    left, right = _physical_lines(before), _physical_lines(after)
    if len(left) > MAX_DIFF_LINES or len(right) > MAX_DIFF_LINES:
        return None
    lines = difflib.unified_diff(left, right, fromfile="before/" + path, tofile="after/" + path)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def _source_side(role: str, targets: tuple) -> str:
    body = "<h3>" + role + "</h3>"
    if not targets:
        return body + '<p class="empty">This target was not selected in this report.</p>'
    for index, target in enumerate(targets):
        if len(targets) > 1:
            body += '<p class="note">Separate record ' + str(index + 1) + " of " + str(len(targets)) + "</p>"
        body += '<p class="meta">Lines ' + str(target["lineno"]) + "–" + str(target["end_lineno"])
        body += " · changed lines: " + _text(", ".join(map(str, target["changed_lines"]))) + "</p>"
        body += _pre(target["source"], role + " selected source")
    return body


def _targets(before: SavedReport, after: SavedReport) -> str:
    body = '<p class="note">Targets are grouped by their recorded path and qualified name. Repeated labels stay as separate records. These reports do not establish a full repository, commit, test configuration, or execution-environment identity.</p>'
    groups = target_groups(before, after)
    if not groups:
        return body + '<p class="empty">No selected targets are recorded.</p>'
    for group in groups:
        title = _text(group["path"] + "::" + group["qualname"])
        inside = '<div class="columns"><div>' + _source_side("Before", group["before"]) + "</div><div>"
        inside += _source_side("After", group["after"]) + "</div></div>"
        body += _details(title, inside)
    return body


def _files(before: SavedReport, after: SavedReport) -> str:
    changes = file_changes(before, after)
    body = '<p class="note">File labels are exact saved paths. “Unchanged” means the two saved source strings are equal. A changed filename stays an addition/removal; no rename or test-equivalence inference is made.</p>'
    if not changes:
        return body + '<p class="empty">Neither report retained generated files.</p>'
    rows = [[c["path"], c["status"], "Absent" if c["before"] is None else len(c["before"]),
             "Absent" if c["after"] is None else len(c["after"])] for c in changes]
    body += _table(["Saved path", "Text relation", "Before characters", "After characters"], rows, "Generated source retained in each report")
    for i, change in enumerate(changes):
        title = '<span class="pill">' + _text(change["status"]) + "</span>" + _text(change["path"])
        detail = ""
        if change["status"] != "unchanged":
            delta = source_diff(change["before"] or "", change["after"] or "", change["path"])
            if delta is None:
                detail += '<p class="note">Inline diff omitted because this file exceeds 200,000 combined characters or 2,000 physical lines per side. Complete saved source remains below and in the original JSON downloads.</p>'
            elif delta:
                detail += _pre(delta, "Saved source difference")
        if change["status"] == "unchanged":
            detail += _pre(change["before"], "Identical saved generated source")
        else:
            detail += '<div class="columns">'
            for role, key in (("Before", "before"), ("After", "after")):
                detail += "<div><h3>" + role + "</h3>"
                detail += '<p class="empty">File absent.</p>' if change[key] is None else _pre(change[key], role + " generated source")
                detail += "</div>"
            detail += "</div>"
        body += _details(title, detail, opened=change["status"] != "unchanged", identity="file-" + str(i))
    return body


def _diagnostics(report: SavedReport, role: str) -> str:
    data, final = report.data, report.data["final"]
    body = "<h3>" + role + "</h3><p class=\"prose\">" + _text(data["message"] or "No run-level message recorded.") + "</p>"
    if final is None:
        return body + '<p class="empty">No final test result is recorded.</p>'
    body += '<p class="note">JUnit: ' + _text(_junit(report)) + ". Case rows retain recorded outcomes; their labels alone do not establish identical tests across runs.</p>"
    body += '<p class="prose">' + _text(final["summary"]) + "</p>"
    for case in final["cases"]:
        title = '<span class="pill">' + _text(case["outcome"]) + "</span>" + _text(case["nodeid"])
        detail = '<p class="meta">Generated file: ' + _text(case.get("generated_file") or "Not attributed to a generated file") + "</p>"
        detail += _pre(case["message"], "Recorded test diagnostic") if case["message"] else "<p>No diagnostic text recorded.</p>"
        body += _details(title, detail)
    if not final["cases"]:
        body += '<p class="empty">No individual test cases are recorded.</p>'
    body += _details("Recorded pytest output · last 3,000 characters", _pre(final["output"], "Recorded pytest output tail"))
    return body


def _coverage_rows(before: SavedReport, after: SavedReport) -> list[list[Any]]:
    rows = []
    for label, key, suffix in [
        ("Total before generation", "total_before", "%"),
        ("Total after generation", "total_after", "%"),
        ("Within-run total change", "total_delta", " percentage points"),
        ("Executable changed lines", "changed_lines_executable", ""),
        ("Changed lines before generation", "changed_lines_before", "%"),
        ("Changed lines after generation", "changed_lines_after", "%"),
    ]:
        row = [label]
        for report in (before, after):
            coverage = report.data["coverage"]
            row.append(str(coverage[key]) + suffix if coverage else "Unavailable")
        rows.append(row)
    return rows


def _usage(report: SavedReport, role: str) -> str:
    ledger = report.data["ledger"]
    rows = [[e["role"], e["model"], e["prompt_tokens"], e["completion_tokens"],
             "Estimated" if e["estimated"] else "Provider-reported"] for e in ledger["entries"]]
    body = "<h3>" + role + "</h3>"
    if not rows:
        return body + '<p class="empty">No model calls are recorded.</p>'
    return body + _table(["Role", "Recorded model", "Prompt", "Completion", "Token basis"], rows, role + " saved call ledger, in recorded order")


def _rounds(report: SavedReport, role: str) -> str:
    body = "<h3>" + role + "</h3>"
    if not report.data["rounds"]:
        return body + '<p class="empty">No generation or repair rounds are recorded.</p>'
    for item in report.data["rounds"]:
        result = item["result"]
        text = result["summary"] if result else "No test result recorded for this round"
        detail = '<p class="prose">' + _text(text) + "</p>"
        if item["files"]:
            detail += "<ul>" + "".join("<li>" + _text(p) + "</li>" for p in item["files"]) + "</ul>"
        for warning in item["warnings"]:
            detail += '<p class="prose">' + _text(warning) + "</p>"
        body += _details("Round " + str(item["round"]) + " · " + _text(item["kind"]), detail)
    return body


def render_comparison(before: SavedReport, after: SavedReport) -> str:
    """Render admitted immutable reports without running or normalizing their inputs."""
    result = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
              "<title>Compare saved TestPilot runs</title><style>" + _STYLE + "</style></head><body>",
              '<a class="skip" href="#results">Skip to recorded results</a><main class="shell">',
              '<p class="eyebrow">TestPilot / Saved results</p><h1>Compare saved runs.</h1>',
              '<p class="lead">Review the recorded outcomes, selected source, and generated-test changes in two saved reports.</p>',
              '<p class="note">Before and After are the labels supplied to this comparison. The inputs do not establish chronology or measured improvement.</p>',
              '<div class="columns" aria-label="Selected reports">']
    for role, report in (("Before", before), ("After", after)):
        result.append('<div class="panel"><p class="role">' + role + '</p><span class="outcome">'
                      + _text(_LABELS[report.data["status"]]) + '</span><p class="meta">Recorded status: '
                      + _text(report.data["status"]) + '</p><p class="meta">' + _text(report.name)
                      + " · " + str(len(report.raw)) + " bytes</p></div>")
    result.append('</div><div class="context"><strong>' + _text(context_relation(before, after))
                  + '</strong><span class="note">Inspect the selected-source records before comparing the result figures.</span></div>')
    result.append('<nav aria-label="Report sections">' + "".join('<a href="#' + key + '">' + label + "</a>" for key, label in [
        ("results", "Results"), ("source", "Selected source"), ("files", "Generated files"),
        ("diagnostics", "Diagnostics"), ("coverage", "Coverage"), ("usage", "Usage"),
        ("rounds", "Rounds"), ("originals", "Original reports")]) + "</nav>")
    rows = [
        ["Recorded status", before.data["status"], after.data["status"]],
        ["Selected targets", len(before.data["changed_functions"]), len(after.data["changed_functions"])],
        ["Retained generated files", len(before.data["test_files"]), len(after.data["test_files"])],
        ["Tests written (reported)", before.data["tests_written"], after.data["tests_written"]],
        ["Repair rounds used / allowed", str(before.data["repair_rounds_used"]) + " / " + str(before.data["max_repair_rounds"]),
         str(after.data["repair_rounds_used"]) + " / " + str(after.data["max_repair_rounds"])],
        ["JUnit availability", _junit(before), _junit(after)],
        ["Complete-suite recorded counts", _suite_counts(before), _suite_counts(after)],
        ["Generated-case recorded counts", _generated_counts(before), _generated_counts(after)],
    ]
    result.append('<section id="results" tabindex="-1"><h2>Recorded results</h2>'
                  + _table(["Field", "Before", "After"], rows, "Values retained from each saved run")
                  + '<p class="note">Tests written can count authored definitions when execution evidence is unavailable. A recorded pass or model diagnosis retains its original meaning; this view adds no test execution or correctness finding.</p></section>')
    result.append('<section id="source"><h2>Selected-source context</h2>' + _targets(before, after) + "</section>")
    result.append('<section id="files"><h2>Generated-file changes</h2>' + _files(before, after) + "</section>")
    result.append('<section id="diagnostics"><h2>Final diagnostics</h2><div class="columns"><div>'
                  + _diagnostics(before, "Before") + "</div><div>" + _diagnostics(after, "After") + "</div></div></section>")
    result.append('<section id="coverage"><h2>Recorded coverage</h2>'
                  + '<p class="note">Each column retains its own source and selection denominators. The reported change is within that original run.</p>'
                  + _table(["Measurement", "Before report", "After report"], _coverage_rows(before, after), "Original within-run measurements") + "</section>")
    usage_rows = [
        ["Recorded total tokens", before.data["ledger"]["total_tokens"], after.data["ledger"]["total_tokens"]],
        ["Token basis", "Includes estimates" if before.data["ledger"]["tokens_estimated"] else "Provider-reported",
         "Includes estimates" if after.data["ledger"]["tokens_estimated"] else "Provider-reported"],
        ["Recorded total cost", _cost(before), _cost(after)],
    ]
    result.append('<section id="usage"><h2>Recorded usage</h2>'
                  + _table(["Field", "Before", "After"], usage_rows, "Original totals and completeness flags")
                  + '<p class="note">Prices and currency amounts retain the original run’s configuration. Incomplete cost stays unpriced.</p><div class="columns"><div>'
                  + _usage(before, "Before") + "</div><div>" + _usage(after, "After") + "</div></div></section>")
    result.append('<section id="rounds"><h2>Saved generation and repair rounds</h2><div class="columns"><div>'
                  + _rounds(before, "Before") + "</div><div>" + _rounds(after, "After") + "</div></div></section>")
    originals = [[role, report.name, len(report.raw), report.sha256] for role, report in (("Before", before), ("After", after))]
    result.append('<section id="originals"><h2>Original reports</h2>'
                  + _table(["Label", "Source filename", "Bytes", "SHA256"], originals, "Exact input byte identities")
                  + '<div class="actions">')
    for role, report in (("before", before), ("after", after)):
        encoded = base64.b64encode(report.raw).decode("ascii")
        result.append('<a class="button" id="download-' + role + '" download="' + role
                      + '-report.json" href="data:application/json;base64,' + encoded + '">Download '
                      + role + " JSON</a>")
    result.append('</div><p class="note">The downloads keep the complete original input bytes, including extra fields and formatting.</p></section>'
                  + '<footer>Open this file offline or use your browser’s Print command. Control, separator and surrogate characters appear with visible escapes; original downloads are unchanged. No report content is executed.</footer></main></body></html>')
    return "\n".join(result)
