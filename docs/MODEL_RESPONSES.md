# Model response handling

TestPilot saves completed generation work when a later OpenAI-compatible model
reply cannot be used. The run returns `model_error` with CLI exit code 1 and uses
the existing output writer for `testpilot.patch`, `report.json`, `report.md` and
`report.html`.

A repair failure retains the prior generated test files, their patch, the plan,
the last actual pytest result, completed round records and admitted model usage.
An editor failure can retain the plan even though no tests have been produced.
A planner failure still produces the ordinary error reports with no invented
generated files or model usage.

## Replies admitted by the text client

The default HTTP transport must receive the declared response body completely
and decode it as UTF-8 JSON. Malformed encoding or JSON, JSON decoder digit or
nesting limits, and a prematurely closed body become model errors.

The selected `choices[0].message.content` must be text or null; null keeps the
existing empty-text meaning. Text and a provided model name must be representable
as UTF-8. Missing model metadata continues to use the requested model name.
Text, whitespace and Unicode are preserved without stringifying other types.

Missing or null usage keeps the existing character-based token estimate. An
object without `prompt_tokens` keeps that same estimation convention. When
prompt counts are supplied, their existing `int()` conversion is preserved;
numeric strings and other previously convertible values keep their prior
behavior, while failed conversions become model errors. This change does not
introduce nonnegative-integer validation or a new token-accounting policy.
Malformed non-object usage is refused.

## Requests and the saved ledger

An unusable completed response is terminal. TestPilot does not automatically
repeat it, even if an earlier request in the same call was retried. Existing
configured HTTP status, connection and timeout retries keep their own shared
attempt budget and delays. If a terminal HTTP error has an incomplete diagnostic
body, its HTTP status is retained with an incomplete-body message.

The ledger includes successfully admitted replies only. A failed reply adds no
token or cost entry. This does not establish what an external provider billed.
Unrelated exceptions from a caller-supplied transport retain their original
identity; cancellation behavior is unchanged.

## Saved-work boundaries

The existing report schema, runner, target selection and output writer are
unchanged. Output preparation or filesystem failures retain the writer's
documented behavior; handling a model error does not guarantee that an unavailable
output filesystem can accept the reports. See the README's **Saving a complete
report** section for the four-file replacement boundary.

All receiving evidence for this correction uses authored localhost responses and
temporary test projects. It does not establish a live provider's availability,
billing or model quality.
