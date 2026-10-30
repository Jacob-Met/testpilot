# Generation limits

`testpilot run --rounds N` and `--max-tokens N` take nonnegative whole integers.
Invalid limits return configuration-error exit code 2 before reading a diff,
constructing a model client, starting pytest, or replacing saved reports.

`--rounds 0` still generates and verifies tests once, without repair calls. The
default is three repair rounds. A positive value limits repair attempts after
the initial generated suite; it does not count the initial generation as a
repair.

`--max-tokens 0` permits no model calls. If the diff selects functions, TestPilot
still runs the existing-suite baseline, then reports `budget_exhausted`. Omit
`--max-tokens` for no total-token budget.

The token budget is checked before each model call using the accumulated ledger.
An individual call can take the recorded total past the budget; the setting
does not impose a provider request limit or predict the next response's size.

Python callers use the same count rules:

```python
pilot = TestPilot(client, max_repair_rounds=0, max_total_tokens=10000)
```

An invalid `max_repair_rounds` or `max_total_tokens` raises `ValueError` during
construction. Use integer values, not floats, strings, or booleans. `None` is
supported only for the omitted token budget. Valid defaults and run, repair,
ledger, and output behavior are unchanged.
