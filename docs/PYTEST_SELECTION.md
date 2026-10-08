# Select the pytest cases used by a generation run

Use native pytest keyword and marker expressions when a project has a focused
offline test scope. The same selection is configured for the existing-test
baseline, generated tests and every repair run:

```sh
python -m testpilot run --repo /path/to/project --git-base main \
  --backend scripted --script replies --pytest-k 'parser and not slow' \
  --pytest-m 'unit and not external' --out parser-review
```

Both expressions are interpreted by the selected project's pytest version. If
both are provided, a case must match both. These options do not change which
Python functions TestPilot selects from a diff or explicit `--target` values.
They also do not configure pytest testpaths, import behavior, plugins, markers or
fixtures: the project must supply any required configuration. A fixture can
still run for a selected case. Deselection is not an isolation boundary.

Quote the expression for your shell. To pass a value beginning with a dash, use
`--pytest-k=VALUE` or `--pytest-m=VALUE`. Each expression is forwarded as one
argument; it cannot introduce another pytest command-line option. Whitespace
and an explicitly empty string are retained. Omit both flags to retain the
existing unfiltered behavior. A native pytest usage refusal in a selected
baseline stops the run with failed diagnostics before asking a model to write
tests.

The Python API has corresponding keyword-only arguments:

```python
pilot = TestPilot(client, pytest_k="parser and not slow", pytest_m="unit")
result = pilot.run(project, diff_text)
```

Arguments must be strings without NUL or `None`. TestPilot does not implement a
second parser for pytest's expression grammar. The planner, writer and repairer
receive the literal selection so they can produce tests that are collected
within it. An existing selected test passing is insufficient: at least one
generated case must actually pass under the unchanged generated-case admission
rules. If all generated cases are deselected, the run remains `no_tests` even
when existing selected cases pass. Generated files and the proposed patch remain
available for review, without claiming that the patch passed.

When either selector is supplied, `report.json` includes optional context:

```json
"pytest_selection": {"keyword": "parser and not slow", "marker": "unit"}
```

An omitted counterpart is `null`; explicit empty values remain `""`. The field
is absent when neither selector is supplied. Markdown and HTML show the literal
context and identify that unselected tests were not verified. Coverage, when
enabled, describes the selected execution; it does not establish the result of
the unselected suite. The HTML's embedded JSON and patch keep their exact bytes.

## Saved-test recheck remains a separate execution

`testpilot recheck` does **not** inherit these generation filters. It retains its
existing behavior of admitting exact saved tests and running them with the
current project's configured suite. A filtered generation can pass and its later
unfiltered recheck can fail. Inspect each execution's own result; a saved filtered
pass does not establish a full-suite pass or authorize changing recheck admission.
