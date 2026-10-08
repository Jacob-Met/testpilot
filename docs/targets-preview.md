# Preview the functions selected by a diff

Use `testpilot targets` to inspect what TestPilot's existing selector would send into generation. The command prints changed Python functions and methods before a developer chooses to run test generation.

## Inspect a working tree

From a TestPilot checkout or installed package:

```sh
python -m testpilot targets --repo /path/to/project --git-base main
```

The default output contains a quoted source path, inclusive line range, and qualified function name for each target:

```text
1 changed Python function outside tests
"src/cart.py":7-12  "total"
```

Paths and names use JSON quoting so Unicode escapes, tabs, or newlines cannot be confused with another output row. The concise view does not print function bodies.

## Inspect a saved diff or pipe

The source choices match the generation command:

```sh
python -m testpilot targets --repo /path/to/project --diff change.diff
git diff main -- '*.py' | python -m testpilot targets --repo . --diff -
```

Exactly one of `--diff` or `--git-base` is required. `--diff -` reads standard input. With `--git-base`, the command invokes the same native Git working-tree diff used by `run`; this retains Git's configured repository behavior.

## Read the selected source as JSON

```sh
python -m testpilot targets --repo /path/to/project --git-base main --json
```

The top-level `changed_functions` array uses the native selector's records, with no second AST walk or new selection rules. Each record contains:

| Field | Meaning |
| --- | --- |
| `path` | Exact repository-relative diff path |
| `module` | Existing selector's import module name |
| `qualname` | Function or class-qualified method name |
| `lineno`, `end_lineno` | Inclusive source range, including decorators |
| `changed_lines` | Added lines within the selected function |
| `source` | Current function source returned by the selector |
| `is_method` | Whether the function is selected in a class |

The same `changed_functions` field appears in a generation report. JSON strings preserve the native path and source values, including escaped characters.

A successful empty preview is `{"changed_functions": []}`. It means the selector found no eligible changed Python functions. It does not establish that the repository is clean or that tests pass.

## What preview executes

The preview calls the existing `changed_functions` reader. It parses selected source rather than importing project modules, constructs no model client, runs no pytest, and does not invoke the report or patch writer. It needs no scripted replies or model configuration. Redirecting stdout to a file is an ordinary caller-controlled way to save the preview.

The existing native selector still controls test-path exclusion, deleted-file handling, decorated and conditional definitions, containment checks, source decoding, and line attribution. Source and diff inputs are read at invocation time. A preview does not reserve those bytes: edits between preview and generation can change the selected context. A supplied diff is interpreted against the current working tree, just as in `run`.

This command is an inspection interface, not an execution sandbox or a new Git configuration policy. Generation remains a separate explicit `testpilot run` invocation, with all existing backend, project-Python, sandbox, reporting, and exit behavior retained.

## Exit codes

- `0`: the preview was produced, including an empty selection.
- `2`: invalid command arguments, unreadable diff input, failed Git diff, or a native source-selection/parse error. There is no partial success output.

Generation's existing exit codes remain unchanged. The `--python`, `--script`, backend, repair, timeout, token-budget, and output-directory options belong to `run`, not `targets`.

## Focused verification

The new tests use real disposable Git diffs and actual module CLI processes, plus a saved-diff call with explicit model, runner, subprocess, and output-writer tripwires:

```sh
python -m unittest discover -s tests -p test_cli_targets.py
```

They also retain an actual native `run` control that produces the existing zero-target report without consuming a scripted model reply. Full repository pytest qualification and model quality are separate from this CLI receiving boundary.
