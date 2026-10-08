# Test a project in its prepared Python environment

Use `--python` when the repository's dependencies are installed in a different
environment from TestPilot. The selected interpreter runs the existing tests,
generated tests, every repair round, and optional coverage collection. TestPilot
and its model client continue running in the interpreter that launched the CLI.

For example, from the repository containing `.venv`:

```sh
testpilot run --repo . --git-base main --python .venv/bin/python \
  --script /path/to/scripted-responses --out out/testpilot
```

On Windows, use `.venv\Scripts\python.exe`. Quote paths containing spaces.
Absolute paths are accepted; relative paths are interpreted from the shell's
current directory, before TestPilot copies the repository to its temporary test
directory. A command such as `python3.12` is looked up on `PATH`. A virtual
environment's Python symlink stays bound to that environment.

Prepare the selected environment with the project's dependencies and `pytest`
before running the command. Install `coverage` there too if a coverage report is
needed. TestPilot does not install dependencies or activate an environment for
you. A missing or non-executable interpreter is a configuration error (exit 2).

Without `--python`, test runs continue to use the interpreter running TestPilot.
The test timeout, scripted/provider selection, generated patch, and output
locations retain their existing behavior.
