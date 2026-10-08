"""Verify the frozen author packet without executing TestPilot, fixtures or a browser."""
from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(condition, label):
    if not condition:
        raise ValueError(label)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Downloads(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and "download" in attributes:
            name = attributes["download"]
            require(name not in self.values, "duplicate download")
            href = attributes["href"]
            require(href.startswith("data:") and ";base64," in href, "embedded download")
            self.values[name] = base64.b64decode(href.split(",", 1)[1], validate=True)


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
    receipt = json.loads((root / "author-receipt.json").read_bytes())
    archive_bytes = (root / "author-native.tar.xz").read_bytes()
    require(len(archive_bytes) == receipt["archive"]["bytes"], "archive byte count")
    require(digest(archive_bytes) == receipt["archive"]["sha256"], "archive digest")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:xz") as archive:
        members = archive.getmembers()
        require(len(members) == receipt["archive"]["ordinary_members"], "member count")
        require(all(m.isfile() and not PurePosixPath(m.name).is_absolute()
                    and ".." not in PurePosixPath(m.name).parts for m in members), "ordinary relative members")
        require(len({m.name for m in members}) == len(members), "unique members")
        data = {m.name: archive.extractfile(m).read() for m in members}
    raw_manifest = data["native-manifest.json"]
    require(digest(raw_manifest) == receipt["native_manifest"]["sha256"], "native manifest digest")
    require(raw_manifest == (root / "author-native-manifest.json").read_bytes(), "exposed manifest")
    native = json.loads(raw_manifest)
    require(len(native["artifacts"]) == native["artifact_count"] == 836, "native artifact count")
    require(set(data) == {r["path"] for r in native["artifacts"]} | {"native-manifest.json"}, "manifest covers exact archive")
    for row in native["artifacts"]:
        require(len(data[row["path"]]) == row["bytes"] and digest(data[row["path"]]) == row["sha256"], row["path"])

    def read_json(path):
        return json.loads(data[path])

    source_sets = {}
    for filename, prefix, count, size_key, blob_key in [
        ("baseline-source-manifest.json", "baseline", 73, "size", "sha"),
        ("candidate-source-manifest.json", "source", 77, "bytes", "git_blob"),
        ("current-source-manifest.json", "current-source", 79, "bytes", "git_blob"),
    ]:
        manifest = read_json(filename)
        require(len(manifest["files"]) == count, prefix + " source count")
        values = {}
        for row in manifest["files"]:
            raw = data[prefix + "/" + row["path"]]
            require(len(raw) == row[size_key] and digest(raw) == row["sha256"] and blob(raw) == row[blob_key], prefix + "/" + row["path"])
            values[row["path"]] = {"bytes": len(raw), "sha256": digest(raw)}
        source_sets[prefix] = values

    frozen = read_json("candidate-source-manifest.json")
    current = read_json("current-source-manifest.json")
    current_tree = read_json("current-tree.json")
    require(current_tree["sha"] == current["current_tree"] and not current_tree["truncated"], "complete current tree")
    leaves = {r["path"]: r for r in current_tree["tree"] if r["type"] == "blob"}
    require(len(leaves) == 430, "current tree leaves")
    scope = set(frozen["scope_paths"])
    require(len(scope) == 6 and scope == set(current["scope_paths"]), "six-file scope")
    for path in scope:
        require(data["source/" + path] == data["current-source/" + path], "frozen scoped source " + path)
    for path in source_sets["current-source"]:
        if path not in scope:
            require(blob(data["current-source/" + path]) == leaves[path]["sha"], "current unowned source " + path)
    loop = data["source/testpilot/loop.py"].decode()
    loop = loop.replace("from .html_report import render_html_report\n", "", 1)
    loop = loop.replace(', "md": out / "report.md",\n             "html": out / "report.html"}', ', "md": out / "report.md"}', 1)
    loop = loop.replace('    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n', "", 1)
    require(loop.encode() == data["baseline/testpilot/loop.py"], "exactly additive output integration")

    outcomes = {"passed": "passed", "repair": "passed", "failed": "failed", "suspected": "suspected_code_bug",
                "no_tests": "no_tests", "no_changes": "no_changes", "budget": "budget_exhausted",
                "model_error": "model_error", "timeout": "failed"}
    cli_results = {}
    for folder, source, count, html, driver in [
        ("baseline-cli-v2", "baseline", 9, False, "capture_runs-v2.py"),
        ("candidate-cli-v2", None, 9, True, "capture_runs-v2.py"),
        ("candidate-cli-final", "source", 9, True, "capture_runs-v2.py"),
        ("current-cli", "current-source", 9, True, "capture_runs-v2.py"),
        ("literal-cli", "source", 1, True, "capture_literal.py"),
    ]:
        prefix = "evidence/" + folder
        report = read_json(prefix + "/report.json")
        require(report["passed"] == len(report["cases"]) == count, folder + " completed cases")
        require(report["source_before"] == report["source_after"], folder + " stable source")
        if source:
            require(report["source_before"] == source_sets[source], folder + " exact source closure")
        else:
            require(report["source_before"]["testpilot/html_report.py"]["sha256"] == digest(data["evidence/html_report-before-phone.py"]), "pre-phone source")
        require(report["driver_sha256"] == digest(data[driver]), folder + " driver")
        require(report["expect_html"] is html, folder + " HTML expectation")
        require([c["name"] for c in report["cases"]] == (list(outcomes) if count == 9 else ["passed"]), folder + " fixed cohort")
        for case in report["cases"]:
            path = prefix + "/" + case["name"]
            require(case["status"] == outcomes[case["name"]], path + " status")
            require(case["exit_code"] == (0 if case["status"] == "passed" else 1), path + " CLI exit")
            result = read_json(path + "/out/report.json")
            for key in ["status", "final", "tests_written", "repair_rounds_used"]:
                require(case[key] == result[key], path + " captured result " + key)
            for name, metadata in case["artifacts"].items():
                raw = data[path + "/out/" + name]
                require(len(raw) == metadata["bytes"] and digest(raw) == metadata["sha256"], path + " artifact " + name)
            for name, metadata in case["inputs"].items():
                raw = data[path + "/repo/" + name]
                require(len(raw) == metadata["bytes"] and digest(raw) == metadata["sha256"], path + " input " + name)
            if result["patch"]:
                require(case["git_apply_check"]["exit_code"] == 0, path + " applicable patch")
            if html:
                parser = Downloads(); parser.feed(data[path + "/out/report.html"].decode())
                require(set(parser.values) == {"report.json", "testpilot.patch"}, path + " download set")
                for name, raw in parser.values.items():
                    require(raw == data[path + "/out/" + name], path + " exact embedded " + name)
            else:
                require(path + "/out/report.html" not in data, path + " baseline has no HTML")
        cli_results[folder] = count

    browsers = {}
    for folder, capture, count, driver in [
        ("browser-v1", "candidate-cli-v2", 132, "check_browser.mjs"),
        ("browser-final", "candidate-cli-final", 133, "check_browser-v2.mjs"),
        ("current-browser", "current-cli", 133, "check_browser-v2.mjs"),
    ]:
        prefix = "evidence/" + folder
        report = read_json(prefix + "/report.json")
        require(report["captureReportSha256"] == digest(data["evidence/" + capture + "/report.json"]), folder + " capture binding")
        require(report["driverSha256"] == digest(data[driver]), folder + " driver binding")
        require(report["passed"] == len(report["checks"]) == count and not report.get("failure"), folder + " completed checks")
        require(report["requests"] == report["applicationErrors"] == report["consoleErrors"] == [], folder + " error/request observations")
        for check in report["checks"]:
            require(check["passed"] is True and canonical(check["actual"]) == canonical(check["expected"]), folder + ": " + check["label"])
        for name in outcomes:
            require(data[prefix + "/isolated-pages/" + name + ".html"] == data["evidence/" + capture + "/" + name + "/out/report.html"], folder + " detached " + name)
            for filename in ["report.json", "testpilot.patch"]:
                require(data[prefix + "/" + name + "-" + filename] == data["evidence/" + capture + "/" + name + "/out/" + filename], folder + " actual download " + name + "/" + filename)
        require(data[prefix + "/repair-print.pdf"].startswith(b"%PDF"), folder + " actual PDF")
        browsers[folder] = count
    literal = read_json("evidence/literal-browser/report.json.receipt")
    require(literal["passed"] == len(literal["checks"]) == 9 and literal["requests"] == literal["errors"] == [], "literal browser")
    for check in literal["checks"]:
        require(check["passed"] is True and canonical(check["actual"]) == canonical(check["expected"]), check["label"])
    for name in ["report.json", "testpilot.patch"]:
        require(data["evidence/literal-browser/" + name] == data["evidence/literal-cli/passed/out/" + name], "literal actual download " + name)
    require(literal["htmlSha256"] == digest(data["evidence/literal-browser/record.html"]) and literal["reportSha256"] == digest(data["evidence/literal-browser/report.json"]), "literal source binding")

    require(b"5 failed, 191 passed" in data["evidence/full-suite.log"], "initial complete suite result")
    require(b"5 failed" in data["evidence/baseline-five.log"] and read_json("evidence/baseline-five-command.json")["exit_code"] == 1, "unchanged baseline failures")
    require(b"19 passed" in data["evidence/html-tests-final.log"], "final focused tests")
    require(all(c["exit_code"] == 0 for c in read_json("evidence/final-commands.json")), "final command exits")
    require(all(c["exit_code"] == 0 for c in read_json("evidence/current-composition-commands.json")), "current command exits")
    initial = read_json("evidence/baseline-cli/report.json")
    require(len(initial["cases"]) == 5 and "passed" not in initial and b"FileNotFoundError" in data["evidence/baseline-cli.log"], "original observer failure retained")
    return {"schema": "testpilot.html_report.author_verification.v1", "archive_sha256": digest(archive_bytes),
            "native_manifest_sha256": digest(raw_manifest), "ordinary_members": len(data), "artifacts_verified": 836,
            "source_files": {k: len(v) for k, v in source_sets.items()}, "frozen_scoped_files_unchanged": 6,
            "current_unowned_source_blobs_verified": 73, "current_base": current["current_base"], "current_tree": current["current_tree"],
            "cli_cases": cli_results, "browser_checks": browsers, "literal_browser_checks": 9,
            "initial_complete_suite": {"passed": 191, "failed": 5}, "baseline_reproduced_failures": 5,
            "final_focused_tests": 19, "existing_output_integration": "Only HTML import/key/write added; independent original-writer byte replay is in the separate receiving packet.",
            "verification_execution": "Reads saved artifacts only; does not replay native TestPilot or browser execution."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False) + "\n", end="")
