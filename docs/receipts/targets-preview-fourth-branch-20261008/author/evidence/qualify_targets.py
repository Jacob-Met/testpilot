"""Portable focused CLI receiving against a selected exact TestPilot checkout."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
import unittest

def digest(path):
    raw = path.read_bytes()
    return {
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    test = args.test.resolve()
    if args.out.exists():
        raise SystemExit("refusing to overwrite a retained receiving result")
    paths = sorted((source / "testpilot").glob("*.py"))
    before = {str(p.relative_to(source)): digest(p) for p in paths}
    test_before = digest(test)
    sys.path.insert(0, str(source))
    spec = importlib.util.spec_from_file_location("test_cli_targets", test)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = {str(p.relative_to(source)): digest(p) for p in paths}
    report = {
        "source": str(source), "test": str(test),
        "python": sys.version, "platform": platform.platform(),
        "optimized": sys.flags.optimize,
        "methods": result.testsRun, "successful": result.wasSuccessful(),
        "failures": [{"id": t.id(), "traceback": text} for t, text in result.failures],
        "errors": [{"id": t.id(), "traceback": text} for t, text in result.errors],
        "skipped": result.skipped,
        "native_cli_invocations": len(module.CLI_RECEIPTS),
        "cli_receipts": module.CLI_RECEIPTS,
        "direct_main_tripwire_case": "test_saved_diff_preview_never_constructs_model_or_test_runner",
        "source_before": before, "source_after": after,
        "test_before": test_before, "test_after": digest(test),
        "source_unchanged": before == after and test_before == digest(test),
        "log": stream.getvalue(),
        "boundary": "Actual CLI/Git and one injected no-effects main seam; no pytest framework, inference, account or live project.",
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "methods": report["methods"], "successful": report["successful"],
        "failures": len(report["failures"]), "errors": len(report["errors"]),
        "skipped": len(report["skipped"]),
        "native_cli_invocations": report["native_cli_invocations"],
        "source_unchanged": report["source_unchanged"], "out": str(args.out),
    }))
    return 0 if result.wasSuccessful() and report["source_unchanged"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
