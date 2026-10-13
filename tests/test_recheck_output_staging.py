"""Preserve the new recheck destination until complete reports are staged."""
from __future__ import annotations

import base64
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from testpilot import recheck
from testpilot.sandbox import CaseResult, SandboxResult

NAMES = {"md": "recheck.md", "json": "recheck.json", "html": "recheck.html"}


def sample(repo):
    """Authored serializer fixture, not evidence that these tests executed."""
    name = "tests/test_retained.py"
    source = "# café\r\ndef test_retained():\n    assert True"
    final = SandboxResult(
        0, False, 0.1, 10, "Authored writer fixture; no execution claim.\n",
        [CaseResult(name + "::test_retained", "passed", generated_file=name)],
        generated_files=[name], junit_available=True,
    ).to_dict()
    return {
        "schema": "testpilot.recheck/1", "status": "passed", "ok": True,
        "repo": str(repo), "python": sys.executable,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "source_report": {"path": "authored-original.json", "sha256": "a" * 64,
                          "recorded_status": "failed"},
        "test_files": {name: source},
        "retained_tests": [{"path": name, "bytes": len(source.encode("utf-8")),
                            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                            "placement": "temporary"}],
        "final": final, "model_calls": 0,
        "scope": "Authored writer fixture only; no pytest or provider executed.",
    }


def legacy_outputs(result, out):
    """The original writer's actual native text operations, kept independent."""
    out.mkdir(parents=True)
    (out / NAMES["md"]).write_text(recheck.render_recheck(result), encoding="utf-8")
    (out / NAMES["json"]).write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (out / NAMES["html"]).write_text(
        recheck.render_recheck_html((out / NAMES["json"]).read_bytes()), encoding="utf-8")
    return {key: (out / name).read_bytes() for key, name in NAMES.items()}


LIMIT_CHILD = r"""
import errno,json,resource,signal,sys
from pathlib import Path
from testpilot.recheck import write_recheck_outputs
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE,(4096,4096))
try:
    write_recheck_outputs(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
except OSError as exc:
    print(json.dumps({"errno":exc.errno}))
    raise SystemExit(72)
raise SystemExit(0)
"""


class RecheckOutputStagingTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        (self.repo / "keep.txt").write_bytes(b"original project bytes")
        self.result = sample(self.repo)

    def assert_stages_removed(self):
        self.assertEqual(list(self.root.rglob(".testpilot-recheck-*")), [])
        self.assertEqual((self.repo / "keep.txt").read_bytes(), b"original project bytes")

    def test_success_preserves_native_bytes_mapping_modes_and_json_download(self):
        for content in ("ordinary\n", "mixed\r\nnewlines\rand bare\n", "café 雪 🦉 & <literal>"):
            with self.subTest(content=content), tempfile.TemporaryDirectory(dir=self.root) as folder:
                root = Path(folder)
                result = copy.deepcopy(self.result)
                result["final"]["output"] = content
                unchanged = copy.deepcopy(result)
                expected = legacy_outputs(result, root / "legacy")
                out = root / "nested" / "new"
                paths = recheck.write_recheck_outputs(result, out)
                self.assertEqual(paths, {key: out / name for key, name in NAMES.items()})
                self.assertEqual(list(paths), list(NAMES))
                self.assertEqual({key: path.read_bytes() for key, path in paths.items()}, expected)
                for key, path in paths.items():
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode),
                                     stat.S_IMODE((root / "legacy" / NAMES[key]).stat().st_mode))
                download = re.search(rb"data:application/json;base64,([A-Za-z0-9+/=]+)",
                                     paths["html"].read_bytes())
                self.assertIsNotNone(download)
                self.assertEqual(base64.b64decode(download.group(1)), paths["json"].read_bytes())
                self.assertEqual(result, unchanged)
                self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(NAMES.values()))
        self.assert_stages_removed()

    @unittest.skipUnless(os.name == "posix", "real POSIX child file-size limit")
    def test_real_write_failures_leave_destination_absent_and_explicit_retry_succeeds(self):
        for artifact in ("md", "json", "html"):
            with self.subTest(artifact=artifact):
                result = copy.deepcopy(self.result)
                if artifact == "md":
                    result["final"]["summary"] = "long summary " * 600
                elif artifact == "json":
                    result["final"]["output"] = "long diagnostic " * 600
                request = self.root / (artifact + "-request.json")
                request.write_text(json.dumps(result), encoding="utf-8")
                out = self.root / (artifact + "-retry")
                original = request.read_bytes()
                command = [sys.executable, "-B"]
                if sys.flags.optimize:
                    command.append("-O")
                command.extend(["-c", LIMIT_CHILD, str(request), str(out)])
                env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONPATH": str(Path(recheck.__file__).resolve().parent.parent)}
                limited = subprocess.run(command, capture_output=True, text=True, env=env, timeout=10)
                self.assertEqual(limited.returncode, 72, limited.stderr)
                self.assertEqual(json.loads(limited.stdout)["errno"], errno.EFBIG)
                self.assertEqual(limited.stderr, "")
                self.assertFalse(out.exists())
                self.assert_stages_removed()
                expected = legacy_outputs(result, self.root / (artifact + "-reference"))
                actual = recheck.write_recheck_outputs(result, out)
                self.assertEqual({key: p.read_bytes() for key, p in actual.items()}, expected)
                self.assertEqual(request.read_bytes(), original)
        self.assert_stages_removed()

    def test_preparation_failures_do_not_create_final_directory(self):
        for renderer in ("render_recheck", "render_recheck_html"):
            out = self.root / renderer
            with self.subTest(renderer=renderer), patch.object(
                    recheck, renderer, side_effect=ValueError("authored rendering failure")):
                with self.assertRaisesRegex(ValueError, "authored rendering failure"):
                    recheck.write_recheck_outputs(self.result, out)
            self.assertFalse(out.exists())
        self.assert_stages_removed()

    def test_unencodable_markdown_leaves_destination_available_for_corrected_input(self):
        result = copy.deepcopy(self.result)
        result["final"]["summary"] = "unencodable \ud800"
        out = self.root / "unicode"
        with self.assertRaises(UnicodeEncodeError):
            recheck.write_recheck_outputs(result, out)
        self.assertFalse(out.exists())
        self.assert_stages_removed()
        self.assertEqual(set(recheck.write_recheck_outputs(self.result, out)), set(NAMES))

    def test_occupied_destination_is_preserved_before_rendering(self):
        for kind in ("directory", "file", "symlink", "dangling-symlink"):
            with self.subTest(kind=kind):
                out = self.root / kind
                if kind == "directory":
                    out.mkdir()
                    (out / "keep").write_bytes(b"original")
                elif kind == "file":
                    out.write_bytes(b"original")
                else:
                    target = self.root / (kind + "-target")
                    if kind == "symlink":
                        target.write_bytes(b"original")
                    try:
                        out.symlink_to(target)
                    except OSError:
                        continue
                with patch.object(recheck, "render_recheck_html", side_effect=RuntimeError("renderer entered")):
                    with self.assertRaises(recheck.RecheckError):
                        recheck.write_recheck_outputs(self.result, out)
                if kind == "directory":
                    self.assertEqual((out / "keep").read_bytes(), b"original")
                elif kind == "file":
                    self.assertEqual(out.read_bytes(), b"original")
                else:
                    self.assertTrue(out.is_symlink())
                    self.assertEqual(out.readlink(), target)
                    if kind == "symlink":
                        self.assertEqual(target.read_bytes(), b"original")
                    else:
                        self.assertFalse(target.exists())
        self.assert_stages_removed()

    def test_destination_occupied_after_staging_is_never_replaced(self):
        out = self.root / "late-occupant"
        original_mkdir = Path.mkdir

        def occupy(path, *args, **kwargs):
            if path == out and not path.exists():
                original_mkdir(path)
                (path / "keep").write_bytes(b"new occupant")
            return original_mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", occupy):
            with self.assertRaises(FileExistsError):
                recheck.write_recheck_outputs(self.result, out)
        self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, {"keep": b"new occupant"})
        self.assert_stages_removed()

    def test_late_publication_failure_retains_honest_partial_result(self):
        out = self.root / "late-move"
        expected = legacy_outputs(self.result, self.root / "reference")
        original_replace = Path.replace

        def refuse_json(source, target):
            if target == out / NAMES["json"]:
                raise OSError(errno.EACCES, "authored publication refusal", str(target))
            return original_replace(source, target)

        with patch.object(Path, "replace", refuse_json):
            with self.assertRaises(OSError) as raised:
                recheck.write_recheck_outputs(self.result, out)
        self.assertEqual(raised.exception.errno, errno.EACCES)
        self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, {NAMES["md"]: expected["md"]})
        with self.assertRaises(recheck.RecheckError):
            recheck.write_recheck_outputs(self.result, out)
        self.assert_stages_removed()


if __name__ == "__main__":
    unittest.main(verbosity=2)
