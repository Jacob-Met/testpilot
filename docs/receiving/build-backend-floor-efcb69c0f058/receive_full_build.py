"""Receive the unchanged complete TestPilot tree through an isolated 77.0.3 build.

This is separate from the retained first fixture that omitted NOTICE. It copies
all 1,545 current Git leaves, checks the full source before and after, and joins
the wheel's fourteen modules, two license files, metadata and complete bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: object, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def manifest(files: dict[str, bytes]) -> dict:
    return {n: {"bytes": len(b), "sha256": sha(b)} for n, b in sorted(files.items())}


def receive_source(source: Path, inventory: dict, phase: str) -> tuple[dict, dict]:
    expected = {entry["path"]: entry for entry in inventory["entries"]}
    require(len(expected) == 1545, "complete original Git inventory differs")
    actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
    require(actual == set(expected), "source does not contain exactly the full Git leaf inventory")
    files, mtimes = {}, {}
    for name, entry in expected.items():
        path = source / name
        require(not path.is_symlink(), "unexpected source symlink")
        body = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        wanted = ("9228b2ba8975f07ab59bf5a7b4cb802a81c7fc03"
                  if phase == "candidate" and name == "pyproject.toml" else entry["sha"])
        require(blob == wanted, "Git source bytes differ: " + name)
        mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        require(mode == entry["mode"], "Git source mode differs: " + name)
        files[name] = body
        mtimes[name] = path.stat().st_mtime_ns
    require(inventory["commit"] == "478f68adf01658a94a3ede22526da00f580785bd"
            and inventory["tree"] == "ca0756e20da9c87c90ebd24c45ab494bfa31d47b",
            "full source parent identity differs")
    return files, mtimes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("original", "candidate"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--depot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--original-receipt", type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    inventory = json.loads(args.inventory.read_bytes())
    files, mtimes = receive_source(source, inventory, args.phase)
    floor = "setuptools>=69" if args.phase == "original" else "setuptools>=77.0.3"
    config = tomllib.loads(files["pyproject.toml"].decode())
    require(config["build-system"] == {"requires": [floor], "build-backend": "setuptools.build_meta"},
            "selected declared build backend differs")
    package = {n: b for n, b in files.items() if n.startswith("testpilot/")}
    require(len(package) == 14 and all(n.endswith(".py") for n in package),
            "fourteen-module current package inventory differs")
    require(sha(files["NOTICE"]) == "4564e24959bca812ed0fa34d42786012dddbed523c02dd1bb5bdf424262be344",
            "complete source NOTICE differs")
    depot = args.depot.resolve(strict=True)
    backend = depot / "setuptools-77.0.3-py3-none-any.whl"
    require(sorted(p.name for p in depot.iterdir()) == [backend.name]
            and sha(backend.read_bytes()) == "67122e78221da5cf550ddd04cf8742c8fe12094483749a792d56cd669d6cf58c",
            "exact supported backend depot differs")
    out = args.out.absolute()
    out.mkdir(exist_ok=False)
    before = manifest(files)
    (out / "input-manifest.json").write_text(json.dumps(before, indent=2) + "\n")
    receipt = {"schema": "testpilot.complete-source-build-floor-receiving/1",
               "phase": args.phase, "started_at": datetime.now(timezone.utc).isoformat(),
               "receiver_sha256": sha(Path(__file__).read_bytes()),
               "inventory_sha256": sha(args.inventory.read_bytes()),
               "input_manifest_sha256": sha((out / "input-manifest.json").read_bytes()),
               "parent": inventory["commit"], "parent_tree": inventory["tree"],
               "source_leaves": len(files), "source": str(source),
               "pyproject_sha256": sha(files["pyproject.toml"]),
               "package_files": manifest(package),
               "license_files": manifest({n: files[n] for n in ("LICENSE", "NOTICE")}),
               "python": sys.version.split()[0], "frontend_python": sys.executable,
               "backend": "77.0.3", "backend_wheel_sha256": sha(backend.read_bytes())}
    try:
        project = out / "project"
        shutil.copytree(source, project)
        copied, _ = receive_source(project, inventory, args.phase)
        require(copied == files, "complete build copy differs")
        temporary = out / "temporary"
        temporary.mkdir()
        wheels = out / "wheels"
        env = {k: v for k, v in os.environ.items() if k.upper() in {"PATH", "LANG", "LC_ALL"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                   SOURCE_DATE_EPOCH="1791835200", PIP_NO_INDEX="1",
                   PIP_DISABLE_PIP_VERSION_CHECK="1", TMPDIR=str(temporary))
        command = [sys.executable, "-m", "pip", "--isolated", "--verbose", "wheel",
                   "--no-index", "--find-links", str(depot), "--no-deps", "--no-cache-dir",
                   "--disable-pip-version-check", "--wheel-dir", str(wheels), str(project)]
        result = subprocess.run(command, cwd=out, env=env, capture_output=True, timeout=45)
        (out / "stdout.log").write_bytes(result.stdout)
        (out / "stderr.log").write_bytes(result.stderr)
        receipt.update(command=command, returncode=result.returncode,
                       stdout_sha256=sha(result.stdout), stderr_sha256=sha(result.stderr))
        built = list(wheels.glob("*.whl"))
        require(result.returncode == 0 and len(built) == 1, "complete-source isolated build failed")
        require(b"Successfully installed setuptools-77.0.3" in result.stdout + result.stderr,
                "isolated backend installation is not identified in actual logs")
        wheel = built[0]
        receipt["wheel"] = {"file": wheel.name, "bytes": wheel.stat().st_size,
                            "sha256": sha(wheel.read_bytes())}
        with zipfile.ZipFile(wheel) as archive:
            require(archive.testzip() is None, "wheel CRC differs")
            members = {name: archive.read(name) for name in archive.namelist()}
        dist = "testpilot-0.1.0.dist-info/"
        expected_names = set(package) | {dist + n for n in
                         ("METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt",
                          "licenses/LICENSE", "licenses/NOTICE")}
        require(set(members) == expected_names, "complete wheel inventory differs")
        require({n: members[n] for n in package} == package, "packaged module bytes differ")
        for name in ("LICENSE", "NOTICE"):
            require(members[dist + "licenses/" + name] == files[name], "packaged license bytes differ")
        metadata = BytesParser().parsebytes(members[dist + "METADATA"])
        require(metadata["Name"] == "testpilot" and metadata["Version"] == "0.1.0"
                and metadata["Requires-Python"] == ">=3.12"
                and metadata["License-Expression"] == "Apache-2.0", "package metadata differs")
        require(sorted(metadata.get_all("License-File")) == ["LICENSE", "NOTICE"],
                "both declared wheel license files must be retained")
        require(sorted(metadata.get_all("Requires-Dist")) == ['coverage>=7; extra == "coverage"', "pytest>=8"],
                "runtime dependencies differ")
        require(members[dist + "entry_points.txt"] == b"[console_scripts]\ntestpilot = testpilot.__main__:main\n",
                "console entry point differs")
        require(b"Generator: setuptools (77.0.3)" in members[dist + "WHEEL"], "wheel generator differs")
        receipt["wheel_members"] = manifest(members)
        receipt["complete_license_metadata_received"] = True
        if args.phase == "candidate":
            require(args.original_receipt is not None, "candidate needs accepted original receipt")
            original = json.loads(args.original_receipt.read_bytes())
            require(original["accepted"] and original["phase"] == "original"
                    and original["parent"] == inventory["commit"], "original full-source receipt differs")
            original_wheel = args.original_receipt.parent / "wheels" / original["wheel"]["file"]
            require(wheel.read_bytes() == original_wheel.read_bytes(), "complete wheel bytes changed")
            require(receipt["wheel"] == original["wheel"]
                    and receipt["wheel_members"] == original["wheel_members"], "wheel manifests differ")
            receipt["complete_wheel_byte_identical_to_original"] = True
        after, after_mtimes = receive_source(source, inventory, args.phase)
        require(after == files and after_mtimes == mtimes, "complete input source bytes or mtimes changed")
        for name, body in files.items():
            require((project / name).read_bytes() == body, "build modified an inherited source leaf")
        receipt["all_1545_input_bytes_and_mtimes_preserved"] = True
        receipt["all_1545_build_copy_inherited_bytes_preserved"] = True
        receipt["accepted"] = True
    except Exception as error:
        receipt["accepted"] = False
        receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt["limits"] = ("Actual isolated 77.0.3 build from complete current source; no product import, "
                         "runtime suite, installed CLI, provider, native-device or Actions execution. "
                         "The retained first four selected-input builds remain separate historical evidence.")
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "accepted": receipt["accepted"],
                      "wheel": receipt.get("wheel"), "error": receipt.get("error")}))
    return 0 if receipt["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
