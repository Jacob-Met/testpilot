# Preserve literal test content through verdict parsing

[TestPilot #55](https://github.com/Jacob-Met/testpilot/issues/55) repairs a concrete failure in the native generation/repair workflow: a corrected test containing `VERDICT: CODE_BUG` was read as a diagnosis before it could execute. The earlier failing patch was retained even though the model supplied a valid repair.

Only `parse_verdict` changes in production. It requires an explicit uppercase, same-line header in prose and the complete `CODE_BUG` token. Fenced examples and unfinished fences remain text. An actual verdict still keeps the previous failing tests. The generated-file parser, placement, sandbox, model client and other loop behavior are unchanged.

## Source to compose

Use base commit `906ce149fba770a62c9f5f2fbc1b7238b949d423`, tree `626557015edc297dfc6ba00028a8de64f7dfdfa9`. It contains PR51's paired-regression capability. These are the final offered blobs:

| Path | Git blob |
| --- | --- |
| `testpilot/loop.py` | `b9ba4870f9dd0a373fb48b94434656540251a15c` |
| `tests/test_verdict_boundaries.py` | `89ca8b5801d985ca3058f08510e03981862dbd56` |
| `README.md` | `8b618f404447afc564ee6aa54fafb063e6ca2a9c` |

The current README preserves the incoming owner's text. The earlier author packet contains its older e114 README solely as historical evidence; it is not the README to compose. Exact inverse checks recover both current original production module and README.

## Separate qualifications

| Receiving | Exact scope | Result |
| --- | --- | --- |
| Original actual CLI witness | Unchanged e114 source, three ScriptedModel/native pytest runs | Literal-bearing repair wrongly reports suspected bug; ordinary repair and actual verdict controls retain their expected outcomes |
| Author new controls | Unchanged e114 source, 53 tests | 38 failures, 15 controls pass, no errors or skips |
| Author candidate plus maintained compatibility | Offered loop/tests on e114, 53 new plus 61 maintained tests | 114 pass, including all five existing scripted eval cases |
| Root independent oracle | 27 expectations frozen before candidate exposure; exact maintained method | Original fails 17 and preserves 10 controls; candidate passes all 27; bytes outside the method are exact |
| Current composition | Full current 19-file closure on 906, new 53 controls plus incoming paired-regression owner's 20 tests | 73 pass; all 17 unowned materialized inputs and candidate files remain exact |

Separate candidate CLI receiving retains each exact input, all four saved outputs and the full process result. The literal-bearing repair produces one actual generated pass, and its patch passes `git apply --check`, applies exactly to a separate project copy and passes native pytest. The ordinary repair remains passing; an explicit code-bug verdict remains a failed-test diagnosis with its original failing patch.

Execution used Python 3.12.14, pytest 9.1.1, coverage 7.16.2 and Git 2.51.1 from existing read-only dependencies. Bytecode writes and plugin autoload were disabled. Dependency metadata and source hashes remain unchanged. All fixture/project/output mutations were confined to private `/dev` processes; no dependency installation occurred.

## Durable evidence

- `original-witness-envelope.json`: original three-CLI source/witness packet, 99,411 decoded gzip bytes, SHA-256 `c363f1c55dfd24768eb6f0ce0725f12410c8228a25da6017f3bc399a5e61df1a`.
- `author-receiving-envelope.json`: 54-file author packet, 215,335 decoded gzip bytes, SHA-256 `883d5864a72258b696b0d36ebc35e22086a39bf5a3b3dd31f8b833edc9472b73`.
- `current-composition-envelope.json`: 16-file current addendum, 158,607 decoded gzip bytes, SHA-256 `baab6d32d637e0f05966eb81aa78fbaceddead6de6bf84d40497bea6551bab49`.
- `independent-root-receiving.json`: all 27 frozen oracle inputs, expected/actual results, source identities and method-only byte proof.
- `source-manifest.json`: immutable source/base/workflow pins and expected custody changes.

Each envelope is UTF-8 JSON. Base64-decode its `content`, verify the gzip bytes against `sha256`, decompress and parse the JSON `files` map. The author/current packets include raw process logs, JUnit, caller inputs/outputs, source fixtures, member hashes and standalone receiving launchers. Those launchers were compiled and their source reconstruction checked. The initial rejected JavaScript template and original failures remain preserved.

Current tree/workflow/source readbacks are exact. The sole workflow, `.github/workflows/ci.yml`, stays at blob `86a3236e38155506b5fe6077322d508f7f676649` and triggers on pushes to main and pull requests. [HAMON #140 scope](https://github.com/Jacob-Met/hamon/issues/140#issuecomment-6068597101) retains source ownership.

The Actions publication pause remains in force. This qualification makes no complete-current-repository-suite, hosted CI, live model quality, installed-adoption or deployment claim. Root owns the final tree/ref and later publication gate. Source capture #50/#53, report downloads #47, history #39 and comparison #26/#33 retain their owners; paired-regression #51 is preserved exactly.
