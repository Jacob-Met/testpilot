VERDICT: CODE_BUG
clamp(5, 0, 10) returns 10 and clamp(-3, 0, 10) returns 10: the expression `max(hi, min(lo, x))` has lo and hi swapped, so it always returns hi. The tests encode the documented contract ("clamp x into [lo, hi]"); the fix is `max(lo, min(hi, x))`.
