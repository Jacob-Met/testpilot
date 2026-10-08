import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
root = Path.cwd()
snapshot = root / "snapshot"
receipt = {"source_commit": "e2285d68b2ea5eb2158c0a7e0d936ce5d56f8ff5", "python": sys.version, "qualification": "Exact-source read-only product assessment; disposable synthetic Git fixtures only", "cases": [], "commands": []}
env = {k: v for k, v in os.environ.items() if not any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET")) and not k.startswith("TESTPILOT_") and k != "PYTHONPATH"}
env["PYTHONDONTWRITEBYTECODE"] = "1"
def command(args, cwd, check=True):
    p = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=15)
    if check and p.returncode:
        raise RuntimeError((args, p.returncode, p.stderr))
    return p
def call_cli(label, args):
    p = command([sys.executable, "-B", "-m", "testpilot", *args], snapshot, False)
    receipt["commands"].append({"label": label, "arguments": args, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
    return p
cases = [
    ("module_constant", "LIMIT = 100\n\n\ndef accepts(amount):\n    return amount <= LIMIT\n", "LIMIT = 50\n\n\ndef accepts(amount):\n    return amount <= LIMIT\n", "accepts", 75, True, False, 0),
    ("default_binding", "LIMIT: int = 100\n\n\ndef cap(amount, limit=LIMIT):\n    return min(amount, limit)\n", "LIMIT: int = 50\n\n\ndef cap(amount, limit=LIMIT):\n    return min(amount, limit)\n", "cap", 150, 100, 50, 0),
    ("ordinary_function_edit", "LIMIT = 100\n\n\ndef accepts(amount):\n    return amount <= LIMIT\n", "LIMIT = 100\n\n\ndef accepts(amount):\n    return amount < LIMIT\n", "accepts", 100, True, False, 1),
]
for label, before, after, name, argument, expected_before, expected_after, expected_targets in cases:
    with tempfile.TemporaryDirectory(prefix="fixture-" + label + "-", dir=root) as temp:
        directory = Path(temp)
        repo = directory / "repo"; repo.mkdir()
        script = directory / "script"; script.mkdir()
        (script / "01.txt").write_text("TRIPWIRE: a no_changes run must not consume this response.\n")
        source = repo / "settings.py"
        source.write_text(before)
        command(["git", "init", "--quiet", str(repo)], directory)
        command(["git", "-C", str(repo), "add", "--", "settings.py"], directory)
        source.write_text(after)
        diff = command(["git", "-C", str(repo), "diff", "--", "settings.py"], directory).stdout
        diff_file = directory / "change.diff"; diff_file.write_text(diff)
        old_namespace, new_namespace = {}, {}
        exec(compile(before, label + ":before", "exec"), old_namespace)
        exec(compile(after, label + ":after", "exec"), new_namespace)
        old_result, new_result = old_namespace[name](argument), new_namespace[name](argument)
        assert old_result == expected_before and new_result == expected_after and old_result != new_result
        preview = call_cli(label + ":targets", ["targets", "--repo", str(repo), "--diff", str(diff_file), "--json"])
        assert preview.returncode == 0, preview.stderr
        targets = json.loads(preview.stdout)["changed_functions"]
        assert len(targets) == expected_targets, targets
        case = {"name": label, "before_source": before, "after_source": after, "git_diff": diff, "function": name, "argument": argument, "before_result": old_result, "after_result": new_result, "target_count": len(targets), "targets": targets}
        if expected_targets == 0:
            out = root / (label + "-run")
            run = call_cli(label + ":run", ["run", "--repo", str(repo), "--diff", str(diff_file), "--backend", "scripted", "--script", str(script), "--out", str(out)])
            report = json.loads((out / "report.json").read_text())
            assert run.returncode == 1 and report["status"] == "no_changes"
            assert report["changed_functions"] == [] and report["ledger"]["entries"] == [] and report["ledger"]["total_tokens"] == 0
            assert report["test_files"] == {} and report["final"] is None and (out / "testpilot.patch").read_bytes() == b""
            case["run"] = {"exit": run.returncode, "status": report["status"], "message": report["message"], "model_calls": len(report["ledger"]["entries"]), "tokens": report["ledger"]["total_tokens"], "generated_files": len(report["test_files"]), "report_sha256": hashlib.sha256((out / "report.json").read_bytes()).hexdigest()}
        if label == "module_constant":
            for mode in ["targets", "run"]:
                requested = [mode, "--repo", str(repo), "--diff", str(diff_file), "--target", "settings.py::accepts"]
                if mode == "run": requested += ["--backend", "scripted", "--script", str(script), "--out", str(directory / "refused-explicit-output")]
                result = call_cli(label + ":missing-explicit-" + mode, requested)
                assert result.returncode == 2 and "unrecognized arguments: --target settings.py::accepts" in result.stderr
            assert not (directory / "refused-explicit-output").exists()
        assert source.read_text() == after and diff_file.read_text() == diff
        case["fixture_bytes_unchanged"] = True
        receipt["cases"].append(case)
manifest = json.loads((root / "source-manifest.json").read_text())
for item in manifest["files"]:
    data = (snapshot / item["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == item["sha256"]
receipt["source_files_unchanged"] = len(manifest["files"])
receipt["actual_cli_calls"] = len(receipt["commands"])
receipt["all_private_git_fixtures_removed"] = True
(root / "assessment-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"cases": [{"name": c["name"], "before": c["before_result"], "after": c["after_result"], "targets": c["target_count"], "run": c.get("run")} for c in receipt["cases"]], "cli_calls": receipt["actual_cli_calls"], "source_files_unchanged": receipt["source_files_unchanged"], "python": sys.version, "receipt": str(root / "assessment-result.json")}))
