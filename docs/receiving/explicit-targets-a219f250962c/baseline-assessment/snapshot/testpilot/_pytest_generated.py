"""Run pytest with generated files added to its normal configured collection.

Copied beside the sandbox manifest so the chosen project interpreter needs only
pytest, not an installed copy of TestPilot. The project keeps its own collection
roots, conftest files, fixtures, selection hooks and assertion rewriting.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest
from _pytest.main import search_pypath

if __name__ == "__main__":
    # Match ``python -m pytest`` without adding the temporary runner directory
    # to the project's import search path.
    sys.path[0] = str(Path.cwd())


class GeneratedFiles:
    def __init__(self, files: dict[str, str]):
        self.files = files
        self.covered_paths: set[Path] = set()

    @pytest.hookimpl(trylast=True)
    def pytest_configure(self, config):
        selected = set()
        path_options = {}
        if config.option.pyargs and "consider_namespace_packages" in inspect.signature(search_pypath).parameters:
            path_options["consider_namespace_packages"] = config.getini("consider_namespace_packages")
        for arg in config.args:
            path = arg.split("::", 1)[0]
            if config.option.pyargs:
                path = search_pypath(path, **path_options) or path
            selected.add(str(Path(path).resolve()))
        roots = [Path(path) for path in selected if Path(path).is_dir()]
        for path in self.files:
            if path in selected:
                continue
            resolved = Path(path).resolve()
            if any(resolved.is_relative_to(root) for root in roots):
                self.covered_paths.add(resolved)
            else:
                config.args.append(path)

    @pytest.hookimpl(tryfirst=True)
    def pytest_collectstart(self, collector):
        if isinstance(collector, pytest.Session) and self.covered_paths:
            # pytest 8.0 skips a directory cached while resolving an explicit
            # child; newer versions normalize that child out of initial paths.
            # Traverse the normal root once, but retain the generated child's
            # explicit treatment for python_files and ignored parent paths.
            collector._initialpaths |= self.covered_paths
            collector._initialpaths_with_parents |= {
                parent for path in self.covered_paths for parent in (path, *path.parents)
            }

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items):
        for item in items:
            rel = self.files.get(str(item.path.resolve()))
            if rel is not None:
                item.user_properties.append(("testpilot.generated_file", rel))


def main() -> int:
    files = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    return pytest.main(sys.argv[2:], plugins=[GeneratedFiles(files)])


if __name__ == "__main__":
    raise SystemExit(main())
