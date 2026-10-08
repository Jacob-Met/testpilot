"""Recompute the frozen receiving evidence using only the Python standard library.

This validates captured source, actual CLI outputs, browser DOM tables/downloads,
negative controls and custody. It does not rerun TestPilot, browsers or providers.
"""
from __future__ import annotations
import argparse
import ast
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

BASE = "d7c28b0ad261e78d681f40e355447dffa4d435ed"
HEAD = "fe791af1a0908b2379dd7cbb87a9fb8f3cad87de"
CONTROL_PINS = {
    "prepare_inputs.py": "ef4d5e61c5471a164eecb91a44f965ddb6d94f85a37b570184285a33ff45d366",
    "prepare_inputs_v2.py": "e7b71e524efeaac61bf20b3fe3c2032495c4ed3131298f59145ef1d20758d8be",
    "run_cli.py": "f23d84c0257222c89ee88f28b240f21b29f212a50e8bf6c994f07053e8120c42",
    "replay_original_writer.py": "26c6399bc48269394433420aa2e32730f881085f37984747123af4cc4bdf1991",
    "receive_html.mjs": "0ab5635f2b5fcfc76836f4abba7c689b65f0438864031797898c788a0e9dd7e1",
}
SOURCE_PINS = {
    "testpilot/html_report.py": "183703d05f32552f7f7c39aa958c39bae61d824e3fa9cd6a6dd686f0d4c228a4",
    "testpilot/loop.py": "bf19e45239e7301f3b7b1a07ecfb1b80224ac60158c7134190de252b54ac4559",
}
def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def digest(path):
    b = path.read_bytes()
    return {"bytes": len(b), "sha256": sha(b)}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def failed(cases):
    return {x["name"]: [k for k, value in x["checks"].items() if not value] for x in cases}

def visible(value):
    return "—" if value is None else str(value)

class Downloads(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.downloads = {}
        self.h1 = 0
        self.headers = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "header":
            self.headers += 1
        if tag == "a" and attrs.get("download"):
            name = attrs["download"]
            require(name not in self.downloads, "Duplicate download name")
            href = attrs["href"]
            require(href.startswith("data:") and ";base64," in href, "Download is not embedded")
            self.downloads[name] = base64.b64decode(href.split(";base64,", 1)[1], validate=True)

def tables_from_report(data):
    tables = []
    runs = ([data["final"]] if data["final"] else []) + [
        r["result"] for r in data["rounds"] if r["result"] is not None]
    for result in runs:
        tables.append([["Passed", "Failed", "Errors", "Skipped"],
                       [visible(result[k]) for k in ("passed", "failed", "errors", "skipped")]])
        generated = result.get("generated")
        if generated is not None:
            tables.append([["Collected", "Passed", "Failed", "Errors", "Skipped"],
                           [visible(generated[k]) for k in ("collected", "passed", "failed", "error", "skipped")]])
    coverage = data["coverage"]
    if coverage is not None:
        tables.append([["Measurement", "Before", "After"],
                       ["Total coverage (%)", visible(coverage["total_before"]), visible(coverage["total_after"])],
                       ["Changed executable lines (%)", visible(coverage["changed_lines_before"]),
                        visible(coverage["changed_lines_after"])]])
    entries = data["ledger"]["entries"]
    if entries:
        tables.append([["Call", "Role", "Model", "Prompt tokens", "Completion tokens", "Token source", "Recorded cost (USD)"]] + [
            [str(i + 1), e["role"], e["model"], str(e["prompt_tokens"]), str(e["completion_tokens"]),
             "estimated" if e["estimated"] else "reported", str(e["cost_usd"])]
            for i, e in enumerate(entries)])
    return tables

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?", default=Path(__file__).resolve().parent)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    final = root / "final"
    if (root / "receipt.json").exists():
        receipt = read(root / "receipt.json")
        for row in receipt["files"]:
            require(digest(root / row["path"]) == {k: row[k] for k in ("bytes", "sha256")},
                    "Frozen receipt mismatch: " + row["path"])
    for name, pin in CONTROL_PINS.items():
        require(sha((root / name).read_bytes()) == pin, "Receiver source changed: " + name)
    freeze = read(final / "controls-freeze.json")
    require(freeze["candidate_source_inspected"] is False, "Pre-candidate control boundary missing")
    for row in freeze["files"]:
        require(digest(root / row["name"]) == {k: row[k] for k in ("bytes", "sha256")},
                "Control freeze mismatch")

    manifests = {}
    maps = {}
    canonical = read(root / "canonical-tree.json")
    require(canonical["truncated"] is False, "Canonical tree was truncated")
    leaves = {x["path"]: x for x in canonical["tree"] if x["type"] == "blob"}
    for phase in ("baseline", "candidate"):
        manifest = read(root / (phase + "-source-manifest.json"))
        manifests[phase] = manifest
        maps[phase] = {x["path"]: {**x, "bytes": x.get("bytes", x.get("size")),
                                         "git_blob": x.get("git_blob", x.get("sha"))}
                       for x in manifest["files"]}
        for rel, row in maps[phase].items():
            b = (root / phase / rel).read_bytes()
            require(digest(root / phase / rel) == {k: row[k] for k in ("bytes", "sha256")},
                    "Source content mismatch: " + phase + "/" + rel)
            git = hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
            require(git == row["git_blob"], "Git object mismatch: " + rel)
            if phase == "baseline":
                leaf = leaves[rel]
                require((leaf["sha"], leaf["size"], leaf["mode"]) == (git, len(b), row["mode"]),
                        "Canonical baseline leaf mismatch: " + rel)
    candidate = manifests["candidate"]
    require(candidate["canonical_base"] == BASE and candidate["local_projection_head"] == HEAD,
            "Wrong reviewed source identity")
    for rel, pin in SOURCE_PINS.items():
        require(maps["candidate"][rel]["sha256"] == pin, "Wrong executable freeze")
    old, new = maps["baseline"], maps["candidate"]
    changed = [p for p in old if old[p]["sha256"] != new[p]["sha256"]]
    added = sorted(set(new) - set(old))
    require(set(old) <= set(new) and sorted(changed + added) == sorted(candidate["scope_paths"]),
            "Unexpected source scope")
    def definitions(phase):
        module = ast.parse((root / phase / "testpilot/loop.py").read_text())
        return {n.name: ast.dump(n, include_attributes=False) for n in module.body
                if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    a, b = definitions("baseline"), definitions("candidate")
    require(set(a) == set(b), "Loop definitions changed")
    require([n for n in a if a[n] != b[n]] == ["write_outputs"], "Behavior changed outside writer")

    for base in (root, final):
        inputs = read(base / "inputs-manifest.json")
        for row in inputs["files"]:
            require(digest(base / row["path"]) == {k: row[k] for k in ("bytes", "sha256")},
                    "Authored input changed: " + row["path"])
    specs = read(final / "inputs-manifest.json")["cases"]
    names = [s["name"] for s in specs]
    initial = read(root / "baseline-cli/summary.json")
    expected_initial = {name: ["actual_html_emitted"] for name in names}
    expected_initial["timeout_tail"] = ["stored_output_is_tail", "actual_html_emitted"]
    require(failed(initial["cases"]) == expected_initial, "Original fixture failure history changed")
    baseline = read(final / "baseline-cli/summary.json")
    baseline_browser = read(final / "baseline-cli-browser/summary.json")
    require(failed(baseline["cases"]) == {n: ["actual_html_emitted"] for n in names},
            "Corrected baseline has another failure")
    require(failed(baseline_browser["cases"]) == {n: ["actual_html_emitted"] for n in names},
            "Baseline browser negative is not missing HTML")
    cli = read(final / "candidate-cli/summary.json")
    browser = read(final / "candidate-cli-browser/summary.json")
    require(cli["case_count"] == browser["case_count"] == 7, "Wrong actual case count")
    require(cli["case_passed"] == browser["case_passed"] == 7 and
            failed(cli["cases"]) == failed(browser["cases"]) == {n: [] for n in names},
            "Candidate receiving contains a failed check")
    require(browser["driver_sha256"] == CONTROL_PINS["receive_html.mjs"], "Browser used another driver")
    for phase, source in (("baseline-cli", "baseline"), ("candidate-cli", "candidate")):
        require(read(final / phase / "source-before.json") == read(final / phase / "source-after.json"),
                "Source changed during actual CLI")
        expected = [{"path": p, "bytes": x["bytes"], "sha256": x["sha256"]}
                    for p, x in sorted(maps[source].items())]
        require(read(final / phase / "source-before.json") == expected, "CLI source snapshot does not match freeze")

    cli_by_name = {x["name"]: x for x in cli["cases"]}
    browser_by_name = {x["name"]: x for x in browser["cases"]}
    original_count = download_count = table_count = table_cells = case_records = 0
    results = []
    for spec in specs:
        name = spec["name"]
        capture = final / "candidate-cli" / name
        view = final / "candidate-cli-browser" / name
        data = read(capture / "report.json")
        event = cli_by_name[name]
        require(event["pid"] > 0 and event["exit_code"] == spec["expected_exit"], "Wrong actual CLI exit")
        require(data["status"] == spec["expected_status"] and data["ok"] == (data["status"] == "passed"),
                "Actual status disagrees with expected case")
        require(data["repair_rounds_used"] == spec["expected_repairs"] and len(data["rounds"]) == spec["expected_rounds"],
                "Actual repair history disagrees")
        if "expected_generated" in spec:
            require(data["final"]["generated"] == spec["expected_generated"], "Generated counts disagree")
        if spec.get("expected_final_none"):
            require(data["final"] is None, "Missing final result was invented")
        if spec.get("expected_output_tail"):
            result = data["final"]
            require(result["timed_out"] and result["returncode"] is None and result["junit_available"] is False,
                    "Timeout/unknown boundary changed")
            require(result["coverage"] is None and data["coverage"] is None, "Timeout coverage invented")
            require(len(result["output"]) == 3000 and "RETAINED-TAIL-雪" in result["output"] and
                    "NOT-IN-RETAINED-OUTPUT-" not in result["output"], "Real output is not the bounded tail")
        if spec.get("expected_collision"):
            p = spec["expected_collision"]
            require(p in data["test_files"] and data["rounds"][0]["contents"][p] != data["rounds"][1]["contents"][p],
                    "Partial repair history lost")
            require(data["rounds"][0]["contents"]["tests/test_retained.py"] ==
                    data["rounds"][1]["contents"]["tests/test_retained.py"], "Retained file changed")
        for filename in ("report.json", "report.md", "testpilot.patch"):
            require(digest(capture / filename) == event["files"][filename], "Actual CLI file hash differs")
            require((capture / filename).read_bytes() == (final / "original-writer" / name / filename).read_bytes(),
                    "Original writer bytes differ")
            original_count += 1
        replay = read(final / "original-writer" / name / "writer-verification.json")
        require(all(x["equal"] for x in replay["files"]), "Original writer replay failed")

        html = (capture / "report.html").read_bytes()
        require(digest(capture / "report.html") == event["html"], "Actual HTML hash differs")
        require((view / "report.html").read_bytes() == html, "Detached HTML changed")
        parsed = Downloads()
        parsed.feed(html.decode("utf-8"))
        require(parsed.h1 == parsed.headers == 1, "Unexpected duplicate document header")
        require(set(parsed.downloads) == {"report.json", "testpilot.patch"}, "Unexpected embedded downloads")
        for filename in ("report.json", "testpilot.patch"):
            expected = (capture / filename).read_bytes()
            require(parsed.downloads[filename] == expected, "Embedded download bytes differ")
            require((view / ("download-" + filename)).read_bytes() == expected, "Actual browser download differs")
            download_count += 1
        require((view / "javascript-disabled-report.json").read_bytes() == (capture / "report.json").read_bytes(),
                "JavaScript-disabled download differs")
        download_count += 1
        dom = read(view / "dom.json")
        expected_tables = tables_from_report(data)
        require(dom["tables"] == expected_tables, "Actual DOM counts/coverage/ledger differ: " + name)
        table_count += len(expected_tables)
        table_cells += sum(len(row) for table in expected_tables for row in table[1:])
        runs = ([data["final"]] if data["final"] else []) + [
            r["result"] for r in data["rounds"] if r["result"] is not None]
        for result in runs:
            for case in result["cases"]:
                require(case["nodeid"] in dom["text"], "A recorded case identity is absent")
                if case.get("message"):
                    require(any(case["message"].rstrip() in p for p in dom["pres"]), "A diagnostic is absent")
                case_records += 1
        require(data["ledger"]["total_tokens"] == sum(e["prompt_tokens"] + e["completion_tokens"]
                                                    for e in data["ledger"]["entries"]), "Ledger total disagrees")
        require(all(e["estimated"] for e in data["ledger"]["entries"]), "Fixture model token source changed")
        row = browser_by_name[name]
        require(row["requests"] == row["errors"] == [] and row["mobile"]["scrollWidth"] <= 376,
                "Actual browser network/error/viewport boundary failed")
        results.append({"name": name, "status": data["status"], "exit_code": event["exit_code"],
                        "html_sha256": sha(html), "tables": len(expected_tables),
                        "browser_checks": len(row["checks"])})
    require(browser["checks"] == sum(len(x["checks"]) for x in browser["cases"]) == 219,
            "Browser check count disagrees")

    negative = final / "negative-controls"
    neg = read(negative / "negative-cli-browser/summary.json")
    expected_negative = {"passed_unicode": ["exact_download_report.json", "javascript_disabled_exact_download"],
                         "timeout_tail": ["output_tail_qualified"]}
    require(failed(neg["cases"]) == expected_negative, "Consequential negative controls were not caught")
    require(neg["driver_sha256"] == CONTROL_PINS["receive_html.mjs"] and
            read(negative / "execution.json")["exit_code"] == 1, "Negative controls used another receiver")
    for mutation in read(negative / "mutations.json"):
        name = mutation["case"]
        require(sha((final / "candidate-cli" / name / "report.html").read_bytes()) == mutation["source_sha256"],
                "Negative control original changed")
        require(sha((negative / "negative-cli" / name / "report.html").read_bytes()) == mutation["mutant_sha256"],
                "Negative control mutant changed")
    visuals = read(final / "visual-supplement/summary.json")
    require(len(visuals["rows"]) == 3 and all(x["metrics"]["headers"] == x["metrics"]["h1"] == 1 and
            x["metrics"]["scrollWidth"] == 375 and not x["requests"] for x in visuals["rows"]),
            "Fresh mobile document boundary failed")
    require(visuals["rows"][0]["ledger"]["scrollAfterKey"] > 0, "Keyboard did not scroll the table")
    pdf = final / "candidate-cli-browser/repaired_partial/print.pdf"
    require(pdf.read_bytes().startswith(b"%PDF-") and pdf.stat().st_size > 1000, "Print artifact missing")
    result = {
        "schema": "testpilot-html-independent-recomputed-v1",
        "baseline_commit": BASE, "candidate_projection": HEAD,
        "canonical_leaves": len(leaves), "baseline_source_files": len(old), "candidate_source_files": len(new),
        "inherited_source_files_exact": len(old) - len(changed),
        "changed_paths": changed, "added_paths": added,
        "unchanged_loop_top_level_definitions": len(a) - 1,
        "corrected_baseline_cases_missing_html": 7,
        "original_fixture_failure_retained": "timeout output remained captured because sandbox resets addopts",
        "actual_cli_cases_passed": 7, "actual_cli_checks": sum(len(x["checks"]) for x in cli["cases"]),
        "original_writer_artifacts_byte_equal": original_count,
        "actual_browser_cases_passed": 7, "actual_browser_checks": 219,
        "actual_browser_downloads_byte_equal": download_count,
        "actual_dom_tables_equal": table_count, "actual_dom_data_cells_equal": table_cells,
        "recorded_case_identities_and_diagnostics_present": case_records,
        "negative_controls_rejected_exactly": expected_negative,
        "fresh_375px_document_cases": 3, "native_table_keyboard_scroll": True,
        "print_pdf": digest(pdf), "browser": browser["browser"], "node": browser["node"],
        "python": cli["python"], "pytest": cli["pytest"], "coverage": cli["coverage"],
        "cases": results,
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

if __name__ == "__main__":
    main()
