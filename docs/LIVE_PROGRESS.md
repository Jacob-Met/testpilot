# Live generation progress

Add `--progress` to an ordinary run to see what is happening before its final
report is ready:

```sh
python -m testpilot run --repo ./project --git-base HEAD \
  --backend scripted --script ./responses --out ./review --progress
```

Progress goes to stderr and is flushed at each phase boundary. Normal stdout and
saved JSON, Markdown, HTML and patch formats are unchanged. Omitting the flag
keeps the existing quiet execution. It is supported by `run`; other commands
retain their existing behavior.

Typical notices include:

```text
[testpilot] Baseline pytest: running
[testpilot] Baseline pytest: finished: 8 passed, 0 failed, 0 errors, 0 skipped (rc=0)
[testpilot] Planning tests: starting
[testpilot] Planning tests: completed
[testpilot] Generating tests: starting
[testpilot] Generating tests: completed
[testpilot] Generated pytest: running
```

A repair emits `Repairing tests` and another generated pytest phase. Native
completion reports the returned counts and return code; a timeout or unavailable
JUnit is identified explicitly. These notices are observations, not an extra
test-success verdict. The final report remains authoritative.

Starting a model phase means the loop entered that phase; budget and routing
checks still happen before any underlying model call. A missing completion line
can mean the phase is still running or ended by an error or interruption. There
is no periodic heartbeat or per-test streaming. The normal timeout, cancellation,
retry, token-accounting and model/test invocation behavior is unchanged.

Notices contain fixed phase names and native result counts. They do not include
prompts, generated source, project paths, model response bodies or provider
configuration. If stderr is absent, progress is disabled without falling back
to stdout. If the optional destination refuses a write or flush, progress is
disabled for that pilot and the failed stream is closed best-effort to avoid a
later buffered shutdown failure. The underlying operation continues. Normal
Python cancellation still propagates.

The Python API may construct `testpilot.progress.ProgressTestPilot` with the same
arguments as `TestPilot`. It delegates the existing loop methods and writes to
the current `sys.stderr`.
