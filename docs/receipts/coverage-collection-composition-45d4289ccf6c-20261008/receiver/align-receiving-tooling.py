"""Align only the private receiving environment using unchanged installed tools."""
import hashlib, importlib.util, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

root = Path("/home/jacob/testpilot-coverage-45d4289ccf6c")
evidence = root / "composition-dcd353-evidence"
envroot = root / "composition-receiving-venv"
purelib = envroot / "lib/python3.14/site-packages"
assert purelib.is_dir()
modules = ("pytest", "_pytest", "coverage", "pluggy", "iniconfig", "packaging", "pygments", "py")
records = {}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for name in modules:
    spec = importlib.util.find_spec(name)
    assert spec and spec.origin, name
    package = bool(spec.submodule_search_locations)
    origin = Path(next(iter(spec.submodule_search_locations))) if package else Path(spec.origin)
    target = purelib / (name if package else origin.name)
    if name == "pytest":
        assert target.is_dir() and not target.is_symlink()
        method = "physical copy, all non-cache bytes checked against unchanged installed package"
    else:
        if not target.exists() and not target.is_symlink():
            target.symlink_to(origin, target_is_directory=package)
        assert target.is_symlink() and target.resolve() == origin.resolve(), (name, str(target))
        method = "read-only use through private symlink; original bytes not modified"
    sources = sorted(p for p in origin.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc") if package else [origin]
    files = []
    for source in sources:
        rel = source.relative_to(origin).as_posix() if package else source.name
        actual = target / rel if package else target
        assert actual.read_bytes() == source.read_bytes(), (name, rel)
        files.append({"path": rel, "bytes": source.stat().st_size, "sha256": digest(source)})
    if name == "pytest":
        current = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
        assert current == [f["path"] for f in files]
    records[name] = {"source": str(origin), "receiving_path": str(target), "method": method, "files": files}
newpython = envroot / "bin/python"
probe = "import pytest,coverage,sys,json; from pathlib import Path; print(json.dumps({'python':sys.version,'pytest':pytest.__version__,'pytest_origin':pytest.__file__,'coverage':coverage.__version__,'coverage_origin':coverage.__file__,'fixture_tooling_parent':str(Path(pytest.__file__).resolve().parent.parent)}))"
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
env.pop("PYTHONPATH", None)
env.pop("PYTHONHOME", None)
result = subprocess.run([str(newpython), "-B", "-c", probe], text=True, capture_output=True, env=env, check=False)
(evidence / "aligned-tooling-probe.stdout.txt").write_text(result.stdout)
(evidence / "aligned-tooling-probe.stderr.txt").write_text(result.stderr)
assert result.returncode == 0, (result.stdout, result.stderr)
runtime = json.loads(result.stdout)
assert runtime["fixture_tooling_parent"] == str(purelib)
assert Path(runtime["coverage_origin"]).is_relative_to(purelib)
metadata = [{"path": p.name, "target": str(p.resolve())} for p in sorted(purelib.iterdir()) if p.name.endswith((".dist-info", ".egg-info"))]
report = {
    "utc": datetime.now(timezone.utc).isoformat(),
    "purpose": "Make both installed pytest and coverage available from the one directory shared by the unchanged prepared_python fixture; no product or test change.",
    "base_python": sys.executable,
    "receiving_python": str(newpython),
    "runtime": runtime,
    "module_files": records,
    "metadata_links": metadata,
    "coverage_distribution_metadata": "Absent in original environment; actual coverage module version and bytes verified instead.",
    "prior_setup_failures": ["aligned-tooling-initial-setup-error.txt", "aligned-tooling-resume-setup-error.txt"],
    "tests_executed_by_this_setup": 0,
    "downloads_or_package_installs": False,
    "existing_environments_modified": False,
}
path = evidence / "aligned-tooling-manifest.json"
assert not path.exists()
path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({"manifest": str(path), "sha256": digest(path), "runtime": runtime, "module_file_counts": {k:len(v["files"]) for k,v in records.items()}}, indent=2))
