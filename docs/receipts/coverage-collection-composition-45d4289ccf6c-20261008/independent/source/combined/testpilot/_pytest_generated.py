"""Run pytest with generated files added to its normal configured collection.

Copied beside the sandbox manifest so the chosen project interpreter needs only
pytest, not an installed copy of TestPilot. The project keeps its own collection
roots, conftest files, fixtures, selection hooks and assertion rewriting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

if __name__ == "__main__":
    # Match ``python -m pytest`` without adding the temporary runner directory
    # to the project's import search path.
    sys.path[0] = str(Path.cwd())


class GeneratedFiles:
    def __init__(self, files: dict[str, str]):
        self.files = files

    @pytest.hookimpl(trylast=True)
    def pytest_configure(self, config):
        selected = {str(Path(arg.split("::", 1)[0]).resolve()) for arg in config.args}
        config.args.extend(path for path in self.files if path not in selected)

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
