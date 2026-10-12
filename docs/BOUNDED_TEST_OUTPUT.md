# Bounded test output on POSIX

On Linux and macOS, TestPilot continuously drains the test process's combined
stdout and stderr while retaining only the final **256 KiB of raw output**.
Large print loops can finish or reach their ordinary test deadline without
requiring the parent runner to hold every diagnostic byte in memory.

Output below that limit keeps its existing decoding and newline behavior. When
earlier bytes are discarded, the retained output starts with a marker such as:

```text
[testpilot: omitted 1048576 earlier output bytes]
```

The tail still contains the final diagnostics. A retained range that begins
inside a multibyte character uses replacement characters at that incomplete
boundary, as it already does for invalid or interrupted output. Saved reports
and repair prompts retain their existing, smaller diagnostic-tail limits.

Normal exit codes, native pytest/JUnit results, and coverage results still
determine the run's outcome. The same wall-clock timeout, process-group kill,
one-second POSIX post-kill collection budget, and Ctrl+C cleanup apply. An
escaped helper retaining the pipe does not extend that collection budget.

This bound applies to TestPilot's POSIX pipe collection. A test's own memory,
pytest's internal capture, generated files, and JUnit diagnostics have their
separate existing behavior. Windows keeps its existing reader implementation.

## Verify

Use the project's Python environment with pytest and optional coverage installed:

```sh
python -m pytest -q tests/test_sandbox_output.py tests/test_sandbox_deadline.py tests/test_sandbox_interrupt.py tests/test_sandbox.py
```

The output tests exercise real child processes, byte-limit boundaries, final
diagnostic retention, memory allocation, timeout/recovery, early pipe closure,
UTF-8 truncation, and an ordinary noisy pytest run with its native JUnit result.
The existing deadline suite exercises detached pipes. The interruption suite
uses child-authored file challenges and native reaping observations; see
[portable interruption receiving](INTERRUPTION_RECEIVING.md) for its scope and
limits.
