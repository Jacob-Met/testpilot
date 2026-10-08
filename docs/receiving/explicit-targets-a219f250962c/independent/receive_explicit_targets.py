"""Independent native receiving for TestPilot's explicit-target contribution.

The optional observation wrapper calls the actual CLI main and native
make_client, returning its untouched ScriptedModel while retaining actual calls.
No production file is edited, no model/provider transport is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

BEFORE = """LIMIT = 10


def accepts(amount):
    return amount <= LIMIT


def ignored(amount):
    return amount + 5


class Policy:
    @staticmethod
    def cap(amount, limit=LIMIT):
        return min(amount, limit)
"""
AFTER = BEFORE.replace("LIMIT = 10", "LIMIT = 7").replace("amount + 5", "amount + 6")
EXISTING = "from settings import ignored\n\ndef test_existing_stays_in_run():\n    assert ignored(1) == 7\n"
FIRST_TESTS = """from settings import accepts, Policy

def test_selected_limit():
    assert accepts(8) is True

def test_selected_default():
    assert Policy.cap(20) == 7
"""
FINAL_TESTS = """from settings import accepts, Policy

def test_selected_limit():
    assert accepts(7) is True
    assert accepts(8) is False

def test_selected_default():
    assert Policy.cap(20) == 7
"""
OBSERVER = r"""
import json, os, pathlib, sys
from testpilot import __main__ as cli
from testpilot.model import ScriptedModel
actual = cli.make_client
seen = []
def record_client(*args, **kwargs):
    client = actual(*args, **kwargs)
    if not isinstance(client, ScriptedModel):
        raise RuntimeError("Receiver admits only the actual ScriptedModel")
    seen.append(client)
    return client
cli.make_client = record_client
try:
    code = cli.main(sys.argv[1:])
finally:
    pathlib.Path(os.environ["TARGET_RECEIVER_CALLS"]).write_text(
        json.dumps([{"type": type(c).__name__, "calls": c.calls} for c in seen], ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
raise SystemExit(code)
"""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def snapshot(root):
    result = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink() and ".git" not in p.relative_to(root).parts:
            b = p.read_bytes()
            result[str(p.relative_to(root))] = {"bytes": len(b), "sha256": sha(b)}
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--baseline-source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    source = Path(args.source).resolve()
    baseline_source = Path(args.baseline_source).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        raise RuntimeError("Receiver output destination already exists")
    free = shutil.disk_usage(out.parent).free
    if free < 1024 ** 3:
        raise RuntimeError(f"Receiving free-space floor not met: {free}")
    out.mkdir()
    package_before = snapshot(source / "testpilot")
    baseline_before = snapshot(baseline_source / "testpilot")
    receipt = {"schema": "testpilot.independent_explicit_targets.v1",
               "started_at": time.time(), "python": sys.version,
               "source": str(source), "baseline_source": str(baseline_source),
               "free_bytes_before": free, "commands": [], "groups": [],
               "qualification": "Native synthetic fixtures and actual ScriptedModel only; no live model quality claim"}
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(source)
    for key in list(env):
        if key.startswith("TESTPILOT_"):
            env.pop(key)
    env["TESTPILOT_BACKEND"] = "scripted"

    def command(label, argv, *, cwd=None, input_bytes=None, child_env=None, expected=0, timeout=45):
        began = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, input=input_bytes, env=child_env or env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        record = {"label": label, "argv": [str(a) for a in argv],
                  "returncode": result.returncode, "seconds": time.monotonic() - began,
                  "stdout": result.stdout.decode("utf-8", "backslashreplace"),
                  "stderr": result.stderr.decode("utf-8", "backslashreplace")}
        receipt["commands"].append(record)
        if expected is not None and result.returncode != expected:
            raise AssertionError(f"{label}: exit {result.returncode}, expected {expected}: {record['stderr']}")
        return record

    def cli(label, argv, *, source_root=source, observe=False, input_bytes=None, expected=0):
        child_env = dict(env, PYTHONPATH=str(source_root))
        calls = out / (label.replace("/", "_") + "-model-calls.json")
        prefix = [sys.executable, "-m", "testpilot"]
        if observe:
            child_env["TARGET_RECEIVER_CALLS"] = str(calls)
            prefix = [sys.executable, "-c", OBSERVER]
        record = command(label, prefix + argv, child_env=child_env, input_bytes=input_bytes, expected=expected)
        seen = json.loads(calls.read_text()) if calls.exists() else []
        return record, seen

    def group(name, run):
        began = time.monotonic()
        try:
            details = run()
            receipt["groups"].append({"name": name, "pass": True, "seconds": time.monotonic() - began, "details": details})
        except Exception:
            receipt["groups"].append({"name": name, "pass": False, "seconds": time.monotonic() - began, "traceback": traceback.format_exc()})
        (out / "receiving-progress.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    try:
        with tempfile.TemporaryDirectory(prefix="fixture-", dir=out) as raw:
            fixture = Path(raw)
            repo = fixture / "repo"
            repo.mkdir()
            (repo / "tests").mkdir()
            (repo / "settings.py").write_text(BEFORE, encoding="utf-8")
            (repo / "tests/test_existing.py").write_text(EXISTING, encoding="utf-8")
            command("git-init", ["git", "init", "-q", str(repo)])
            command("git-add", ["git", "-C", str(repo), "add", "."])
            command("git-commit", ["git", "-C", str(repo), "-c", "user.name=HAMON receiving",
                                  "-c", "user.email=hamon-receiving@invalid.example", "commit", "-qm", "Synthetic receiving baseline"])
            (repo / "settings.py").write_text(AFTER, encoding="utf-8")
            diff = command("actual-git-diff", ["git", "-C", str(repo), "diff", "HEAD", "--", "*.py"])["stdout"]
            diff_path = fixture / "change.diff"
            diff_path.write_text(diff, encoding="utf-8")
            specs = ["settings.py::Policy.cap", "settings.py::accepts", "settings.py::Policy.cap"]
            spec_args = [part for spec in specs for part in ("--target", spec)]
            common = ["--repo", str(repo), "--git-base", "HEAD"]
            original = snapshot(repo)
            scripts = fixture / "script"
            scripts.mkdir()
            fence = chr(96) * 3
            for name, content in [("00-plan.txt", "Pin only the caller-selected boundary and captured default."),
                                  ("01-generate.txt", fence + "python path=tests/test_selected.py\n" + FIRST_TESTS + fence + "\n"),
                                  ("02-repair.txt", fence + "python path=tests/test_selected.py\n" + FINAL_TESTS + fence + "\n")]:
                (scripts / name).write_text(content, encoding="utf-8")

            def default_parity():
                old, _ = cli("default-baseline", ["targets"] + common + ["--json"], source_root=baseline_source)
                new, _ = cli("default-candidate", ["targets"] + common + ["--json"])
                assert old["stdout"] == new["stdout"]
                obj = json.loads(new["stdout"])
                assert list(obj) == ["changed_functions"]
                assert [f["qualname"] for f in obj["changed_functions"]] == ["ignored"]
                return {"exact_json_equal": True, "default_targets": ["ignored"]}

            def preview():
                record, _ = cli("explicit-preview", ["targets"] + common + spec_args + ["--json"])
                data = json.loads(record["stdout"])
                functions = data["changed_functions"]
                assert [f["qualname"] for f in functions] == ["Policy.cap", "accepts"]
                assert all(f["changed_lines"] == [] for f in functions)
                selection = data["selection"]
                assert selection["mode"] == "explicit" and selection["requested"] == specs
                assert selection["diff_text"] == diff
                assert "Caller" in selection["reason"] and "inference" in selection["reason"]
                assert functions[0]["is_method"] is True and functions[1]["is_method"] is False
                assert snapshot(repo) == original
                receipt["preview"] = data
                return {"caller_order": True, "duplicates_once": True, "unchanged_lines_empty": True,
                        "input_unchanged": True}

            def generation():
                output = out / "native-run"
                record, clients = cli("explicit-run", ["run"] + common + spec_args +
                                      ["--backend", "scripted", "--script", str(scripts),
                                       "--rounds", "1", "--timeout", "15", "--out", str(output)], observe=True)
                data = json.loads((output / "report.json").read_text(encoding="utf-8"))
                assert data["status"] == "passed" and data["tests_written"] == 2
                assert data["repair_rounds_used"] == 1
                assert [f["qualname"] for f in data["changed_functions"]] == ["Policy.cap", "accepts"]
                assert data["selection"]["requested"] == specs and data["selection"]["diff_text"] == diff
                assert len(clients) == 1 and clients[0]["type"] == "ScriptedModel"
                calls = clients[0]["calls"]
                assert len(calls) == 3
                for _, messages in calls:
                    text = "\n".join(m["content"] for m in messages)
                    assert diff in text
                    for fn in data["changed_functions"]:
                        assert fn["source"] in text
                    assert "Caller" in text or "caller" in text
                coverage = data.get("coverage")
                if coverage is not None:
                    assert coverage["changed_lines_executable"] == 0
                    assert coverage["changed_lines_before"] is None and coverage["changed_lines_after"] is None
                assert snapshot(repo) == original
                receipt["native_result"] = data
                return {"actual_cli_main": True, "observation_only_wrapper": True, "native_model_calls": 3,
                        "all_prompts_contain_exact_diff_and_selected_source": True,
                        "existing_and_generated_suite_passed": True, "source_unchanged": True}

            def patch_receive():
                output = out / "native-run"
                patch = output / "testpilot.patch"
                assert patch.is_file()
                delivery = fixture / "delivery"
                command("delivery-clone", ["git", "clone", "-q", "--no-hardlinks", str(repo), str(delivery)])
                (delivery / "settings.py").write_text(AFTER, encoding="utf-8")
                before_input = (delivery / "settings.py").read_bytes()
                existing_input = (delivery / "tests/test_existing.py").read_bytes()
                command("patch-check", ["git", "-C", str(delivery), "apply", "--check", str(patch)])
                command("patch-apply", ["git", "-C", str(delivery), "apply", str(patch)])
                ran = command("installed-patch-pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                              cwd=delivery)
                assert "3 passed" in ran["stdout"]
                assert (delivery / "settings.py").read_bytes() == before_input
                assert (delivery / "tests/test_existing.py").read_bytes() == existing_input
                return {"patch_sha256": sha(patch.read_bytes()), "actual_git_apply": True,
                        "installed_tests": 3, "original_inputs_preserved": True}

            group("default_selector_output_parity", default_parity)
            group("explicit_preview_custody_and_order", preview)
            group("actual_cli_generation_repair_and_prompt_context", generation)
            group("actual_patch_install_and_native_execution", patch_receive)

            (repo / "ambiguous.py").write_text("if True:\n    def same():\n        return 1\nelse:\n    def same():\n        return 2\n", encoding="utf-8")
            (repo / "badsyntax.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
            (repo / "plain.txt").write_text("def hidden():\n    return 1\n", encoding="utf-8")
            outside = fixture / "outside.py"
            outside.write_text("def hidden():\n    return 'outside'\n", encoding="utf-8")
            (repo / "outside_link.py").symlink_to(outside)
            refusals = ["settings.py::missing", "ambiguous.py::same", "tests/test_existing.py::test_existing_stays_in_run",
                        "../outside.py::hidden", str(outside) + "::hidden", "outside_link.py::hidden",
                        "plain.txt::hidden", "badsyntax.py::broken", "settings.py", "settings.py::"]
            refusal_snapshot = snapshot(repo)
            def refused_targets():
                cases = []
                for i, target in enumerate(refusals):
                    output = out / f"refused-output-{i}"
                    record, clients = cli(f"refusal-{i}", ["run", "--repo", str(repo), "--diff", str(diff_path),
                                                   "--target", target, "--backend", "scripted",
                                                   "--script", str(scripts), "--out", str(output)],
                                           observe=True, expected=2)
                    assert not output.exists()
                    assert not any(c["calls"] for c in clients)
                    cases.append({"target": target, "exit": record["returncode"], "model_calls": 0, "output_absent": True})
                assert snapshot(repo) == refusal_snapshot
                assert outside.read_text() == "def hidden():\n    return 'outside'\n"
                return {"cases": cases, "source_and_outside_bytes_unchanged": True}
            group("refusals_before_execution_or_generation", refused_targets)

            # Remove only our intentionally invalid sibling so it cannot interfere
            # with current native diff selection during this separate preview.
            (repo / "badsyntax.py").unlink()
            (repo / "latin1.py").write_bytes(b"# coding: latin-1\n# caf\xe9\n\ndef caf\xe9(value):\n    return value + 1\n")
            (repo / "never_import.py").write_text("raise RuntimeError('preview must never import this source')\n\ndef picked(value):\n    return value\n", encoding="utf-8")
            def literal_and_read_only_preview():
                record, _ = cli("literal-preview", ["targets", "--repo", str(repo), "--diff", "-",
                                                   "--target", "latin1.py::caf\u00e9", "--target", "never_import.py::picked", "--json"],
                                input_bytes=diff.encode("utf-8"))
                data = json.loads(record["stdout"])
                assert [f["qualname"] for f in data["changed_functions"]] == ["caf\u00e9", "picked"]
                assert "def caf\u00e9(value):" in data["changed_functions"][0]["source"]
                assert data["selection"]["diff_text"] == diff
                assert (repo / "latin1.py").read_bytes().startswith(b"# coding: latin-1\n# caf\xe9")
                return {"unicode_name_and_encoding_cookie": True, "stdin_context_exact": True,
                        "selected_module_not_imported": True}
            group("encoded_source_and_read_only_stdin_preview", literal_and_read_only_preview)
    except Exception:
        receipt["fatal_error"] = traceback.format_exc()
    finally:
        receipt["package_source_unchanged"] = snapshot(source / "testpilot") == package_before
        receipt["baseline_source_unchanged"] = snapshot(baseline_source / "testpilot") == baseline_before
        receipt["source_fingerprints"] = package_before
        receipt["finished_at"] = time.time()
        receipt["accepted"] = (len(receipt["groups"]) == 6 and all(g["pass"] for g in receipt["groups"])
                               and receipt["package_source_unchanged"] and receipt["baseline_source_unchanged"]
                               and "fatal_error" not in receipt)
        data = (json.dumps(receipt, indent=2, ensure_ascii=True) + "\n").encode()
        (out / "receiving-result.json").write_bytes(data)
        print(json.dumps({"schema": receipt["schema"], "accepted": receipt["accepted"],
                          "groups": [{"name": g["name"], "pass": g["pass"]} for g in receipt["groups"]],
                          "commands": len(receipt["commands"]), "receipt": str(out / "receiving-result.json"),
                          "bytes": len(data), "sha256": sha(data)}))
    return 0 if receipt["accepted"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
