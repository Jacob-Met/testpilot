# Fix an unavailable baseline runner before generation

TestPilot runs the project's existing suite before asking a model to plan or
write tests. If that baseline cannot produce a complete JUnit report, generation
now stops immediately with a failed result and the baseline's original runner
diagnostics. It makes no planning, generation or repair model calls and creates
no generated patch in this case.

For example, selecting a Python interpreter without pytest produces a failed
report that retains `No module named pytest` and records zero model calls. Use
an environment with the project's required dependencies before running again.
The same boundary applies to a timeout or abnormal process exit without a
complete report. This check uses the existing baseline execution; it adds no
extra interpreter or dependency probe.

A baseline containing ordinary failing tests can still have a complete report.
TestPilot continues to generation in that case, as before. A normal empty pytest
suite also produces a complete report and remains eligible for generation.
This change does not require the existing suite to pass before generating tests.
The existing selected-baseline pytest usage-error message remains unchanged.

The failed baseline is retained in the existing final-result field. It is not
compared to itself for a coverage delta. Report schemas, source selection,
scripted response loading, model construction, and output filenames are
unchanged. A source diff selecting no functions still skips both the test runner
and the model.

This change handles the runner's existing `junit_available` result. It does not
repair malformed XML parsing, install dependencies, validate model credentials,
or prove that every later test execution will succeed.

Run the focused tests without third-party dependencies:

```sh
python -m unittest discover -s tests -p test_baseline_runner_admission.py -v
```

The native missing-pytest checks create an isolated temporary virtual environment
without pip or system site packages; they do not install anything. They exercise
the real API and CLI with a scripted model. Other controls supply explicit
baseline results to check that failed and empty complete suites, usage errors,
coverage reporting and no-change behavior retain their intended meanings.
