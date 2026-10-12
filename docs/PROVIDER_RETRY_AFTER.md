# Waiting after a provider asks TestPilot to retry

The OpenAI-compatible client now reads a provider's `Retry-After` response
header before another attempt. This applies to the client's existing retryable
HTTP statuses: 429, 500, 502, 503 and 504, and only while a retry remains.

For each retry, TestPilot waits for the greater of its existing exponential
backoff and the provider's requested delay. With the default two retries, the
backoff remains two seconds and then four seconds. For example, a first 429
response with `Retry-After: 17` selects a 17-second wait; `Retry-After: 0`
retains the two-second backoff. Neither header changes the request or adds
another retry.

Supported guidance is a nonnegative ASCII integer number of seconds or a
parseable HTTP date. The three HTTP-date forms are supported: the usual
four-digit-year form, the obsolete two-digit-year form and asctime. An
asctime value is interpreted in UTC. The obsolete year uses HTTP's rolling
fifty-year rule, so a year such as `69` is interpreted as 2069 when the current
year is 2026. Date guidance uses the computer's current UTC clock; an incorrect
system clock can affect its meaning. Past dates, missing headers and values
that cannot be parsed retain the existing backoff.

## Long waits and saved results

A valid provider delay above 120 seconds ends that model call with a
`ModelError`, without another request or sleep. The diagnostic retains the
HTTP status and explains that the requested wait exceeds 120 seconds. It does
not copy the response body or the full header value. This makes long provider
outages explicit and avoids retrying before the requested wait has elapsed.
Exactly 120 seconds is accepted. The limit applies to provider guidance, not
to a caller's pre-existing exponential schedule with unusually many retries.

TestPilot's normal generation loop handles this error through its existing
`model_error` result. Previously completed planning, generated tests, test
results and known token usage remain available in the saved report and patch.
A later run is a new run; this change does not add automatic resumption.

The failed HTTP response is closed before either sleeping or returning the
long-wait error. Retry paths do not read its diagnostic body. Terminal HTTP
statuses and exhausted retries retain their existing bounded diagnostic read.
Connection errors and timeouts keep their existing retry behavior.

## Verification

Run the focused suite with:

```sh
python -m pytest -q tests/test_model_retry_after.py tests/test_model.py tests/test_model_timeouts.py tests/test_model_retry_lifetime.py tests/test_model_error_detail.py
```

The new cases exercise the public client, all existing retryable statuses,
seconds/date parsing, refused long waits and response lifetime. Two cases use
the real urllib transport against an authored loopback HTTP server and the
existing CLI: recovery produces passing tests and reports, while a long wait
during repair retains the failing patch and completed usage. Test sleeps are
injected so the suite checks the selected delay without waiting two minutes.
No live model or provider credentials are used. Existing timeout helpers supply
the same fictional repository and CLI boundary for these two cases.

HTTP guidance: [RFC 9110 §10.2.3, Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
and [§5.6.7, Date/Time Formats](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7).
