# Query the TestPilot package version

Use the top-level version option with the Python environment that runs TestPilot:

```sh
python -m testpilot --version
```

For the current public package version, stdout is exactly:

```text
testpilot 0.1.0
```

The command exits 0 and requires no subcommand, repository, diff or backend.
An installed `testpilot` console command uses the same `main` entrypoint, so its
corresponding syntax is `testpilot --version`. Use the top-level option before
a subcommand; ordinary command requirements remain unchanged.

The value comes from the existing `testpilot.__version__`. It is the package's
public version, not a Git commit, a working-tree fingerprint or proof that two
installations have identical source. This addition does not bump that version.

The ordinary package imports still occur. Argument parsing then prints the version
and exits before diff acquisition, client or routing construction, generation,
project test execution or report publication. No backend or price configuration
is needed for the query. `--help` now lists the option; omitting both the option
and a command retains the existing command-required error.

## Source and receiving

The production change is exactly two additive lines in `testpilot/__main__.py`:
import the existing package version and register argparse's version action.
The package metadata, version declaration, all other production modules and
existing command bodies remain unchanged.

Qualification used Linux and CPython 3.14.4 with source pinned to
`11f4d6c42621bb6b26159726641a19bbd7aa086b` plus those two lines.
The complete original CLI query was received before the candidate: it exited 2
with empty stdout and the command-required diagnostic. Existing help succeeded
and the missing-command control exited 2.

The three new version tests failed against the unchanged original, then passed
with the candidate. The focused candidate course also ran the unchanged target
preview and timeout test modules: **25 tests and six unittest subtests passed**,
with no failures, errors or skips. The JUnit suite attribute reports 31 because
it includes those subtests; it contains 25 collected-test elements. This is a
focused course, not a full-repository test-suite result.

The actual module query also passed from an unrelated directory with a local
test-loading sentinel, deliberately invalid backend/prices and exact local file
preservation. Direct-entrypoint tripwires verified that the query did not enter
diff, client, routing, runner construction or output publication. Existing
native target inspection and authored scripted-pytest controls passed. All
staged source/fixture bytes remained exact after qualification.

[The portable receipt](qualification/cli-version-20261013/receiving.json)
preserves source identities, commands, timings, original and candidate results,
raw pytest/JUnit streams and the initial staging failure. That first oversized
command was rejected with `spawn E2BIG` before execution; supported file
transfer then staged the pinned inputs successfully.

No external provider request, installed-package replacement, hosted execution
or deployment was performed. The console-entrypoint statement above follows
the unchanged `pyproject.toml` entrypoint; the actual native commands used
`python -m testpilot` and the same direct `main` function.

## Publication composition

Publication is based on `ef519fe6e302259f5bed0032427c5cd27eace0e4`, which
adds only the independently reviewed README platform clarification from PR113.
Complete tree comparison confirms that all production, test, fixture,
configuration and workflow inputs are unchanged from the qualified base.
This version change preserves that accepted README exactly; no additional
runtime execution is attributed to the documentation-only base advance.
