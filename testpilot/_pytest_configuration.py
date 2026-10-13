"""Keep native pytest configuration inside the copied project.

Run with the selected project interpreter. The private parent marker stops
ancestor discovery; a root fallback keeps relative path options rooted in the
project when no project configuration was selected.
"""
from __future__ import annotations

import inspect
import runpy
import sys
from pathlib import Path

from _pytest.config.findpaths import locate_config


def prepare_configuration(marker: Path) -> None:
    root = Path.cwd()
    try:
        # pytest 8.0 accepts only args; newer finders also take invocation_dir.
        options = {"args": [root]}
        if "invocation_dir" in inspect.signature(locate_config).parameters:
            options["invocation_dir"] = root
        selected = locate_config(**options)[1]
    except Exception:
        # Let the normal invocation report malformed default configuration,
        # or use an explicit -c that legitimately bypasses that configuration.
        return
    if selected is not None and selected.resolve() == marker.resolve():
        try:
            with (root / "pytest.ini").open("x", encoding="utf-8") as stream:
                stream.write("[pytest]\n")
        except FileExistsError:
            # Never replace a project file if one appeared after discovery.
            pass


def main() -> None:
    # Match python -m pytest without adding the private runner directory to
    # project imports. The generated-file runner preserves the same convention.
    sys.path[0] = str(Path.cwd())
    prepare_configuration(Path(sys.argv[1]))
    command = sys.argv[2:]
    if command[:2] == ["-m", "pytest"]:
        sys.argv = ["pytest", *command[2:]]
        runpy.run_module("pytest", run_name="__main__", alter_sys=True)
    else:
        sys.argv = command
        runpy.run_path(command[0], run_name="__main__")


if __name__ == "__main__":
    main()
