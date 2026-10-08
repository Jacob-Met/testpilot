"""Verify saved PR20 allocator/HTML composition evidence without replaying product code."""
from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.downloads = {}
        self.text = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and "download" in attrs:
            name = attrs["download"]
            require(name not in self.downloads, "duplicate download")
            require(attrs["href"].startswith("data:") and ";base64," in attrs["href"], "embedded download")
            self.downloads[name] = base64.b64decode(attrs["href"].split(",", 1)[1], validate=True)

    def handle_data(self, text):
        self.text.append(text)


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
    archive_bytes = (root / "pr20-native.tar.xz").read_bytes()
    require(len(archive_bytes) == 1077732 and sha(archive_bytes) == "8f480e0b9edb7bfa29c4e75bbcf8f5298e9d735fdc3ca0a65205dd6b3bb0670a", "native archive")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:xz") as archive:
        members = archive.getmembers()
        require(len(members) == len({m.name for m in members}) == 134, "134 unique members")
        require(all(m.isfile() and not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members), "ordinary relative members")
        data = {m.name: archive.extractfile(m).read() for m in members}
    raw_manifest = data["native-manifest.json"]
    require(sha(raw_manifest) == "09e516e12f09ff72bbe8dbbaee3fbcd7e1041a9e9bc9acd640ae8c313b79f334", "native manifest")
    require(raw_manifest == (root / "native-manifest.json").read_bytes(), "exposed native manifest")
    native = json.loads(raw_manifest)
    require(len(native["artifacts"]) == native["artifact_count"] == 133, "133 artifact records")
    require(set(data) == {r["path"] for r in native["artifacts"]} | {"native-manifest.json"}, "complete artifact manifest")
    for row in native["artifacts"]:
        require(len(data[row["path"]]) == row["bytes"] and sha(data[row["path"]]) == row["sha256"], row["path"])
    manifest = json.loads(data["source-manifest.json"])
    require(data["source-manifest.json"] == (root / "source-manifest.json").read_bytes(), "exposed source manifest")
    require(sha(data["source-manifest.json"]) == "510f4dc179c71970444e4e97389272b763b1ce3b1f6229d86e13c6a08769b29a", "frozen source manifest")
    require(manifest["base"] == "269e55332a9bb78a0a0e107cbab6b2e5c895ca57" and manifest["tree"] == "2045a73704f752d374704657fccf90fd5e774258", "canonical parent")
    tree = json.loads(data["current-tree-blobs.json"])
    require(tree["sha"] == manifest["tree"] and tree["truncated"] is False, "complete current tree")
    leaves = {r["path"]: r for r in tree["tree"]}
    require(len(leaves) == 432 and len(manifest["files"]) == 80, "current closure size")
    source = {}
    for row in manifest["files"]:
        raw = data["source/" + row["path"]]
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"] and blob(raw) == row["git_blob"], row["path"])
        source[row["path"]] = {"bytes": len(raw), "sha256": sha(raw)}
        if row["path"] not in manifest["scope_paths"]:
            require(blob(raw) == leaves[row["path"]]["sha"], "current unowned source " + row["path"])
    for path in ["README.md", "testpilot/loop.py"]:
        require(blob(data["upstream/" + path]) == leaves[path]["sha"], "canonical upstream " + path)
    old_paths = '    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md"}\n'
    new_paths = '    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",\n             "html": out / "report.html"}\n'
    extra = '    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n'
    loop = data["source/testpilot/loop.py"].decode()
    require(loop.replace("from .html_report import render_html_report\n", "", 1).replace(new_paths, old_paths, 1).replace(extra, "", 1).encode() == data["upstream/testpilot/loop.py"], "only accepted loop additions")
    readme = data["source/README.md"].decode()
    section = "## Review your own run in a browser\n" + readme.split("## Review your own run in a browser\n", 1)[1].split("## Running on Nebius Token Factory", 1)[0]
    require(readme.replace(section, "", 1).encode() == data["upstream/README.md"], "only accepted README section")
    original_archive = root.parent / "author" / "author-native.tar.xz"
    with tarfile.open(original_archive, mode="r:xz") as original:
        original_readme = original.extractfile("source/README.md").read().decode()
        original_baseline = original.extractfile("baseline/README.md").read().decode()
        require(original_readme.replace(section, "", 1) == original_baseline, "README section is unchanged from original freeze")
        for path in manifest["unchanged_frozen_files"]:
            require(data["source/" + path] == original.extractfile("source/" + path).read(), "unchanged frozen file " + path)

    cli = json.loads(data["cli/report.json"])
    require(cli["passed"] == len(cli["cases"]) == 2 and [c["name"] for c in cli["cases"]] == ["passed", "repair"], "two fixed CLI cases")
    require(cli["source_before"] == cli["source_after"] == source, "stable exact source")
    require(cli["driver_sha256"] == sha(data["capture_allocator_compatibility.py"]), "CLI driver identity")
    expected_files = ["tests/unit/test_calc_testpilot.py", "tests/integration/test_calc_testpilot_2.py"]
    for case in cli["cases"]:
        prefix = "cli/" + case["name"]
        result = json.loads(data[prefix + "/out/report.json"])
        require(case["exit_code"] == 0 and result["status"] == "passed", prefix + " passed")
        require(list(result["test_files"]) == expected_files, prefix + " resolved filenames")
        require(result["final"]["junit_available"] is True and result["final"]["passed"] == 3, prefix + " actual pytest result")
        require(result["final"]["failed"] == result["final"]["errors"] == 0, prefix + " no failed tests")
        require(result["final"]["generated"]["collected"] == result["final"]["generated"]["passed"] == result["tests_written"] == 2, prefix + " two generated tests")
        require(result["repair_rounds_used"] == (case["name"] == "repair"), prefix + " repair count")
        require(len(result["rounds"]) == (2 if case["name"] == "repair" else 1), prefix + " round count")
        require(case["git_apply_check"]["exit_code"] == 0, prefix + " applicable patch")
        for name, row in case["artifacts"].items():
            raw = data[prefix + "/out/" + name]
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], prefix + "/" + name)
        for path, row in case["inputs"].items():
            raw = data[prefix + "/repo/" + path]
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], prefix + " input " + path)
        document = Document(); document.feed(data[prefix + "/out/report.html"].decode())
        require(set(document.downloads) == {"report.json", "testpilot.patch"}, prefix + " downloads")
        for name, raw in document.downloads.items():
            require(raw == data[prefix + "/out/" + name], prefix + " exact embedded " + name)
        text = "".join(document.text)
        for warning in result["rounds"][0]["warnings"]:
            require(warning in text, prefix + " literal rename warning")
        require(("assert double(operand) == 7" in text) == (case["name"] == "repair"), prefix + " retained failing source")
        for content in result["test_files"].values():
            require(content in text, prefix + " literal final source")
        if case["name"] == "repair":
            require(result["rounds"][0]["result"]["failed"] == 1 and result["rounds"][0]["result"]["passed"] == 2, "retained initial pytest result")
            require("== 7" in result["rounds"][0]["contents"][expected_files[0]] and "== 6" in result["test_files"][expected_files[0]], "partial alias repair history")
    browser = json.loads(data["browser/report.json"])
    require(browser["captureReportSha256"] == sha(data["cli/report.json"]), "browser capture identity")
    require(browser["driverSha256"] == sha(data["check_browser.mjs"]) == "1827644fff1d252e71f4302baaef88e4cf9a00d1aea8ce3ff38533fd7f75d98f", "unchanged browser driver")
    require(browser["passed"] == len(browser["checks"]) == 39 and not browser.get("failure"), "39 browser checks")
    require(browser["requests"] == browser["applicationErrors"] == browser["consoleErrors"] == [], "browser observations")
    for check in browser["checks"]:
        require(check["passed"] is True and canonical(check["actual"]) == canonical(check["expected"]), check["label"])
    for name in ["passed", "repair"]:
        require(data["browser/isolated-pages/" + name + ".html"] == data["cli/" + name + "/out/report.html"], "detached HTML " + name)
        for filename in ["report.json", "testpilot.patch"]:
            require(data["browser/" + name + "-" + filename] == data["cli/" + name + "/out/" + filename], "actual download " + name + "/" + filename)
    require(b"19 passed" in data["commands/focused-tests.log"], "19 focused tests")
    require(all(c["exit_code"] == 0 for c in json.loads(data["commands/invocations.json"])), "native command exits")
    require(json.loads(data["commands/source-custody.json"])["source_files_unchanged"] is True, "native source custody")
    return {"schema": "testpilot.html_report.pr20_verification.v1", "base": manifest["base"], "tree": manifest["tree"],
            "archive_sha256": sha(archive_bytes), "ordinary_members": 134, "artifacts_verified": 133,
            "source_files_verified": 80, "unowned_current_blobs_verified": 74, "unchanged_frozen_files": 4,
            "composed_files_reconstruct_current_parent": ["README.md", "testpilot/loop.py"],
            "native_focused_tests": 19, "native_cli_cases": 2, "browser_checks": 39, "actual_browser_downloads": 4,
            "resolved_filenames": expected_files, "each_case_total_passed": 3, "each_case_generated_passed": 2,
            "partial_repair_history_and_warnings_preserved": True,
            "verification_execution": "Reads saved artifacts only; no product or browser replay."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2) + "\n", end="")
