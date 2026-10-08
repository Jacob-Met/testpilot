"""Finalize the independent TestPilot source and private-fixture review."""
from pathlib import Path
import ast, hashlib, json, os, stat, subprocess, time
PROJECT = Path("/home/jacob/hamon-e46e74cdc4f4-testpilot")
ROOT = Path("/home/jacob/hamon-e46e74cdc4f4-testpilot-source-review")
PARENT = "191cca4e416286a9e1fa4b5d5daf5fc30b936db6"
env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
def git(*args):
    return subprocess.run(["git", "-C", str(PROJECT), *args], env=env, check=True, capture_output=True).stdout
def metadata(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
v1 = json.loads((ROOT / "review-v1.json").read_text())
original_main = git("show", PARENT + ":testpilot/__main__.py")
current_main = (PROJECT / "testpilot/__main__.py").read_bytes()
current_readme = (PROJECT / "README.md").read_bytes()
original_readme = git("show", PARENT + ":README.md")
current_test = (PROJECT / "tests/test_cli_git_diff_config.py").read_bytes()
initial_test = (ROOT / "candidate.test_cli_git_diff_config.py").read_bytes()
assert metadata(current_main)["sha256"] == "01dc85e0d4d1b0616f8c9616a6515e9e8236922c4a12ea20d47e13c5d5b85975"
assert metadata(current_test)["sha256"] == "f31e4b275c06b1064ac6da89e7463e4647197ab9232d6df71a46fd8de162dd45"
assert metadata(current_readme)["sha256"] == "9b87f414f792ef371b09d2e512ab3432191bf85c54853d220f236fa020c18181"
assert metadata(initial_test)["sha256"] == "e541ee6edc58faa6d1bb90acd9cb0675c898e26b0920f425e0b0e151fae730c9"
old = ast.parse(original_main)
new = ast.parse(current_main)
func = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == "_read_diff")
calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)
         and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
         and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"]
assert len(calls) == 1
argv = calls[0].args[0]
assert isinstance(argv, ast.List)
added = ["--no-ext-diff", "--no-textconv", "--no-color", "--src-prefix=a/", "--dst-prefix=b/"]
assert [n.value for n in argv.elts[4:9]] == added
del argv.elts[4:9]
assert ast.dump(new, include_attributes=False) == ast.dump(old, include_attributes=False)
assert current_readme == (ROOT / "candidate.README.md").read_bytes()
note = (
    b"The \x60--git-base\x60 path requests a raw, uncolored Git patch with standard file\n"
    b"prefixes. Git display preferences such as \x60diff.noprefix\x60, \x60diff.mnemonicprefix\x60\n"
    b"and forced color therefore keep the same source targets. External diff and\n"
    b"text-conversion helpers are disabled for this read; the repository's Git\n"
    b"configuration stays unchanged. Saved-file and stdin \x60--diff\x60 inputs retain their\n"
    b"existing decoding and selection behavior.\n\n"
)
assert current_readme.count(note) == 1
assert current_readme.replace(note, b"", 1) == original_readme
before_environment = (
    b"        self.env = dict(os.environ)\n"
    b'        for key in ("GIT_EXTERNAL_DIFF", "GIT_DIFF_OPTS", "GIT_CONFIG_COUNT"):\n'
    b"            self.env.pop(key, None)\n"
)
after_environment = (
    b"        self.env = {key: value for key, value in os.environ.items()\n"
    b'                    if not key.startswith("GIT_")}\n'
)
assert initial_test.count(before_environment) == 1
assert initial_test.replace(before_environment, after_environment, 1) == current_test
(ROOT / "final.test_cli_git_diff_config.py").write_bytes(current_test)
leaves = []
for raw in git("ls-tree", "-rz", PARENT).split(b"\0"):
    if not raw:
        continue
    header, raw_path = raw.split(b"\t", 1)
    mode, kind, blob = header.decode().split()
    assert kind == "blob"
    path = raw_path.decode()
    native = PROJECT / path
    if mode == "120000":
        data = os.fsencode(os.readlink(native))
        actual_mode = "120000"
    else:
        data = native.read_bytes()
        actual_mode = "100755" if native.stat().st_mode & stat.S_IXUSR else "100644"
    leaves.append({"path": path, "parent_mode": mode, "current_mode": actual_mode,
                   "parent_blob": blob, "current_blob": metadata(data)["git_blob"]})
changed = [x for x in leaves if x["parent_mode"] != x["current_mode"] or x["parent_blob"] != x["current_blob"]]
assert sorted(x["path"] for x in changed) == ["README.md", "testpilot/__main__.py"]
assert all(x["parent_mode"] == x["current_mode"] for x in leaves)
receipts = {}
for label, source_hash, expected in [
    ("original", "e541ee6edc58faa6d1bb90acd9cb0675c898e26b0920f425e0b0e151fae730c9", False),
    ("corrected", "f31e4b275c06b1064ac6da89e7463e4647197ab9232d6df71a46fd8de162dd45", True),
]:
    path = ROOT / ("sentinel-" + label) / "receipt.json"
    data = path.read_bytes()
    receipt = json.loads(data)
    assert receipt["accepted"] and receipt["source_unchanged"] and receipt["private_sentinels_only"]
    assert receipt["source"]["sha256"] == source_hash
    assert not receipt["product_cli_run"] and len(receipt["cases"]) == 2
    assert all(row["isolated"] == expected for row in receipt["cases"])
    receipts[label] = {
        "path": str(path), **metadata(data),
        "time_utc": receipt["time_utc"], "python": receipt["python"],
        "cases": [{"route": row["route"], "isolated": row["isolated"],
                  "setup_succeeded": row["fixture_receipt"]["setup_succeeded"],
                  "sentinel_changed_paths": row["sentinel_changed_paths"],
                  "before_file_count": len(row["before"]), "after_file_count": len(row["after"])}
                 for row in receipt["cases"]],
    }
record = {
    "schema": "testpilot.git-diff-source-review.final.v1",
    "reviewer": "chatgpt:/root/source_frontier",
    "status": "accepted: bounded runtime change and corrected new-test fixture",
    "parent": PARENT, "source_checkout": str(PROJECT),
    "observed_head": git("rev-parse", "HEAD").decode().strip(),
    "source": {
        "testpilot/__main__.py": metadata(current_main), "README.md": metadata(current_readme),
        "tests/test_cli_git_diff_config.py": metadata(current_test), "initial_authored_test": metadata(initial_test),
    },
    "checks": {
        "full_runtime_ast_restored_by_removing_only_five_literal_git_arguments": True,
        "argv_additions": added,
        "readme_restored_by_removing_only_bounded_behavior_note": True,
        "new_test_restored_from_initial_author_version_with_only_environment_filter_replacement": True,
        "tracked_parent_leaf_count": len(leaves),
        "tracked_original_leaves_and_modes_preserved": len(leaves) - len(changed),
        "tracked_changed_paths": changed, "tracked_modes_all_preserved": True,
    },
    "review_conclusions": [
        "The five arguments are inserted only into the Git-source diff command before the unchanged base revision, separator and Python pathspec.",
        "Saved diff files, stdin decoding, target parser, errors and unrelated CLI behavior retain the same full-module AST.",
        "The README note describes only the Git-source read and is the sole README change.",
        "Clearing inherited GIT_* belongs only to the newly authored test fixture and occurs before its first Git invocation.",
        "The new fixture retains its explicit process-local Git system/global isolation, project PYTHONPATH, no-bytecode setting and every original behavioral assertion.",
        "Private sentinel receiving demonstrates the fixture-routing defect on the initial test and verifies that the corrected fixture creates and commits its own repository while preserving all sentinel file bytes.",
    ],
    "fixture_receiving": receipts,
    "receiver": {"path": str(ROOT / "receive_fixture_isolation.py"),
                 **metadata((ROOT / "receive_fixture_isolation.py").read_bytes())},
    "boundaries": [
        "This reviewer ran only private Git fixture setup/teardown receiving, plus static source and byte/mode review.",
        "No product CLI, model/provider, production repository mutation, remote write, service restart or hosted CI run was performed by this receiver.",
        "Runtime behavioral acceptance is recorded independently by the production receiver and author's tests; this receipt does not replace those gates.",
        "Sentinel byte-preservation measures every retained file including .git; it does not claim filesystem metadata or atime preservation.",
    ],
    "source_runtime_unchanged_after_review": (PROJECT / "testpilot/__main__.py").read_bytes() == current_main,
    "source_test_unchanged_after_review": (PROJECT / "tests/test_cli_git_diff_config.py").read_bytes() == current_test,
    "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
assert record["source_runtime_unchanged_after_review"] and record["source_test_unchanged_after_review"]
data = (json.dumps(record, indent=2) + "\n").encode()
path = ROOT / "review-final.json"
path.write_bytes(data)
print(json.dumps({"path": str(path), **metadata(data), "status": record["status"],
                  "source": record["source"], "leaf_count": len(leaves),
                  "unchanged_leaves": len(leaves) - len(changed),
                  "fixture_receipts": receipts, "receiver": record["receiver"]}, indent=2))
