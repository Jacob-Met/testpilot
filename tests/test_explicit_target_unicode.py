"""Native selection regressions for Python-normalized explicit identifiers."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import testpilot
from testpilot.diff import changed_functions
from testpilot.targets import TargetSelectionError, resolve_targets, selection_record

PACKAGE_ROOT = Path(testpilot.__file__).resolve().parents[1]


class ExplicitTargetUnicodeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="testpilot-target-unicode-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)

    def source(self, text, filename="names.py", encoding="utf-8"):
        path = self.repo / filename
        path.write_bytes(text.encode(encoding))
        return path

    def selected(self, name, filename="names.py", diff=""):
        return resolve_targets(self.repo, diff, [filename + "::" + name])

    def test_decomposed_request_selects_the_composed_python_name(self):
        body = "def Café():\n    return 'literal Cafe\\u0301'\n"
        self.source(body)
        copied = self.selected("Cafe\u0301")
        self.assertEqual(copied, self.selected("Café"))
        self.assertEqual(copied[0].qualname, "Café")
        self.assertEqual(copied[0].source, body.rstrip("\n"))

    def test_compatibility_spellings_select_the_native_ast_name(self):
        for spelling, canonical in (("Kelvin", "Kelvin"), ("ｃａｌｃ", "calc"), ("ﬀoo", "ffoo")):
            with self.subTest(spelling=spelling):
                body = f"def {spelling}():\n    return 'literal {spelling}'\n"
                self.source(body)
                copied = self.selected(spelling)
                self.assertEqual(copied, self.selected(canonical))
                self.assertEqual(copied[0].qualname, canonical)
                self.assertEqual(copied[0].source, body.rstrip("\n"))

    def test_nested_class_and_method_components_use_python_names(self):
        body = ("class Ｃａｆｅ:\n"
                "    class Kitchen:\n"
                "        @staticmethod\n"
                "        def Mixe\u0301():\n"
                "            return 'literal Ｃａｆｅ.Kitchen.Mixe\u0301'\n")
        self.source(body)
        selected = self.selected("Ｃａｆｅ.Kitchen.Mixe\u0301")[0]
        self.assertEqual(selected.qualname, "Cafe.Kitchen.Mixé")
        self.assertTrue(selected.is_method)
        self.assertEqual((selected.lineno, selected.end_lineno), (3, 5))
        self.assertEqual(selected.source, "\n".join(body.splitlines()[2:]))

    def test_equivalent_requests_deduplicate_without_rewriting_intent(self):
        self.source("def Cafe\u0301(): return 1\ndef other(): return 2\n")
        specs = ["names.py::Cafe\u0301", "names.py::other", "names.py::Café"]
        selected = resolve_targets(self.repo, "", specs)
        self.assertEqual([item.qualname for item in selected], ["Café", "other"])
        self.assertEqual(selection_record("", specs)["requested"], specs)
        self.assertEqual(specs[0], "names.py::Cafe\u0301")

    def test_normalization_equivalent_definitions_remain_ambiguous(self):
        self.source("def Kelvin(): return 1\ndef Kelvin(): return 2\n")
        for name in ("Kelvin", "Kelvin"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(TargetSelectionError, "ambiguous target matches 2 definitions"):
                    self.selected(name)

    def test_unicode_source_paths_are_not_normalized(self):
        first = "def Cafe\u0301(): return 'fullwidth path'\n"
        second = "def Cafe\u0301(): return 'ASCII path'\n"
        self.source(first, "ｎａｍｅｓ.py")
        self.source(second, "names.py")
        specs = ["ｎａｍｅｓ.py::Cafe\u0301", "names.py::Café"]
        selected = resolve_targets(self.repo, "", specs)
        self.assertEqual([item.path for item in selected], ["ｎａｍｅｓ.py", "names.py"])
        self.assertEqual([item.source for item in selected], [first.rstrip("\n"), second.rstrip("\n")])
        self.assertEqual(selection_record("", specs)["requested"], specs)

    def test_python_source_encoding_is_preserved(self):
        body = "# coding: latin-1\ndef Café(): return 'déjà'\n"
        path = self.source(body, encoding="latin-1")
        original = path.read_bytes()
        self.assertEqual(self.selected("Cafe\u0301")[0].source, "def Café(): return 'déjà'")
        self.assertEqual(path.read_bytes(), original)

    def test_case_and_distinct_identifiers_and_invalid_names_still_refuse(self):
        self.source("def Café(): return 1\ndef A(): return 2\ndef ordinary(): return 3\n")
        for name in ("café", "Α", "missing", "Café.inner", "bad name", "Café．method", "\u200bCafé"):
            with self.subTest(name=name):
                with self.assertRaises(TargetSelectionError):
                    self.selected(name)
        self.assertEqual(self.selected("ordinary")[0].qualname, "ordinary")
        for spec in ("../names.py::Café", "names.py", "tests/test_names.py::Café"):
            with self.subTest(spec=spec):
                with self.assertRaises(TargetSelectionError):
                    resolve_targets(self.repo, "", [spec])

    def test_explicit_and_automatic_selection_preserve_the_same_source_records(self):
        body = "def Cafe\u0301():\n    return 'literal Cafe\u0301'\n"
        path = self.source(body)
        original = path.read_bytes()
        diff = "--- a/names.py\n+++ b/names.py\n@@ -2 +2 @@\n-    return 1\n+    return 'literal Cafe\u0301'\n"
        self.assertEqual(self.selected("Cafe\u0301", diff=diff), changed_functions(self.repo, diff))
        self.assertEqual(path.read_bytes(), original)

    def test_actual_cli_keeps_copied_spelling_and_never_executes_source(self):
        body = "raise AssertionError('source must not execute')\n\ndef Cafe\u0301():\n    return 'literal Cafe\u0301'\n"
        self.source(body)
        (self.repo / "empty.diff").write_bytes(b"")
        before = {p.name: p.read_bytes() for p in self.repo.iterdir()}
        specs = ["names.py::Cafe\u0301", "names.py::Café"]
        env = dict(os.environ, PYTHONPATH=str(PACKAGE_ROOT), PYTHONDONTWRITEBYTECODE="1")
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                command = [sys.executable, "-B"] + (["-O"] if optimized else [])
                command += ["-m", "testpilot", "targets", "--repo", str(self.repo),
                            "--diff", str(self.repo / "empty.diff"), "--json"]
                for spec in specs:
                    command += ["--target", spec]
                run = subprocess.run(command, cwd=self.repo, env=env, capture_output=True,
                                     encoding="utf-8", timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stderr, "")
                result = json.loads(run.stdout)
                self.assertEqual(result["selection"]["requested"], specs)
                self.assertEqual(result["selection"]["diff_text"], "")
                self.assertEqual(len(result["changed_functions"]), 1)
                selected = result["changed_functions"][0]
                self.assertEqual(selected["qualname"], "Café")
                self.assertEqual(selected["source"], "\n".join(body.splitlines()[2:]))
                self.assertEqual(selected["changed_lines"], [])
        self.assertEqual({p.name: p.read_bytes() for p in self.repo.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
