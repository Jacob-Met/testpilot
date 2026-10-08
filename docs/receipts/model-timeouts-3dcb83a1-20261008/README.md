# Model response timeouts

A response-body timeout could terminate TestPilot before it wrote its result
and reports. Native urllib raised `TimeoutError` directly after an authored
HTTP server sent valid response headers and stalled the body. The existing
client caught HTTP/URL errors only, so a client configured with one retry made
one request, performed no retry and leaked the timeout past the loop's
`ModelError` receiver.

## Repair

`OpenAICompatClient.chat` now handles direct `TimeoutError` through the same
existing retry counter and exponential delay as `URLError`. Exhaustion raises
a chained `ModelError`. The loop can then write its existing `model_error`
result, including any generated failing tests retained from earlier rounds.

The configured retry limit and delay schedule are unchanged. HTTP status
handling, successful response parsing/usage and unrelated exception behavior
are unchanged. No CLI, loop, runner, routing or provider configuration changes.

Scope was announced in [issue 2](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6056997400).

## Source and native qualification

| Material | Identity |
| --- | --- |
| Initial tested main | `981eb6c1cc6765c922f2e1fc394b9e28499c5440` |
| Current receiving base | `f350150259c00dd25c43a95d65157022612d15a8` |
| Original model Git blob | `20294ab3ad529b142ae955e1c4bc0ce71f87ae8b` |
| Candidate model Git blob | `af0c0662faed09dc1db286233719b90d1504b229` |
| Candidate model SHA-256 | `7d09afbb738f349a04756a9b69559b3bfabfe096e632409a80563b0dac635547` |
| New regression SHA-256 | `1d1789544582acbacd2bb4c47742ea469e0f0714943c7d56ea6052ba4f340613` |

On native CPython 3.14.4 / pytest 9.0.2, the frozen eight new cases produce
**six failures and two passes on the original**. The candidate passes all
**eight new plus seven existing model cases: 15/15, zero skips/errors**.

The new tests use actual urllib and an HTTP fixture bound to `127.0.0.1`.
They cover recovery, zero/exhausted retries, a retry budget shared with HTTP
503, unchanged terminal HTTP 400 handling and unchanged unrelated exceptions.
The fixture records the requested backoff instead of sleeping through it.

Two tests execute the real CLI entrypoint, current loop and native pytest.
Only the client factory is injected to provide the local endpoint and short
request deadline. A recovered planning response leads to exit 0, two generated
tests plus one existing test passing, and a Git-applicable patch. An exhausted
repair timeout leads to exit 1 and `model_error`, with the already generated
failing-test patch, JSON and Markdown reports retained. Original source and
existing tests stay unchanged in both controls. Reported usage remains the
usage returned with the two successful responses.

Main subsequently incorporated the match selector and project-Python CLI.
The current receiving tree preserves their exact source; the model, loop and
sandbox blobs remained unchanged from the initial qualification.

## Independent receiving

A separately assigned independent source/receiving review is in progress.
The model and regression hashes above are frozen. This initial source
publication remains a draft until that receiving decision is recorded.

## Repeat

From the candidate checkout with its existing pytest dependency:

```bash
python3 -m pytest -q tests/test_model.py tests/test_model_timeouts.py
```

For the negative control, place the unchanged new regression into a separate
checkout at the initial tested main and run that module. Its six timeout
failures and two inherited-behavior passes are expected. No copied baseline
source is needed; Git retains the exact original.

[results.json](results.json) records the original witness, commands, source
pins and scoped results. The independent note records its distinct receiving
control. No full-repository suite, hosted-CI pass, provider/model-quality result
or usage for failed remote attempts is inferred. All endpoints, programs and
replies here were authored fixtures; no provider or account credential was used.
