from eval.harness import evaluate_case, load_cases, render_table, summarize


def test_cases_present():
    assert len(load_cases()) == 5


def test_scripted_eval_outcomes():
    # timeout=10 matches the eval harness CLI default. The sandbox enforces a
    # hard wall clock, so a smaller timeout flakes on loaded machines: a
    # timed-out run consumes script replies (ScriptExhausted -> model_error) or
    # breaks the bug_revealing re-runs, contradicting the "fixed by
    # construction" determinism this test asserts.
    rows = [evaluate_case(c, coverage=False, timeout=10) for c in load_cases()]
    by = {r["case"]: r for r in rows}
    assert by["calc_clamp"]["solved"] and by["calc_clamp"]["rounds_used"] == 1
    assert by["textutil_slugify"]["solved"] and by["textutil_slugify"]["rounds_used"] == 2
    assert by["durations_parse"]["solved"]
    assert by["inventory_cart"]["status"] == "failed" and by["inventory_cart"]["rounds_used"] == 3
    assert by["inventory_cart"]["bug_revealing"] and not by["inventory_cart"]["solved"]
    assert by["stats_median"]["status"] == "passed" and not by["stats_median"]["bug_revealing"]
    s = summarize(rows)
    assert s["pass@1"] == 0.6 and s["tests_written"] == 19 and s["rounds_used"] == 7
    assert "pass@1 = 0.60" in render_table(rows, s, "scripted")
