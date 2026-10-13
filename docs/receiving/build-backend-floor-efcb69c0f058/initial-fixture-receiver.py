"""Exercise the declared TestPilot backend floor through real isolated pip builds.

The caller supplies two offline depots, each containing exactly its indicated
setuptools wheel. The original and candidate phases use new output directories.
No product module, pytest case, model, Git command or workflow is executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
import zipfile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def inputs(source: Path) -> dict[str, bytes]:
    files = [source / n for n in ("pyproject.toml", "README.md", "LICENSE")]
    files.extend(sorted((source / "testpilot").rglob("*.py")))
    require(len(files) == 15, "exact twelve-module packaging input inventory differs")
    return {p.relative_to(source).as_posix(): p.read_bytes() for p in files}


def manifest(files: dict[str, bytes]) -> dict:
    return {n: {"bytes": len(b), "sha256": sha(b)} for n, b in sorted(files.items())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=("original", "candidate"), required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--depots", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--original-receipt", type=Path)
    args = ap.parse_args()
    source = args.source.resolve(strict=True)
    out = args.out.absolute()
    out.mkdir(exist_ok=False)
    files = inputs(source)
    source_before = manifest(files)
    mtimes = {n: (source / n).stat().st_mtime_ns for n in files}
    config = tomllib.loads(files["pyproject.toml"].decode())
    floor = "setuptools>=69" if args.phase == "original" else "setuptools>=77.0.3"
    require(config["build-system"] == {"requires": [floor], "build-backend": "setuptools.build_meta"},
            "source does not have the selected declared backend floor")
    receipt = {"phase": args.phase, "started_at": datetime.now(timezone.utc).isoformat(),
               "receiver_sha256": sha(Path(__file__).read_bytes()),
               "python": sys.version.split()[0], "frontend_python": sys.executable,
               "source": str(source), "input_files": source_before, "cases": []}
    original = None
    if args.phase == "candidate":
        require(args.original_receipt is not None, "candidate needs the accepted original receipt")
        original = json.loads(args.original_receipt.read_bytes())
        require(original["accepted"] and original["phase"] == "original", "original receiving did not pass")
        expected = dict(original["input_files"])
        expected.pop("pyproject.toml")
        actual = dict(source_before)
        actual.pop("pyproject.toml")
        require(actual == expected, "packaging input changed outside pyproject.toml")

    env = {k: v for k, v in os.environ.items() if k.upper() in {"PATH", "LANG", "LC_ALL"}}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
               SOURCE_DATE_EPOCH="1791835200", PIP_NO_INDEX="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1")
    try:
        for backend in ("69.0.0", "77.0.3"):
            depot = (args.depots / ("backend-" + backend)).resolve(strict=True)
            wheels = list(depot.glob("*.whl"))
            require(len(wheels) == 1 and wheels[0].name == "setuptools-" + backend + "-py3-none-any.whl",
                    "backend depot is not the exact single-version input")
            case = out / ("backend-" + backend)
            case.mkdir()
            copy = case / "project"
            copy.mkdir()
            for name, data in files.items():
                path = copy / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            temporary = case / "temporary"
            temporary.mkdir()
            wheel_out = case / "wheels"
            command = [sys.executable, "-m", "pip", "--isolated", "--verbose", "wheel",
                       "--no-index", "--find-links", str(depot), "--no-deps",
                       "--no-cache-dir", "--disable-pip-version-check", "--wheel-dir", str(wheel_out), str(copy)]
            r = subprocess.run(command, cwd=case, env={**env, "TMPDIR": str(temporary)},
                               capture_output=True, timeout=45)
            (case / "stdout.log").write_bytes(r.stdout)
            (case / "stderr.log").write_bytes(r.stderr)
            record = {"backend": backend, "backend_wheel_sha256": sha(wheels[0].read_bytes()),
                      "command": command, "returncode": r.returncode,
                      "stdout_sha256": sha(r.stdout), "stderr_sha256": sha(r.stderr)}
            receipt["cases"].append(record)
            products = list(wheel_out.glob("*.whl")) if wheel_out.exists() else []
            diagnostic = (r.stdout + r.stderr).decode("utf-8", "replace")
            if backend == "69.0.0":
                require(r.returncode != 0 and not products, "old-only depot unexpectedly built a wheel")
                if args.phase == "original":
                    require("project.license" in diagnostic and "configuration error" in diagnostic,
                            "original refusal did not identify the admitted backend's license-schema failure")
                    record["received"] = "admitted69 rejects existing project.license format"
                else:
                    require("setuptools>=77.0.3" in diagnostic and "No matching distribution found" in diagnostic
                            and "project.license" not in diagnostic,
                            "candidate did not reject the unavailable build dependency before metadata validation")
                    record["received"] = "old-only depot refused at declared build dependency resolution"
            else:
                require(r.returncode == 0 and len(products) == 1, "supported-floor build did not produce one wheel")
                wheel = products[0]
                record["wheel"] = {"file": wheel.name, "bytes": wheel.stat().st_size,
                                   "sha256": sha(wheel.read_bytes())}
                with zipfile.ZipFile(wheel) as z:
                    members = {name: z.read(name) for name in z.namelist()}
                record["wheel_members"] = manifest(members)
                packaged = {n: b for n, b in members.items() if n.startswith("testpilot/") and n.endswith(".py")}
                require(packaged == {n: b for n, b in files.items() if n.startswith("testpilot/")},
                        "built wheel does not contain the exact twelve source files")
                metadata = BytesParser().parsebytes(next(b for n, b in members.items() if n.endswith("/METADATA")))
                require(metadata["Name"] == "testpilot" and metadata["Version"] == "0.1.0"
                        and metadata["Requires-Python"] == ">=3.12"
                        and metadata["License-Expression"] == "Apache-2.0",
                        "wheel package/Python/license metadata differs")
                require(sorted(metadata.get_all("Requires-Dist")) == ['coverage>=7; extra == "coverage"', "pytest>=8"],
                        "wheel runtime dependency metadata differs")
                entry = next(b for n, b in members.items() if n.endswith("/entry_points.txt"))
                require(entry == b"[console_scripts]\ntestpilot = testpilot.__main__:main\n",
                        "wheel console entry point differs")
                generator = next(b for n, b in members.items() if n.endswith("/WHEEL"))
                record["wheel_generator_metadata"] = generator.decode("utf-8")
                require("Successfully installed setuptools-77.0.3" in diagnostic,
                        "isolated build log does not identify the selected backend installation")
                record["received"] = "exact package wheel built by declared supported backend"
                if original is not None:
                    before = next(c for c in original["cases"] if c["backend"] == backend)
                    require(record["wheel"] == before["wheel"] and record["wheel_members"] == before["wheel_members"],
                            "correcting the floor changed the wheel built by the same supported backend")
                    record["complete_wheel_identical_to_original"] = True
        require(manifest(inputs(source)) == source_before, "qualification changed input source bytes")
        require({n: (source / n).stat().st_mtime_ns for n in files} == mtimes, "qualification changed input source mtimes")
        receipt["accepted"] = True
    except Exception as exc:
        receipt["accepted"] = False
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt["limits"] = "Real isolated package builds from fifteen exact declared packaging inputs; no runtime suite, installation, pytest, provider, native-device or workflow claim."
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "accepted": receipt["accepted"],
                      "error": receipt.get("error"), "receipt": str(out / "receipt.json")}))
    return 0 if receipt["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
