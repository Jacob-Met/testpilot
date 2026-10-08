# Coverage measurements and configured thresholds

TestPilot reads coverage from the sandbox's actual Coverage.py JSON report.
A project's `[report] fail_under` threshold can make `coverage json` exit with
status 2 even when it wrote a complete, valid measurement. TestPilot retains
that report, including its executed and executable lines, so the before/after
comparison uses the measured percentages.

For example, a baseline at 75% followed by a generated-test run at 100% is a
25 percentage point improvement even when the project's threshold is 100%.
A measured zero remains numeric zero and retains its executable-line population.

Each JSON report is requested in a newly reserved directory after pytest has
finished. A file left at the old report path is not reused if the reporting
command fails. A missing report, a reporting failure with another exit status,
or a reporting timeout remains unavailable instead of becoming a synthetic
zero. The existing parser still reports malformed producer output as an error.

Coverage availability and test outcome remain separate. Successful tests can
have unavailable coverage; failed tests remain failed when a below-threshold
coverage report is readable. The existing loop only computes a before/after
delta when both measurements are available. JSON uses `null` for an unavailable
measurement or delta, and Markdown says `Coverage: unavailable`.

This preserves the existing pytest and repair-loop policy. The project's
coverage threshold is not a new TestPilot pass/fail gate.

## Reproduce the receiving controls

Use the project's Python with pytest and the optional `coverage` dependency
installed:

```bash
python -m pytest -q tests/test_coverage_reporting.py
```

The controls run real local pytest/Coverage.py processes and the public
ScriptedModel CLI. They use authored temporary projects, preserve the original
input files, and exercise a real plugin exit before report generation. They
require no model-provider call.

## Primary reporting contract

Coverage.py documents status 2 for a total below `--fail-under`, and supports
the same setting in its configuration files:
[JSON reporting documentation](https://coverage.readthedocs.io/en/latest/commands/cmd_json.html)
(read 2026-10-08). The exact installed version and source hashes used in
receiving are recorded with the contribution's evidence.
