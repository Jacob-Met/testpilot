# Close retryable HTTP responses before waiting

At main `c32b5459657ec26aac9837b823b1bc326510873e`, `OpenAICompatClient.chat` closes a terminal `HTTPError`, but a retryable error leaves the response open while the client waits and starts another request. The authored receiver retains the actual `urllib` error objects and observes their response state at the injected backoff boundary. This does not rely on garbage collection timing.

The production change closes the failed response immediately before the existing retry counter, delay and continuation. The retry statuses, attempt budget, request payload, terminal diagnostics, successful response admission and usage accounting are unchanged.

## Reproduce

From a repository checkout with Python 3.12:

```sh
python -m unittest discover -s tests -p test_model_retry_lifetime.py -v
python -m unittest discover -s tests -p test_model_error_detail.py -v
```

The new receiver uses actual HTTP/1.1 responses served only on `127.0.0.1`, calls the real `_urllib_transport`, and uses a literal fixture key. It tests retry success, retry exhaustion, a nonretryable error and a retryable error with zero retries. It observes every response as closed before backoff, retains the original retry delays and request content, and checks terminal error chaining. All fixture responses are closed during teardown, including when an assertion fails.

## Recorded results

| Exact source | Result |
| --- | --- |
| Original main model, new unchanged receiver | 2 passed, 2 failed: responses remained open at retry backoff and after exhaustion |
| Candidate model, same receiver | 4 passed |
| Candidate model, unchanged terminal diagnostic receiver | 3 passed |
| Held #54 response protocol model plus only this insertion | 4 passed |
| Independent receiver, original main model | 2 passed, 2 failed |
| Independent receiver, exact candidate model | 4 passed |

These runs used local CPython 3.12.14. Raw stdout/stderr is retained alongside the source and test identities in `manifest.json`. The pytest dependency is absent from this receiving environment; the full pytest suite and pytest-based timeout/CLI gates were not run, and no dependency was installed.

## Independent receiving

The separate `runtime_integration` receiver froze its own four-case contract before running the candidate and did not read the author's tests. Its real loopback HTTP cases use 503 → 429 → 200 to observe both the `HTTPError` and its underlying response closed before each backoff and the next POST, without reading retry error bodies. A distinct interrupted-backoff case confirms that the response closes before the same injected interruption escapes and that no second POST occurs. Terminal 401 diagnostic reads remain bounded to 2,000 bytes and close normally; immediate success, exact usage, request bytes/headers and delays remain unchanged.

The exact receiver, frozen contract and original/candidate JSON receipts are preserved under `independent/`; `manifest.json` binds every file's bytes, SHA-256 and Git identity. The receiver expects `original/model.py` and `candidate/model.py` beside it, with the exact hashes in its contract, and the unchanged `testpilot` package on `PYTHONPATH`. Copy these evidence files to a separate temporary receiving directory before rerunning, because the script writes its two receipt files there. The published receipts are the independently obtained results, not a rerun by the source author.

## Adjacent ownership

[Issue 54](https://github.com/Jacob-Met/testpilot/issues/54) owns completed-response decoding/admission. Its held source at `eec7730ec1c0b91e0a5dd086296888adfafa0762`, model blob `383d91fa1b7f6b3b47057a5ab183ccbb938f89af`, has the same unique retry span. Removing this insertion from the isolated compatibility copy recovers that complete held model byte for byte. Only the new lifetime receiver ran on this copy; its four passes do not qualify the held protocol contribution or release its hosted gate. No owner branch was adopted or modified.

The first isolated compatibility invocation lacked the package's supporting modules and failed during import. `held-protocol-composition.setup-error.log` preserves that setup failure. After copying the 16 exact supporting intake files, the same source and receiver passed in `held-protocol-composition.log`.

All 16 other received source/configuration/test files remain byte-identical to their parent blobs. The candidate does not change the workflow. The inspected workflow subscribes only to main pushes and pull requests; main had no protection, required checks or rulesets, and the repository had no Pages site. Source publication and integration must use the freshly verified owner and trigger conditions, with `[skip ci] [skip actions]` in actual source and merge commit messages under the continuing no-Actions instruction. This receipt establishes local source behavior; it does not claim a provider run, hosted test or deployment.
