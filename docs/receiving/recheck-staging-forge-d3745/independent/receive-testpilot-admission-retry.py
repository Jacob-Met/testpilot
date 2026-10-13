#!/usr/bin/env python3
"""Independent actual-CLI admission recovery control; no writer fault injection."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, pathlib, stat, subprocess, sys, traceback
from html.parser import HTMLParser

BASE_COMMIT = "ffc2590682f30c3ff23084aacb79a8f50111f273"
BASE_PINS = {"testpilot/__init__.py":"296210dd0d58703de4a4e4c9ad72a0944c9400ca","testpilot/__main__.py":"6c1f799a830abc759ba4489251f58095b47d36ad","testpilot/_pytest_generated.py":"90b82725bc0eb1ff3d7cb517c4c9dedcfd14bdcc","testpilot/compare.py":"11d8bbd4939b749760bd2b5fc26326a79ece1e40","testpilot/compare_html.py":"40da0f674798583bd25a177021759aa38b3c5b7b","testpilot/diff.py":"f9970ed6f2a05b259a4f5de6379eb3c041865886","testpilot/html_report.py":"3281bd01b5df5c3122bf95fe4f3bdbc2217642ee","testpilot/loop.py":"69dc4ea2df567133e64ed5ea9d37ace26475d091","testpilot/model.py":"effb064a91caacc1ca1e8e4c6fbfcaeb786e2e02","testpilot/recheck.py":"b5d0b705c30c03e6b7e7e90b83e8dc83b8f9de52","testpilot/recheck_html.py":"9b16cf829029e1b5d34392bb93f6d3a31e916a90","testpilot/regression.py":"9d877deed683c0e38d61fcf5c7320d8f5dd672c9","testpilot/sandbox.py":"6dc325b68ee9de568e93c45666e3da845d6237de","testpilot/targets.py":"2da1600eca93edbe47605e6ca2a9e715663fa370"}
WRITERS = {
    "baseline": "3eab07bd639994f897f76c0cd2b941d5e294c6d7c8132c82deb800e44d7079e6",
    "candidate": "1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6",
}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, reason):
    if not value: raise RuntimeError(reason)
def snapshot(root):
    return {str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes()), "mode": stat.S_IMODE(p.stat().st_mode)}
            for p in sorted(root.rglob("*")) if p.is_file()}
def source_snapshot(root, variant):
    result = {}
    for rel, expected in BASE_PINS.items():
        p = root / rel
        require(p.is_file() and not p.is_symlink(), "source not regular: " + rel)
        raw = p.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if rel == "testpilot/recheck.py":
            require(sha(raw) == WRITERS[variant], "writer source pin differs")
        else:
            require(blob == expected, "inherited module pin differs: " + rel)
        result[rel] = {"bytes": len(raw), "sha256": sha(raw), "git_blob": blob, "mode": stat.S_IMODE(p.stat().st_mode)}
    return result
class Downloads(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("download") == "recheck.json":
            self.urls.append(d.get("href", ""))
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=pathlib.Path, required=True)
    ap.add_argument("--variant", choices=WRITERS, required=True)
    ap.add_argument("--work", type=pathlib.Path, required=True)
    a = ap.parse_args()
    source = a.source.resolve(strict=True)
    before = source_snapshot(source, a.variant)
    work = a.work.absolute()
    require(not work.exists() and not work.is_symlink(), "work path must be new")
    require(all(not p.is_symlink() for p in work.parents), "work parent symlink")
    work.mkdir(mode=0o700)
    report = {"schema": "testpilot.independent-cli-admission-retry.v1", "variant": a.variant,
              "source_root": str(source), "base_commit": BASE_COMMIT, "python": sys.version,
              "scope": "Preserved admission/recovery control, not a new admission fix or staging-failure witness.",
              "source_before": before, "commands": [], "checks": []}
    def check(ok, name):
        require(ok, name); report["checks"].append(name)
    try:
        project = work / "project"; project.mkdir()
        (project / "demo.py").write_text("def add_one(value):\n    return value + 1\n", encoding="utf-8")
        marker = work / "test-executions.txt"
        test = ("from demo import add_one\n\ndef test_retained_add_one():\n"
                "    assert add_one(4) == 5\n"
                "    with open(" + repr(str(marker)) + ", 'a', encoding='utf-8') as stream:\n"
                "        stream.write('executed\\n')\n")
        tests = {"tests/test_retained_add_one.py": test}
        good = (json.dumps({"status": "historical-fixture", "test_files": tests}, ensure_ascii=False, indent=2) + "\n").encode()
        encoded = json.dumps(tests, ensure_ascii=False).encode()
        bad = b'{"status":"historical-fixture","test_files":' + encoded + b',"test_files":' + encoded + b'}\n'
        valid = work / "saved-valid.json"; valid.write_bytes(good)
        invalid = work / "saved-invalid-original.json"; invalid.write_bytes(bad)
        corrected = work / "saved-input.json"; corrected.write_bytes(bad)
        project_before = snapshot(project)
        temporary = work / "tmp"; temporary.mkdir(mode=0o700)
        env = os.environ.copy()
        env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1",
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", TMPDIR=str(temporary))
        def execute(input_path, out, label):
            cmd = [sys.executable, "-B", "-m", "testpilot", "recheck", "--repo", str(project),
                   "--report", str(input_path), "--out", str(out), "--timeout", "20"]
            p = subprocess.run(cmd, cwd=work, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=35)
            item = {"label": label, "argv": cmd, "returncode": p.returncode,
                    "stdout": p.stdout.decode("utf-8", "replace"), "stderr": p.stderr.decode("utf-8", "replace")}
            report["commands"].append(item); return p
        def receive(out, expected_source):
            check(set(p.name for p in out.iterdir()) == {"recheck.md", "recheck.json", "recheck.html"}, "three complete output names")
            raw = (out / "recheck.json").read_bytes(); v = json.loads(raw)
            check(v["status"] == "passed" and v["ok"] is True and v["model_calls"] == 0, "actual successful model-free result")
            check(v["source_report"]["sha256"] == sha(good) and v["source_report"]["path"] == str(expected_source), "exact admitted source identity")
            check(v["test_files"] == tests and v["source_report"]["recorded_status"] == "historical-fixture", "retained tests and historical status")
            final = v["final"]
            check(final["junit_available"] is True and final["returncode"] == 0 and not final["timed_out"], "real native pytest completed")
            cases = final["cases"]
            check(len(cases) == 1 and cases[0]["outcome"] == "passed" and cases[0]["generated_file"] == "tests/test_retained_add_one.py", "one retained generated case passed")
            parsed = Downloads(); parsed.feed((out / "recheck.html").read_text(encoding="utf-8"))
            prefix = "data:application/json;base64,"
            check(len(parsed.urls) == 1 and parsed.urls[0].startswith(prefix), "one exact JSON download")
            check(base64.b64decode(parsed.urls[0][len(prefix):], validate=True) == raw, "HTML embedded JSON equals sibling bytes")
            return snapshot(out)
        neighbor = work / "neighbor"
        p = execute(valid, neighbor, "known-good neighbor")
        check(p.returncode == 0 and not p.stderr, "neighbor CLI success")
        neighbor_before = receive(neighbor, valid)
        check(marker.read_text() == "executed\n", "neighbor executes retained test once")
        retry = work / "retry"
        p = execute(corrected, retry, "duplicate-key refusal")
        failed_argv = report["commands"][-1]["argv"]
        check(p.returncode == 2 and not p.stdout and b"duplicate JSON key" in p.stderr, "malformed saved input refused by actual CLI")
        check(not retry.exists(), "refusal leaves final destination absent")
        check(marker.read_text() == "executed\n", "refusal executes no retained test")
        check(snapshot(neighbor) == neighbor_before and snapshot(project) == project_before, "refusal preserves neighbor and checked project")
        corrected.write_bytes(good)
        p = execute(corrected, retry, "explicit corrected retry")
        check(report["commands"][-1]["argv"] == failed_argv, "explicit retry repeats exact CLI argv")
        check(p.returncode == 0 and not p.stderr, "explicit corrected CLI retry success")
        report["retry_artifacts"] = receive(retry, corrected)
        check(marker.read_text() == "executed\nexecuted\n", "only the two explicit successful calls execute tests")
        check(snapshot(neighbor) == neighbor_before, "neighbor report bytes and modes unchanged")
        check(snapshot(project) == project_before, "project unchanged and retained tests remain sandbox-only")
        check(valid.read_bytes() == good and invalid.read_bytes() == bad and corrected.read_bytes() == good, "only explicit input correction changes fixture")
        check(list(temporary.iterdir()) == [], "owned sandbox temporary directory cleaned")
        report["neighbor_artifacts"] = neighbor_before
        report["fixture_hashes"] = {"valid": sha(good), "invalid_original": sha(bad), "corrected_input": sha(corrected.read_bytes())}
        report["passed"] = True
    except Exception as exc:
        report["passed"] = False; report["error"] = str(exc); report["traceback"] = traceback.format_exc()
    finally:
        try:
            after = source_snapshot(source, a.variant)
            require(after == before, "package source bytes or modes changed")
            report["source_after"] = after; report["source_unchanged"] = True
        except Exception as exc:
            report["passed"] = False; report["source_error"] = str(exc)
        raw = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode()
        receipt = work / "receipt.json"
        with receipt.open("xb") as stream: stream.write(raw)
        print(json.dumps({"passed": report["passed"], "variant": a.variant, "checks": len(report["checks"]),
                          "receipt": str(receipt), "bytes": len(raw), "sha256": sha(raw), "error": report.get("error")}))
    return 0 if report["passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
