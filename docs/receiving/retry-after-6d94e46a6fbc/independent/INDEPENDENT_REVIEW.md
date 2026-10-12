# Independent TestPilot Retry-After review

Recorded 2026-10-12T22:05:31.815679+00:00 by `/root/engine_reliability`.

**Accepted:** no blocking correctness or source-scope finding in the three frozen files. `/root/product_workflow` retains implementation ownership; this review transfers no integration or release authority.

## Exact reviewed files

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `testpilot/model.py` | 12670 | `7cfcebb2b087f788de7ecd62d11426b97b2035f9ca9c7e3f1dac65f162987287` |
| `tests/test_model_retry_after.py` | 8589 | `2890ecfda7606b7cb60f45fa5b21a0e5f8ff3198372c9b53f9e5b6709a15a9a0` |
| `docs/PROVIDER_RETRY_AFTER.md` | 3455 | `5d9a334c7fceb7224fa9a05123b2113e959d18bb245f1416759a192acc13536e` |

## Independent executed receiver

The receiver was prepared from the owner’s declared contract before the candidate source changed from the original bytes. It invokes the public `OpenAICompatClient.chat` API with tracked HTTP error bodies, a fixed UTC clock, an EST5 process timezone, and injected transport/sleep callbacks. It makes no provider request and performs no real backoff wait.

- Original: **28 compatibility controls passed; 24 expected timing failures**, process exit 1.
- Candidate: **52 cases passed, zero failures**, process exit 0.
- The receiver checks request URL/headers/body/timeout identity, returned model and token usage, response closure before waiting or refusing, and diagnostic-body read boundaries.
- Inputs include the existing retry statuses, terminal/exhausted controls, repeated exponential fallback, integer/date guidance, malformed/non-ASCII values, huge and zero-padded integers, the exact 120-second limit, fractional clock offsets, all three HTTP-date forms under a non-UTC timezone, and obsolete-year interpretation. An unusual seven-retry control preserves the existing 128-second exponential wait.

## Source and documentation assessment

The source diff is limited to standard-library imports, the bounded guidance parser and the existing retriable-HTTP branch. Refusal and parsing run inside the response-closing `finally`; the attempt count advances only for a retry that will be made. Connection errors, timeouts, terminal diagnostics, request construction and usage parsing retain their original bodies. The documentation explains the provider-only wait limit and does not promise automatic resumption.

The date interpretation was checked against [RFC 9110 §5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7); the header alternatives against [§10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3). This is a bounded client review, not certification of a general HTTP parser.

## Evidence and limits

`independent-review-receipt.json` contains every source and receipt identity. `original-review.json` and `candidate-review.json` retain all 52 inputs, observed events and results. `independent_retry_review.py` is the exact executed receiver. The owner’s maintained full suite and real-loopback CLI checks are distinct evidence; this reviewer read their new test source but did not execute that full workflow. No installed or external-provider behavior is asserted.
