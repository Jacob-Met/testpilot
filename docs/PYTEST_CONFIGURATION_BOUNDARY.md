# Pytest configuration stays with the copied project

TestPilot copies a selected repository into a private temporary directory before
running pytest. A caller may place its temporary directory inside another
project. Pytest's automatic configuration search must not then select that
unrelated project's settings for the copied tests.

An empty `pytest.ini` in the private temporary parent bounds that search. Before
normal collection, the selected interpreter asks its own pytest configuration
finder which root configuration applies. If it selects that exact private
marker, the runner creates an empty fallback in the copied project root. This
keeps explicit relative path options, such as `-o pythonpath=lib`, based in the
project as well.

The runner uses the selected interpreter's pytest finder and accommodates its
pytest 8 and newer call signatures; it does not substitute another environment's
configuration parser.

Native pytest discovery still selects real project configuration, including
nested configuration for explicitly selected test directories. Explicit `-c`
continues to choose its named configuration and path base. Malformed defaults
remain native errors unless explicitly bypassed. A target without pytest
settings uses ordinary defaults instead of inheriting an enclosing project's
`testpaths` and silently skipping a failing test.

The original repository and every existing copied file are unchanged. Explicit
pytest arguments still apply, and the existing JUnit admission, coverage, output,
timeout and process-cleanup behavior is preserved.

Run the focused receiving with the project's Python environment:

```sh
python -m pytest -q tests/test_sandbox_configuration.py
```

The native cases cover an unconfigured target, a target with an unrelated
`pyproject.toml`, the supported INI and TOML configuration formats, an empty target
`pytest.ini`, explicit selection and configuration overrides, relative import
paths, selected nested configuration and malformed defaults.
The false-pass controls contain a real failing test outside the enclosing
project's selected directory; the corrected run reports that native failure.
