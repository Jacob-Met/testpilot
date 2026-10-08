# Repository boundaries for diff-selected source

TestPilot selects Python functions from the repository passed to `--repo`.
Diff paths used for source selection must be relative paths without `..`
components. Absolute paths, parent traversal, and symlinks whose resolved
destination leaves that repository raise `testpilot.diff.DiffSourceError`, a
`ValueError` subclass. The CLI prints an invalid-diff diagnostic and exits with
configuration-error status **2**, without writing reports or a generated patch.

This validation runs during function selection, before the pipeline starts its
baseline pytest run or sends function source to a model. A mixed diff containing
valid and invalid selected paths is rejected as a whole. An outside file is not
read and silently substituted for an intended source module.

Relative filenames retain their original diff identity, including Git-quoted
Unicode names, spaces, and supported host filename bytes. A symlink inside the
repository is supported when its resolved destination also remains inside. The
repository root itself may be a symlink. Existing exclusions still apply:
deleted files, non-Python paths, test paths unless `include_tests=True`, and
missing files within the repository do not become selected functions.

The check validates paths against the filesystem state observed during source
selection. It is not a filesystem sandbox and does not protect against another
process replacing directories between validation and a read. TestPilot's
documented process-isolation limitations remain applicable.

## Verification

The regression module uses only disposable repositories and synthetic outside
files. It covers absolute and parent paths, file and directory symlink escapes,
quoted paths, missing and excluded files, valid aliases and filenames, pipeline
refusal before pytest/model calls, and the actual CLI error/output behavior.

```bash
python -m pytest -q tests/test_diff_source_boundary.py tests/test_diff.py tests/test_git_quoted_paths.py
python -m pytest -q
```

Against source `feea1889358b570d652f456ce5b63e853ba47d47`, the new regression
module had **14 failures and 4 passes**. With the source boundary correction, the
focused selection suite passed **55 tests**, and the complete repository suite
passed **85 tests**, with no skips, on Python 3.12.14, pytest 9.1.1, and coverage
7.16.2. No provider or installed-service operation was used for this verification.
