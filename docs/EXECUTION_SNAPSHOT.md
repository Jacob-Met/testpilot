# Captured project execution

A generation run uses one captured project input for its selected function source,
model prompts, baseline pytest run, generated-test run, and repairs. Every pytest
phase still executes in its own fresh disposable sandbox.

This keeps a caller's edit during a model response from silently changing the code
being tested. For example, if the selected function returns `2` when captured and
the caller later changes it to return `7`, generation and repair still execute
the captured function returning `2`. The report describes that captured input.
The caller's edited file remains untouched.

## Selection and execution

TestPilot first captures the project using the sandbox's existing ignore policy.
It then resolves changed functions or explicit targets and builds the model
context from the private captured view, before running the baseline. Reading the
supplied diff to identify source paths does not read function bodies.

Source selection retains link identity. A selected source link resolving outside
the repository is still refused; internal aliases retain canonical
deduplication. Internal links are rebound into the private view so that later
caller edits do not change the admitted source. Referenced internal targets
omitted by the normal ignore patterns are retained when needed to preserve the
existing source admission and link behavior. This does not turn ignored
directories into additional pytest collection roots.

After source admission, TestPilot materializes a stable execution template using
the sandbox's existing copy and ignore behavior. Each baseline, generation, and
repair phase copies that template into its own worktree. Writes made by a pytest
hook or test in one worktree do not become input to the next phase.

Readable source directories can be read-only. During construction, TestPilot may
temporarily add write permission to directories in its own private selection
copy to recreate their links or fill a referenced target. It restores those
copied directory modes before execution. It does not change the original
directories or chmod through their links.

Temporary selection and execution copies are removed when the run returns or
raises, including model failures and interruptions.

## Existing tests and the caller's checkout

Generated tests remain additions. Path and pytest module-name reservations check
both the captured input and the caller's current checkout. If the caller deletes
an existing test while model work is in progress, that test remains in the
captured suite and its name stays reserved. If the caller creates a conflicting
path, the existing allocation and final addition checks still protect that path.

The generated patch does not include the captured project or the caller's edits.
A result applies to the captured input. Applying its patch to a subsequently
changed checkout may produce a different test outcome; run TestPilot again when
you want a result for those later edits.

## Boundaries

The initial capture is a finite filesystem copy, not an atomic filesystem
snapshot. Changes while that initial copy is in progress can produce a mixed
input. Once the template is materialized, later generation phases reuse its
project bytes.

Links to external data keep the sandbox's normal materialization behavior and
are copied into the execution template after source admission. Prepared Python
interpreters, installed packages, files accessed outside the copied project, and
external services are not frozen. This feature does not create a security
boundary around project code.

The additional private selection view and execution template require temporary
disk space. Existing per-pytest timeout and process handling remain unchanged.
No new command-line option, report schema, or recheck behavior is introduced.

## Focused verification

`tests/test_execution_snapshot.py` exercises actual pytest runs with scripted
model responses. Its fixtures cover both directions of source drift, an
unselected dependency, repair, per-phase writes, cleanup, existing-test
reservations, internal aliases, ignored targets, external data links, and source
admission. The separate receiving driver reproduces the CLI drift case and
applies the exact emitted patch to the initially captured checkout.

Historical source pins, raw baseline outcomes, and the qualification boundary for
each candidate are recorded under
`docs/receiving/execution-snapshot-f5c43297f890/`.
