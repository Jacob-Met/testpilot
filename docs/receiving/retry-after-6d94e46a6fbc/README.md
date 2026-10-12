# Provider Retry-After receiving

This contribution makes TestPilot respect a provider's requested retry delay while keeping the existing retry statuses and attempt budget. It implements [issue #83](https://github.com/Jacob-Met/testpilot/issues/83). The consumer contract and examples are in [PROVIDER_RETRY_AFTER.md](../../PROVIDER_RETRY_AFTER.md).

The reviewed code reads nonnegative ASCII integer seconds or an HTTP date, including the legacy date spellings and rolling fifty-year rule. An admitted wait uses the greater of the provider delay and the existing exponential backoff. Provider guidance above 120 seconds stops with a targeted `ModelError`; it does not retry early or sleep indefinitely. Failed HTTP responses close before waiting or refusing. No new configuration is needed.

## Source and current composition

The three maintained files are `testpilot/model.py`, `tests/test_model_retry_after.py`, and `docs/PROVIDER_RETRY_AFTER.md`. Their exact identities are in [source-manifest.json](source-manifest.json). [reviewed-source.patch](reviewed-source.patch) contains only those three files.

The publication parent is `e222894c095e16aff19413e6e3f8a2b6201a059a`, after the baseline-runner admission and literal-safe verdict contributions. Every existing file in the 109-file executable/test projection matches that parent except the reviewed model change; the projection includes every current TestPilot module and test file. The Git tree builds on all 1,524 existing leaves, replacing only the reviewed model blob and adding the other two maintained files plus this packet. [current-projection-manifest.json](current-projection-manifest.json) records the projected bytes.

The model, new tests and guide remain byte-for-byte the files accepted by the independent reviewer. No source in the baseline, verdict, routing, scripted-input or response-decoding scopes is changed by this contribution.

## Executed evidence

| Check | Source composition | Result |
| --- | --- | --- |
| New tests against original model | `52275f5` plus the new test file | 17 failures; 14 compatibility controls pass |
| Maintained model and HTTP tests | Candidate on `52275f5` | 55 pass; 8 subtests pass |
| Full maintained suite | Candidate on `52275f5` | 574 pass; 33 subtests pass; 2 failures |
| Exact full-suite failing cases | Untouched `52275f5` | The same 2 failures reproduce |
| Baseline-runner composition | Candidate on `86617fc` | 75 pass; 15 subtests pass |
| Current baseline and verdict composition | Candidate on `e222894` | 128 pass; 15 subtests pass |
| Independent public-API receiver | Exact frozen model | 52 pass; original gives 28 passing controls and 24 expected failures |

The two full-suite failures concern whether an intentionally detached child is still running in this environment. The identical untouched-source failures are retained in [author/original-interrupt.log](author/original-interrupt.log), alongside the full candidate output. They are not suppressed or counted as passing. The current-parent result is the affected 128-test composition check, not another full-suite run.

The new maintained tests exercise a real local HTTP server through `urllib` and the actual CLI. One path recovers from a 429 response and produces passing generated tests. The other refuses a 503 response's 121-second delay during repair, makes no further request, and retains the completed work in its patch and JSON/Markdown/HTML error reports. Sleep is injected so these tests assert the selected delays without waiting or contacting a model provider.

The separate reviewer prepared a public-API receiver before the candidate was frozen. It checks all three date formats under a non-UTC timezone, the obsolete-year rule, cap boundaries, huge and zero-padded integer inputs, malformed values, all retry statuses, exhausted and terminal controls, request and usage preservation, and response lifetime. Its [accepted review](independent/INDEPENDENT_REVIEW.md), original and candidate observations, exact harness and preparation receipt are retained together.

Commands, exit codes, source parents and output links are in [qualification.json](qualification.json). The author used Python 3.12.14, pytest 9.1.1 and coverage 7.16.2 in an isolated virtual environment. To rerun the current combined check from a checkout with those dependencies:

```sh
python -m pytest -q tests/test_model_retry_after.py tests/test_model.py tests/test_model_timeouts.py tests/test_model_retry_lifetime.py tests/test_model_error_detail.py tests/test_baseline_runner_admission.py tests/test_loop.py tests/test_verdict_boundaries.py
```

## Publication boundary

The sole current workflow is `.github/workflows/ci.yml`, blob `86a3236e38155506b5fe6077322d508f7f676649`. It selects pushes to `main` and pull requests; an isolated feature-branch push has no matching trigger. The source contribution uses that non-triggering branch path. This packet does not claim a merge, installed adoption, external-provider execution or a wholly green maintained suite.
