"""Frozen actual selector + actual sandbox-environment module identity controls."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
RECEIPTS = []
SOURCE_BEFORE = {}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load_exact(name, path):
    SOURCE_BEFORE[str(path)] = digest(path.read_bytes())
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

diff = load_exact("received_testpilot_diff", ROOT / "diff.py")
sandbox = load_exact("received_testpilot_sandbox", ROOT / "sandbox.py")
PROBE = "_estate_module_binding_probe"
SOURCE = "def selected_value():\n    return 2\n"
NATIVE = """import importlib, json, sys
from pathlib import Path
m = importlib.import_module(sys.argv[1])
print(json.dumps({"module_file": str(Path(m.__file__).resolve()), "value": m.selected_value()}))
"""

class ModuleIdentity(unittest.TestCase):
    def exercise(self, path, expected_module, *, shadow=False):
        with tempfile.TemporaryDirectory(prefix="module-identity-", dir=ROOT) as tmp:
            repo = Path(tmp)
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            for directory in (target.parent, target.parent.parent):
                if directory != repo and directory.is_relative_to(repo) and directory.name != "src":
                    init = directory / "__init__.py"
                    if init != target:
                        init.write_bytes(b"")
            target.write_text(SOURCE, encoding="utf-8")
            if shadow:
                (repo / (PROBE + ".py")).write_text("def selected_value():\n    return 99\n", encoding="utf-8")
            before = {str(p.relative_to(repo)): digest(p.read_bytes()) for p in repo.rglob("*") if p.is_file()}
            patch = f"--- a/{path}\n+++ b/{path}\n@@ -1,2 +1,2 @@\n def selected_value():\n-    return 1\n+    return 2\n"
            found = diff.changed_functions(repo, patch)
            self.assertEqual(len(found), 1)
            selected = found[0]
            env = sandbox.clean_env(repo)
            rc, output, timed_out = sandbox._run([sys.executable, "-B", "-c", NATIVE, selected.module], repo, env, 10)
            actual = json.loads(output) if rc == 0 else None
            after = {str(p.relative_to(repo)): digest(p.read_bytes()) for p in repo.rglob("*") if p.is_file()}
            RECEIPTS.append({
                "case": self.id(), "fixture_files": {str(p.relative_to(repo)): p.read_text(encoding="utf-8") for p in repo.rglob("*") if p.is_file()},
                "diff": patch, "selected": selected.to_dict(), "expected_module": expected_module,
                "expected_source": str(target.resolve()), "native_pythonpath": env["PYTHONPATH"],
                "native_returncode": rc, "native_output": output, "native_timed_out": timed_out,
                "native_result": actual, "fixture_hashes_before": before, "fixture_hashes_after": after,
            })
            self.assertEqual(after, before)
            self.assertEqual(selected.path, path)
            self.assertEqual(selected.source, SOURCE.rstrip("\n"))
            self.assertEqual(selected.module, expected_module)
            self.assertFalse(timed_out)
            self.assertEqual(rc, 0, output)
            self.assertEqual(actual["module_file"], str(target.resolve()))
            self.assertEqual(actual["value"], 2)

    def test_regular_root_package_control(self):
        self.exercise("pkg/" + PROBE + ".py", "pkg." + PROBE)

    def test_src_lib_package_control(self):
        self.exercise("src/lib/" + PROBE + ".py", "lib." + PROBE)

    def test_regular_lib_package_has_qualified_import_identity(self):
        self.exercise("lib/" + PROBE + ".py", "lib." + PROBE)

    def test_lib_package_does_not_bind_root_namesake(self):
        self.exercise("lib/" + PROBE + ".py", "lib." + PROBE, shadow=True)

    def test_lib_package_initializer_is_importable(self):
        self.exercise("lib/__init__.py", "lib")

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ModuleIdentity))
    unchanged = all(digest(Path(path).read_bytes()) == sha for path, sha in SOURCE_BEFORE.items())
    receipt = {"schema": "testpilot-module-identity-baseline.v1", "source": json.loads((ROOT / "SOURCE_INPUT.json").read_bytes())["commit"],
               "frozen_test_sha256": digest(Path(__file__).read_bytes()), "python": sys.version,
               "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "source_hashes": SOURCE_BEFORE, "source_unchanged": unchanged, "actual_native_processes": len(RECEIPTS),
               "cases": RECEIPTS, "production_edits": False}
    (ROOT / "BASELINE_WITNESS.json").write_text(json.dumps(receipt, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
