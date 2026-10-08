# Model response timeouts

A stalled response could terminate TestPilot before it wrote a result or
reports. Native urllib can raise `TimeoutError` directly after response
headers arrive. The original client caught HTTP/URL errors only, so that
timeout bypassed both its retry policy and the loop's `ModelError` receiver.

The first candidate repaired that path. Independent receiving then confirmed
a second existing boundary: reading a terminal HTTP error's diagnostic body
could itself time out inside the HTTPError handler. Both the original and
first candidate leaked that exception and left the CLI without output files.

## Repair and behavior

`OpenAICompatClient.chat` handles direct transport timeouts through the
existing shared retry counter and backoff. Exhaustion raises a chained
`ModelError`. A timeout while reading a terminal HTTP error body instead
retains the known HTTP status, reports that its body timed out and closes the
terminal response. It does not restart the request budget or turn HTTP 400
into a retryable status.

The existing loop can consequently write its normal error result, including
any failing generated-test patch retained from earlier rounds. HTTP status
policy, routing, successful response parsing and reported usage are unchanged.
No CLI, loop, sandbox or provider configuration source is changed.

[Source ownership](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6056997400)
covers this one handler, its regression module and these compact receipts.
The first published candidate remains in commit
`320dcdfe88a85f7495d5fc90e39bf6f5e41058b5`.

## Exact source

| Material | Identity |
| --- | --- |
| Initial tested main | `981eb6c1cc6765c922f2e1fc394b9e28499c5440` |
| Final receiving base | `f350150259c00dd25c43a95d65157022612d15a8` |
| Original model Git blob | `20294ab3ad529b142ae955e1c4bc0ce71f87ae8b` |
| First candidate SHA-256 | `7d09afbb738f349a04756a9b69559b3bfabfe096e632409a80563b0dac635547` |
| Final model Git blob | `6d4abca38cc1c256df00bcac7923e2dc0bd42b16` |
| Final model SHA-256 | `f6ae697f1f5d686ffdcb96f5451d1a9600d7d41c7bcf324d7e8c276a107e8673` |
| Final regression SHA-256 | `9a5160e63970c39081770e0d35ea0a7dc85a45fb2fd03bdd66aef8e1aef95f9c` |

The final native composition includes the integrated match selector, project
Python CLI and current runner. Their five unmodified module pins are recorded
with the final candidate.

## Native results

CPython 3.14.4 / pytest 9.0.2, authored HTTP fixtures bound to `127.0.0.1`:

| Check | Observed result |
| --- | --- |
| Initial eight new cases on original source | Six failures / two inherited-behavior passes |
| First candidate, eight new plus seven existing model cases | 15/15 |
| Added terminal-body cases on unchanged first candidate | HTTP 400 and exhausted 503 both fail with bare TimeoutError |
| Final current-source composition, ten new plus seven existing model cases | **17/17**, zero skips/errors |

Tests cover body-stall recovery, zero/exhausted retries, budgets shared across
HTTP and timeout failures, terminal HTTP status retention and unchanged
unrelated exceptions. The original eight test assertions are retained.

Two controls execute the real CLI entrypoint, loop and native pytest, injecting
only a local urllib client and short read timeout. Recovery after a
planning timeout yields exit 0, two generated tests plus one existing test
passing, and a Git-applicable patch. Exhaustion during a later repair yields
exit 1 and `model_error`, with the failing-test patch and JSON/Markdown reports
retained. Original source and existing tests remain unchanged.

## Independent receiving

The separately assigned reviewer accepted the final candidate after the
**unchanged four-method receiver passed 4/4**, zero skips/errors, on the exact
integrated source. Both original and first-candidate controls had one pass
and three failures. The retained complete-body HTTP 400 control passed in
every version.

The independent server sends a partial error body before stalling. HTTP 400
now produces `ModelError` with its HTTPError cause after one request and no
backoff. An exhausted HTTP 503 keeps two requests and delay `[2]` for the
reviewer's one-retry configuration. Its real current CLI explicitly exercises
`--python`, returns exit 1 / `model_error`, writes all three output files and
preserves input source, with no leaked exception. These four cases remain
separate from the author's 17-case model selection.

[Independent executable](independent_review.py) SHA-256:
`59ea8a59bbfe3e3fde97863589df243326fda6960d0eee909d3fa2c352f01ae2`.
[Compact independent results](independent-results.json) preserve all three
source identities, the original findings, final observations and raw-receipt
hashes. Replay the unchanged executable with a source checkout directory and
an output JSON path as its two arguments.

## Repeat and retained history

```bash
python3 -m pytest -q tests/test_model.py tests/test_model_timeouts.py
```

[results.json](results.json) retains the initial witness and qualification.
[revision-results.json](revision-results.json) records the two newly exposed
first-candidate failures, final commands and source pins. The unchanged
independent executable and compact observations are retained alongside them.
The exact original and first candidate source remain in Git; no copied
baseline modules are needed to replay the controls.

The HTTP fixtures record requested backoff instead of sleeping through it.
Usage assertions concern returned successful responses, not unknown failed
remote attempts. These are scoped source/native controls; no full-repository,
hosted-CI, provider-quality, installed-runtime or deployment result is inferred.
