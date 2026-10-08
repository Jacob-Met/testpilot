#!/usr/bin/env python3
"""Independent native Git/CLI oracle; no imports from either TestPilot source tree."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args, *, cwd, env, input_bytes=None, check=False):
    process = subprocess.run(
        args, cwd=cwd, env=env, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
    )
    if check and process.returncode:
        raise RuntimeError(f"{args!r}: {process.returncode}: {process.stderr!r}")
    return process


def files(repo):
    names = ["a/subject.py", "subject.py", ".gitattributes", ".git/config"]
    return {name: sha((repo / name).read_bytes()) for name in names}


def line_count(path):
    return len(path.read_bytes().splitlines()) if path.exists() else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    contract = json.loads((Path(__file__).parent / "contract.json").read_text())
    expected = contract["oracle"]["expected_record"]

    env = dict(os.environ)
    for name in list(env):
        if name.startswith(("GIT_CONFIG_", "TESTPILOT_", "GIT_EXTERNAL_DIFF")) or name in {
            "GIT_DIFF_OPTS", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
            "GIT_COMMON_DIR", "GIT_PREFIX", "PYTHONPATH", "PYTHONSTARTUP",
        }:
            env.pop(name, None)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1",
        "PYTHONPATH": str(source), "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
    })
    source_before = {
        str(path.relative_to(source)): sha(path.read_bytes())
        for path in sorted(source.rglob("*")) if path.is_file()
    }
    case_names = [
        "default", "noprefix_decoy", "mnemonicprefix", "color_always",
        "prefix_color_combined", "external_config", "external_environment",
        "textconv", "all_helpers_and_styling", "raw_file", "raw_stdin",
        "invalid_ref",
    ]
    rows = []
    for name in case_names:
        work = out / name
        repo = work / "repo"
        (repo / "a").mkdir(parents=True)
        case_env = dict(env)
        imported = work / "PROJECT_EXECUTED"
        external_marker = work / "EXTERNAL_DIFF_EXECUTED"
        textconv_marker = work / "TEXTCONV_EXECUTED"
        external = work / "external.sh"
        textconv = work / "textconv.sh"
        external.write_text(
            "#!/bin/sh\nprintf 'invoked\\n' >> " + shlex.quote(str(external_marker))
            + "\nprintf 'a display-only external diff\\n'\n", encoding="utf-8",
        )
        textconv.write_text(
            "#!/bin/sh\nprintf 'invoked\\n' >> " + shlex.quote(str(textconv_marker))
            + "\nprintf 'identical display conversion\\n'\n", encoding="utf-8",
        )
        external.chmod(0o755)
        textconv.chmod(0o755)

        header = (
            "from pathlib import Path\n"
            f"Path({str(imported)!r}).write_text('unexpected execution', encoding='utf-8')\n"
            "raise RuntimeError('project source must only be parsed')\n\n"
        )
        original = header + "def answer():\n    return 41\n"
        current = header + "def answer():\n    return 42\n"
        (repo / "a/subject.py").write_text(original)
        (repo / "subject.py").write_text(header + "def decoy():\n    return -999\n")
        (repo / ".gitattributes").write_text("*.py diff=display\n")
        git = ["git", "-C", str(repo)]
        run(git + ["init", "-q"], cwd=work, env=case_env, check=True)
        run(git + ["config", "user.name", "Independent TestPilot receiver"], cwd=work, env=case_env, check=True)
        run(git + ["config", "user.email", "receiver@example.invalid"], cwd=work, env=case_env, check=True)
        run(git + ["config", "core.autocrlf", "false"], cwd=work, env=case_env, check=True)
        run(git + ["add", "--", "a/subject.py", "subject.py", ".gitattributes"], cwd=work, env=case_env, check=True)
        run(git + ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixed receiver baseline"], cwd=work, env=case_env, check=True)
        (repo / "a/subject.py").write_text(current)

        settings = {}
        if name in {"noprefix_decoy", "prefix_color_combined", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            settings["diff.noprefix"] = "true"
        if name in {"mnemonicprefix", "prefix_color_combined", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            settings["diff.mnemonicprefix"] = "true"
        if name in {"color_always", "prefix_color_combined", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            settings["color.ui"] = "always"
        if name in {"external_config", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            settings["diff.external"] = str(external)
        if name in {"external_environment", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            case_env["GIT_EXTERNAL_DIFF"] = str(external)
        if name in {"textconv", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            settings["diff.display.textconv"] = str(textconv)
        for key, value in settings.items():
            run(git + ["config", key, value], cwd=work, env=case_env, check=True)

        before = files(repo)
        raw = (
            "diff --git a/a/subject.py b/a/subject.py\r\n"
            "--- a/a/subject.py\r\n"
            "+++ b/a/subject.py\r\n"
            "@@ -5,2 +5,2 @@\r\n"
            " def answer():\r\n"
            "-    return 41\r\n"
            "+    return 42\r\n"
        ).encode()
        raw_file = work / "raw.patch"
        raw_file.write_bytes(raw)
        argv = [sys.executable, "-B", "-m", "testpilot", "targets", "--repo", str(repo), "--json"]
        data = None
        if name == "raw_file":
            argv += ["--diff", str(raw_file)]
        elif name == "raw_stdin":
            argv += ["--diff", "-"]
            data = raw
        elif name == "invalid_ref":
            argv += ["--git-base", "missing-independent-receiver-ref"]
        else:
            argv += ["--git-base", "HEAD"]
        result = run(argv, cwd=work, env=case_env, input_bytes=data)
        (work / "cli.stdout").write_bytes(result.stdout)
        (work / "cli.stderr").write_bytes(result.stderr)
        cli_helpers = {"external": line_count(external_marker), "textconv": line_count(textconv_marker)}
        try:
            payload = json.loads(result.stdout)
        except (ValueError, UnicodeError):
            payload = None
        preserved = before == files(repo)
        if name == "invalid_ref":
            semantic = result.returncode == 2 and b"cannot inspect targets" in result.stderr and payload is None
        else:
            semantic = result.returncode == 0 and payload == {"changed_functions": [expected]}
        checks = {
            "exact_expected_target_or_ref_refusal": semantic,
            "no_project_execution": not imported.exists(),
            "no_cli_diff_helper_execution": all(count == 0 for count in cli_helpers.values()),
            "source_and_git_config_unchanged": preserved,
            "raw_input_unchanged": sha(raw_file.read_bytes()) == sha(raw),
        }

        direct = None
        if name in {"external_config", "external_environment", "textconv", "all_helpers_and_styling", "raw_file", "raw_stdin"}:
            before_markers = {"external": line_count(external_marker), "textconv": line_count(textconv_marker)}
            positive = run(git + ["diff", "HEAD", "--", "*.py"], cwd=work, env=case_env)
            (work / "direct-git.stdout").write_bytes(positive.stdout)
            (work / "direct-git.stderr").write_bytes(positive.stderr)
            expected_helper = "textconv" if name == "textconv" else "external"
            after_markers = {"external": line_count(external_marker), "textconv": line_count(textconv_marker)}
            helper_delta = {key: after_markers[key] - before_markers[key] for key in before_markers}
            direct = {"exit": positive.returncode, "helper_delta": helper_delta}
            checks["direct_git_positive_helper_control"] = positive.returncode == 0 and helper_delta[expected_helper] > 0
            checks["direct_git_preserves_source_and_config"] = before == files(repo)

        row = {
            "case": name, "checks": checks, "pass": all(checks.values()),
            "exit": result.returncode, "payload": payload,
            "cli_helpers": cli_helpers, "direct_git_control": direct,
            "argv": argv, "local_settings": settings,
            "source_config_hashes": before,
            "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
        }
        rows.append(row)
        print(name, "PASS" if row["pass"] else "FAIL", "target=", None if payload is None else [(f["path"], f["qualname"]) for f in payload["changed_functions"]], "helpers=", cli_helpers, flush=True)

    source_after = {
        str(path.relative_to(source)): sha(path.read_bytes())
        for path in sorted(source.rglob("*")) if path.is_file()
    }
    summary = {
        "schema": 1, "receiver": "chatgpt-e46e74cdc4f4/production",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version, "git": subprocess.check_output(["git", "--version"]).decode().strip(),
        "source": str(source), "contract_sha256": sha((Path(__file__).parent / "contract.json").read_bytes()),
        "receiver_sha256": sha(Path(__file__).read_bytes()),
        "source_inputs_unchanged": source_before == source_after, "source_inputs": source_before,
        "passed": sum(row["pass"] for row in rows), "failed": sum(not row["pass"] for row in rows),
        "cases": rows,
    }
    (out / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("passed", "failed", "source_inputs_unchanged")}))
    return 0 if summary["failed"] == 0 and summary["source_inputs_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
