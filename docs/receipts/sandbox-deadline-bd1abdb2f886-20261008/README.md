# Bounded POSIX timeout output collection

TestPilot's original timeout handler kills the target process group, then calls
`communicate()` with no deadline. A detached helper can retain the stdout pipe
after that group dies. The caller then waits for the helper's EOF instead of
returning a timeout result. An incomplete UTF-8 character can also turn timeout
reporting into `UnicodeDecodeError`.

The change gives the POSIX post-kill `communicate()` call a **one-second output
drain budget**. If the pipe remains open, it returns the bytes already captured,
replaces incomplete/invalid encoded characters, normalizes newlines, closes its
pipe reader and polls the killed leader. Normal output, return codes, process
group signaling and the public `SandboxResult` interface remain supported.

This is a drain deadline, not an unconditional wall-clock guarantee for process
creation, OS scheduling, copying a repository, coverage setup or other work.
It does not kill or contain helpers that escape the target process group. The
receivers own and explicitly clean up their detached helpers. The existing
Windows reader-thread drain path is retained; the new detached-process receiving
cases explicitly require POSIX. Invalid captured text is now represented with
replacement characters instead of aborting result collection.

## Exact source

Differential baseline: `feea1889358b570d652f456ce5b63e853ba47d47`, tree
`435b9278205d9535883ed0e49c533ed3fdeeb05e`. All 90 baseline files were recovered
and checked by Git blob identity. Only `testpilot/sandbox.py::_run` changes at
runtime; the regression module and this directory are additive.

Before publication, the independent source-containment contribution merged to
main at `bc095b47f65805079ee4e9ef97971347fcdfbaa5`, tree
`b3d6bfa31fb02e774e15027e9a62fcdf84763ef0`. Its four changed/new files were
materialized by exact blob identity. All 92 current-main leaves then matched,
apart from the scoped sandbox change. The combined suite was rerun on that
publication base: **91 passed, zero skips**. No source-containment/CLI files are
part of this patch.

| Identity | Git blob |
| --- | --- |
| Original sandbox | `68e14602058608ca86a218e39053249f1891f95e` |
| Reviewed candidate sandbox | `5f96a359d9e23c7b474cda7b23d3360de3dcf748` |

Candidate runtime SHA-256:
`f37cffae5cd8b8b527bd41ac6a9eb6dba0715e0bc6cb95684ac7964339eb10b3`.
The root source reviewer accepted this exact implementation and supplied the
independent continuous-output witness below. Source integration is separate from
installed-estate adoption; no provider or shared service was used.

## Receiving results

Native Linux, Python 3.12.14, pytest 9.1.1 and coverage 7.16.2:

| Check | Original | Candidate |
| --- | --- | --- |
| Six new real-process cases | 2 pass, 4 fail | 6 pass |
| Complete repository suite on publication base | Baseline differential only | 91 pass, zero skips |
| Actual generate/timeout/repair workflow, first timed-out pytest round | 6.182 s | 2.004 s |

The four failing controls were authored before runtime editing and remain
unchanged. They cover a waiting parent, an already exited parent, a truncated
multibyte diagnostic, and an actual default `run_pytest` call. Normal combined
stdout/stderr, nonzero status and empty timeout output are controls. The already
passing normal-text case was changed from explicit UTF-8 bytes to ASCII for
locale portability; the original and candidate were then rerun with identical
final test bytes. The real pytest case also checks a later fresh successful run
and unchanged source files.

`check_repair_workflow.py` exercises the unchanged TestPilot loop using three
authored ScriptedModel replies and actual pytest processes. Both versions finish
with one repaired generated test and two passing tests; the candidate reaches
repair after its bounded output drain. Both patches pass `git apply --check` and
leave the input repository unchanged. The observed total durations, 6.651 and
2.425 seconds, describe these authored runs and are not a performance guarantee.

The independently authored `continuous_output.py` keeps a detached helper
actively writing throughout cleanup. The reviewed candidate returned a timeout
in 1.402183 seconds for a 0.4-second execution deadline, retaining the parent
diagnostic and 135 contiguous, nonduplicated helper lines. The helper was still
alive until the receiver cleaned it up. The unchanged witness and its exact
native output are included; this tests a total drain deadline while bytes keep
arriving.

## Replay

From an isolated checkout with the project's pytest/coverage dependencies:

```sh
python -m pytest -q tests/test_sandbox_deadline.py tests/test_sandbox.py
python -m pytest -q
python docs/receipts/sandbox-deadline-bd1abdb2f886-20261008/check_repair_workflow.py . /tmp/deadline-workflow.json
python docs/receipts/sandbox-deadline-bd1abdb2f886-20261008/continuous_output.py testpilot/sandbox.py
```

To reproduce the baseline differential, make a separate checkout at the baseline
commit, copy only the new regression module into its tests directory, and run
that module using the same interpreter. Pass that checkout to the workflow
witness for the baseline workflow. The four expected baseline failures and final
candidate suite output are preserved here. `receipt.json` binds the source and
evidence files to their SHA-256 and Git blob identities.

Python documents the captured bytes and timeout behavior in
[subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate).
Coordination: [existing issue #2, comment6055917934](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6055917934).
The loop preservation, source containment/CLI and separate CI contributions keep
their existing scopes.
