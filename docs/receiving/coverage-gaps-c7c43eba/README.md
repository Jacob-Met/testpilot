# Saved added-line coverage: version 5 source handoff

The reader identifies exact changed lines missing from a saved TestPilot report's retained final coverage. Version 5 repairs a Windows stdout bug: newline conversion could enlarge an accepted result beyond the documented 16 MiB output limit. The CLI now publishes the already-checked UTF-8 bytes directly.

**Disposition:** qualified source follow-up on the existing contribution branch. Pull-request and main integration remain held while their existing CI triggers would start GitHub Actions. Installation and runtime adoption remain separate.

## Use and maintained verification

From a checkout using Python 3.12 or later:

~~~sh
python3 -B -m testpilot.coverage_gaps --report saved/report.json --output gaps.json
python3 -B -m unittest discover -s tests -p 'test_coverage_gaps.py' -v
~~~

The output must be new and its parent must exist. Omit `--output` for the same UTF-8 JSON bytes on stdout. Both destinations use LF line endings, including on Windows. The API remains `analyze_report(report: dict) -> dict`, with `ReportError(ValueError)` for invalid or over-limit evidence. The [command guide](../../COVERAGE_GAPS.md) defines the full semantics.

Only retained final coverage supplies line states. Exact recorded labels remain distinct across case and slash variants and are never opened. Unique file/changed-line pairs are executed, missing, not represented or unknown. Unrepresented lines are not inferred to be excluded, non-executable, covered or safe to ignore.

Counts retain original function ordinals and empty changed-line records. The percentage concerns only changed lines present in retained executed/missing arrays; it is not project coverage. Unavailable counts and empty denominators remain null. The maintained synthetic fixture still has six unique lines: one executed, three missing and two unrepresented, yielding 25.0% among known executable lines.

## What changed

This follow-up starts from `b77d3868a63f8a596f916c7aa3177ec99f401e45`. It changes three previously owned product/document paths and these two derived handoff summaries. Publication requires a complete-tree audit that all other 1,500 parent leaves retain their exact paths, types, modes and Git blob identities.

The product change is two statements: write the admitted payload through `sys.stdout.buffer`, then flush that buffer. Analysis APIs, classifications, limits, integer-conversion handling, exclusive binary file creation and I/O error handling remain unchanged. No dependency, initializer, other CLI, coverage collector, source selector, workflow or unrelated owner's file changes.

A new maintained regression runs the actual stdout and file CLI forms and compares their raw bytes. The test subprocess helper adds `-S` to suppress unrelated site initialization while retaining its existing explicit `PYTHONPATH`, environment, working directory, timeout and byte capture. The entire original test file is recovered by removing that flag and the new regression.

Exact four-path fingerprints and all evidence references are in [PUBLIC_QUALIFICATION.json](PUBLIC_QUALIFICATION.json). The fixture is unchanged.

## Actual Windows qualification

All current Windows product runs used CPython 3.12.14. The active 4,300-digit integer-conversion setting stayed unchanged.

| Evidence | Actual outcome |
| --- | --- |
| Version 4 initial independent receiving | 3 API cases and 8 CLI cases passed: literal labels/ordinals/null counts, Unicode destinations, native case/hardlink/input aliases, create-only refusal, late invalid input and a real broken output pipe |
| Separately frozen version 4 size witness | Contract failure: the API admitted 16,777,197 LF bytes, but the CLI emitted 17,503,564 CRLF bytes and exited 0 |
| New regression against version 4 | The one method failed at raw stdout/file equality: 2,572 CRLF bytes versus 2,443 LF bytes; both actual CLI children exited 0 |
| Version 5 author gate | 17 methods and 9 joined CLI children; zero failures, errors or skips; author, monitor and outer wrapper exited 0 |
| Version 5 independent repair receiving | 4/4 actual CLI cases passed; target exits 0, 0, 120, 0; receiver and outer wrapper exited 0 |

The original Windows vector values were frozen before version 4 implementation exposure. Two adapter clarifications were recorded after source exposure but before execution: empty function records do not invent changed-line file groups, and the former “same JSON” wording established semantic equality rather than identical platform framing. The later physical-byte witness was separately frozen and is explicitly source-review receiving.

The size witness used a legal 3,632,470-byte input with 128 functions and 90,649 raw entries. Version 4's 726,367 inserted carriage returns put physical output **726,348 bytes over** the 16,777,216-byte ceiling. Successful evidence collection is not a product pass; this failure remains in its original packet.

Version 5's four expectations were frozen before its implementation or author tests were exposed. Small stdout and a new Unicode-path file both match the original 3,998-byte binary-file gold. The same near-limit case physically emits **16,777,197 bytes**, matching the independent LF hash and remaining 19 bytes below the limit. A real closed anonymous stdout still produces nonzero exit 120. Full actual CLI stdout was not retained as an artifact: collection kept its count, SHA-256 and 128-byte prefix/suffix. Expected LF/CRLF byte oracles were computed in memory, and the API materialized its admitted result bytes.

## Source review and custody

A separate post-receiving peer reviewed the exact source delta and author evidence without rerunning tests. It verified 16 original Git-exact files, the 12 unchanged package dependencies, the unchanged fixture, all 27 author stream/output pins (11 stdout, 11 stderr and five saved output files), and the actual author closures. Inverse transformations recover the original module, tests and guide exactly. Its result is clear within this narrow scope.

| Closed native packet | Native files / ZIP members | Archive bytes | SHA-256 |
| --- | --- | ---: | --- |
| Version 5 author evidence | 115 / 116 | 237,013 | `fc19790d2f6fcc487180169678591f03247574a0c805839b8954de54c20945be` |
| Version 4 Windows receiving and negative | 91 / 92 | 401,994 | `927691749b6db1645ff4d5c1dca6d698f9aeef9e7fc89eb5188b821b2951e0e9` |
| Version 5 focused Windows receiving | 43 / 44 | 101,339 | `61e2e8b9042b84db1724b7c30a9ea2a4310ce2fde91eb7f0028e62333e1fa0e6` |

Native bytes, modification times, ZIP membership and CRCs were checked. Root independently verified both receiving packets without repeating product runs. The old Windows sealer and later source-peer collector lost their outer sessions, so those outer numeric exits remain unknown; the verified artifacts and actual product/receiver exits are recorded separately. The version 5 receiving sealer's outer exit is 0.

The Windows author and combined receiving budgets remain 16 MiB each, with a 64 MiB disk reserve and 1.5 GiB available RAM floor. No floor was lowered. Original native packets and runtime paths remain in private estate custody. These public documents are newly derived summaries.

## Prior evidence and preserved failures

The [exact previous summary](https://github.com/Jacob-Met/testpilot/blob/b77d3868a63f8a596f916c7aa3177ec99f401e45/docs/receiving/coverage-gaps-c7c43eba/PUBLIC_QUALIFICATION.json) preserves version 4's Linux/Python 3.14.4 author gate, 122 original independent observations, the before-parser input refusal and two integer-conversion follow-ups. The final version 4 Mac attempt stopped at its memory floor before source writes or execution.

Earlier fixture-count, Mac API-bound and integer-conversion failures remain tied to their exact versions. The Windows oracle-preparation stops, version 4 physical-byte failure and the new version 4 regression failure are also retained. Prior Linux/Mac receipts are not presented as version 5 runtime evidence.

## Integration boundary

The existing 586-byte `ci.yml`, blob `86a3236e38155506b5fe6077322d508f7f676649`, triggers on pushes to main and on pull requests. Updating the existing non-main contribution branch is eligible only while its complete workflow inventory and absent PR association are freshly verified; exact source/ref and run-count readback follow publication.

Opening a PR or merging main remains held. An unrun required gate is not a pass. This handoff does not claim a full-repository pytest/Actions result, version 5 Linux/Mac qualification, deployment, installation or canonical adoption.
