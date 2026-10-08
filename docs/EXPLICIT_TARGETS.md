# Explicit function targets

Use this workflow when you know which function needs tests, including a function
whose body did not change. For example, changing a module-level limit can change
a function's behavior while the normal diff selector finds no changed function.

Preview the current source before generating:

~~~bash
python -m testpilot targets --repo . --diff change.diff \
  --target settings.py::accepts --json

python -m testpilot run --repo . --diff change.diff \
  --target settings.py::accepts \
  --target service.py::Service.apply \
  --script responses --out out/selected
~~~

Use the same repeatable option with `--git-base REF`, or `--diff -` for stdin.
A diff input remains required; an empty diff is permitted when you deliberately
want tests for current functions without a recorded code change.

## Selection and preview

With `--target`, TestPilot selects exactly the requested current functions in
the order supplied. It does not add automatically changed functions. Repeating
the same resolved source/function identity selects it once, at its first
position. The `selection.requested` record preserves every original argument,
including repetitions and spelling, while function records use normalized
repository-relative paths.

Use a repository-relative Python file followed by `::` and its exact qualified
name. A method is `file.py::Class.method`; nested classes can add more components.
The existing AST discovery also supports async functions and definitions inside
module/class `if`, `try`, `with` and `match` blocks. Nested functions belong to
their enclosing function and cannot be selected separately. The final `::`
separates the path from the name; quote the complete argument in your shell when
the path needs it.

A name must identify one source definition. Multiple definitions with the same
qualified name are refused, including definitions in mutually exclusive branches
or property getter/setter definitions. TestPilot does not guess which definition
will exist at runtime.

Missing files/names, malformed specs, non-Python and test sources, absolute or
parent-traversing paths, and symlinks resolving outside the repository are
refused before baseline tests or model calls. A normal-looking alias to a test
source is also refused. Inside-repository source symlinks follow the existing
containment rule. Python source is decoded with Python's encoding-cookie/BOM
rules; selecting source never imports or executes it.

The existing `targets` preview remains read-only: no tests, generated files,
model calls or output directories. Text output says "caller-selected"; `--json`
includes the exact selected source records plus the selection context. A preview
does not reserve files: `run` reads the current source again.

## Context and saved results

Explicit mode sends the exact current selected function source and the exact
diff string received by `TestPilot.run` to the planner, editor and every repair
call. It identifies the functions as caller-selected and potentially unchanged.
The CLI retains its existing raw-byte diff loader, including universal-newline
normalization and surrogate escaping; recorded `diff_text` is that loaded
string, not a reconstruction or a byte-for-byte copy of the original diff file.

The existing `changed_functions` JSON field remains the selected native source
record list for compatibility. Explicit previews and run reports additionally
include:

~~~json
{
  "selection": {
    "mode": "explicit",
    "requested": ["settings.py::accepts"],
    "reason": "Caller selected these targets; no dependency inference was performed.",
    "diff_text": "<exact loaded diff string>"
  }
}
~~~

Markdown labels caller-selected functions and the reason. The offline HTML view
also shows the reason and an expandable literal diff context. Its original JSON
download retains the complete selection record.

Without `--target` (or with the Python API's default `targets=None`), the existing
automatic selector, prompts, report/preview schema and output remain unchanged.
The optional `selection` object is absent. Python callers can use
`TestPilot.run(repo, diff_text, targets=["path.py::qualname"])`; an empty explicit
sequence is an error. `testpilot.targets.resolve_targets(repo, diff_text, targets)`
provides the same resolver, raising `TargetSelectionError` on a refused request.

## Coverage and limits

`changed_lines` still contains only actual added diff lines inside each selected
function's current span. An unchanged function therefore has an empty list.
Selecting it does not turn all of its lines into changed lines. Total coverage
can improve, while the changed-line population is zero and its percentages stay
unavailable. Unrelated or refused diff source paths are context only in explicit
mode and are never opened or added as targets.

This is a deliberate selection workflow. It does not infer dependencies, prove
that all affected functions were selected, or supply surrounding module values
that are absent from both the selected source and the supplied diff. A developer
must provide useful context and review the resulting tests. The existing
sandbox, generated-file preservation, model routing, token budget, execution and
patch contracts apply unchanged.

Receiving uses deterministic `ScriptedModel` responses with actual outgoing
message checks, subprocess tests and patch application. Those controls qualify
the workflow and context delivery; they do not establish live-model generation
quality.
