# TestPilot report: **suspected_code_bug**

clamp(5, 0, 10) returns 10 and clamp(-3, 0, 10) returns 10: the expression `max(hi, min(lo, x))` has lo and hi swapped, so it always returns hi. The tests encode the documented contract ("clamp x into [lo, hi]"); the fix is `max(lo, min(hi, x))`.

- Changed functions: calc.py::clamp
- Tests written: 4 in tests/test_calc_clamp.py
- Repair rounds used: 1/3
- Final run: 3 passed, 3 failed, 0 errors, 0 skipped (rc=1) in 0.237s
- Coverage (total): 60.0% -> 90.0% (+30.0 pts)
- Coverage (changed lines, n=4): 25.0% -> 100.0%
- Tokens: 1051 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 125 in / 51 out
  - `nvidia/Nemotron-3_5-Lightning`: 2 calls, 699 in / 176 out

## Patch

```diff
diff --git a/tests/test_calc_clamp.py b/tests/test_calc_clamp.py
new file mode 100644
--- /dev/null
+++ b/tests/test_calc_clamp.py
@@ -0,0 +1,22 @@
+import pytest
+
+from calc import clamp
+
+
+def test_inside_range_unchanged():
+    assert clamp(5, 0, 10) == 5
+
+
+def test_below_and_above():
+    assert clamp(-3, 0, 10) == 0
+    assert clamp(42, 0, 10) == 10
+
+
+def test_boundaries():
+    assert clamp(0, 0, 10) == 0
+    assert clamp(10, 0, 10) == 10
+
+
+def test_inverted_bounds_raise():
+    with pytest.raises(ValueError):
+        clamp(1, 10, 0)
```
