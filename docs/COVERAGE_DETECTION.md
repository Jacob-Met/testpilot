# Optional coverage detection

With automatic coverage enabled, TestPilot checks whether the selected Python
interpreter can import `coverage` before it copies the project and starts pytest.
That check now has a five-second subprocess timeout. If the import fails or
times out, TestPilot proceeds without optional coverage measurement. The probe's
stdin is closed and its unused output is discarded.

Successful and unsuccessful detection keep the existing cache per interpreter
for the lifetime of the current TestPilot process. After repairing an interpreter
or coverage installation, start a new TestPilot process to detect it again.
An interpreter that cannot be started still raises its original operating-system
error; this change does not turn an unusable Python command into a usable runner.

The probe limit is separate from `run --timeout`, which bounds the test
subprocess. Subprocess creation itself is subject to the operating system, so
this is not a whole-command wall-clock deadline. The timeout kills and waits for
the directly launched probe; it is not containment for hostile imported code or
detached descendants.

`run --no-coverage` and the API's `coverage=False` continue to skip detection.
The API's explicit `coverage=True` also skips detection and requests coverage
directly. Pytest outcomes, JUnit handling, coverage-report generation and saved
report formats are unchanged.

The focused regression suite uses real Python child processes with temporary
coverage-import fixtures, including a slow import and noisy output. Run it with:

```sh
python -m unittest discover -s tests -p test_coverage_probe.py -v
```

The temporary import fixtures are test inputs, not a substitute coverage package
or a claim of running the installed coverage/pytest tools.
