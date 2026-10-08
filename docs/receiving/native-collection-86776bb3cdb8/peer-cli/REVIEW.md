# Independent current-main CLI collection receiving

Accepted the receiver's helper correction with SHA256
`d65352d7bade965d7b9dc73efe5d4d01844fa8c7474a1bdcdb3b708f6decf768`
on actual main
[`269e55332a9bb78a0a0e107cbab6b2e5c895ca57`](https://github.com/Jacob-Met/testpilot/commit/269e55332a9bb78a0a0e107cbab6b2e5c895ca57),
tree `2045a73704f752d374704657fccf90fd5e774258`.

## Source review

Fresh primary Git objects were checked against all seven loaded TestPilot
Python files and the exact pyproject, test conftest and CI configuration.
Only `_pytest_generated.py` differs. `sandbox.py`, including the held
`run_pytest` span, is byte-identical, as are the current CLI, model, loop,
target selection and result-counting code. The helper's runner `main` and
generated JUnit provenance hook remain exact.

The correction keeps native root traversal and avoids the overlapping explicit
child argv that causes pytest 8.0 to omit the configured sibling. Its Session
collection-start hook restores the generated child's explicit-path status.
The native `search_pypath` call preserves named-module resolution and the
available namespace-package option. There is no item/nodeid deduplication,
replacement collector, result-schema change or interpreter substitution.
No actionable source defect was found. The receiver's separate 17-case native
compatibility matrix was not repeated here.

## Actual CLI and repair boundary

Both processes used `python -B -m testpilot run`, its maintained scripted
backend, the explicitly selected pytest **8.0.0** interpreter and its native
coverage integration. `PYTHONPATH` was pinned to each exact source copy;
the loaded module path and source hashes are retained in `run/receipt.json`.

The authored project has `testpaths = tests`, one existing contract for a
doubling function and a native conftest fixture. Generation supplies two
parameterized cases, initially with one incorrect expected value. Repair 1
makes those cases pass by mutating the module's multiplier, which breaks the
existing contract. Repair 2 removes that mutation and supplies the correct
expected values.

| Exact source | CLI result | Repairs used | Final cases | Consequence |
| --- | --- | --- | --- | --- |
| Current main, unchanged helper | Passed | 1 | 2 generated; existing contract omitted | Incorrect mutation remains in the accepted patch |
| Current main plus frozen correction | Passed | 2 | 1 existing + 2 generated | Existing failure forces the correct second repair |

The candidate's initial generation has one generated failure. Its first repair
has two passing generated cases but one failing existing case and cannot
qualify success. Its second repair has three passes, with `tests_written = 2`
and exactly two passing cases marked as generated. This checks the public
repair-stop decision as well as the lower-level collection result.

## JUnit and preservation

An authored project `pytest_unconfigure` observer only copies pytest's
completed XML before the sandbox removes its temporary directory. It does not
alter collection, execution, results or the TestPilot sandbox. All seven raw
JUnit reports are retained: three from the unchanged-main control and four
from the corrected CLI flow. The generated-file properties identify exactly
two cases per generated run, while the existing case remains unmarked.
The native fixture's separate property is present in every executed case.

Both complete native CLI reports, stdout/stderr, source manifests, authored
project, diff and four scripted responses are retained. Neither source copy
nor the original project changed, and no generated file was written into the
original project. No production source, owner branch or remote was edited.

`file-hashes.json` lists the compact transfer set and safe Python archive
names. Empty temporary directories, duplicate rendered reports and duplicate
patch copies are deliberately excluded. The raw `report.json` files already
retain each round's generated source, complete final patch and JUnit-derived
case results.

## Reproduction

Restore this driver as `receive-cli.py` beside `primary-source.json`, then run
it with the two exact source copies, a pytest 8.0.0 interpreter with coverage,
and a new output directory:

```sh
python -B receive-cli.py --main /path/to/exact-main --candidate /path/to/corrected-main --python /path/to/pytest8/bin/python --output /new/output
```

The source copies must match the recorded primary blobs and helper hash. This
is a bounded independent CLI gate; the full repository's hosted qualification
remains a separate publication gate.
