# TestPilot report: **passed**

- Changed functions: stats.py::median
- Tests written: 3 in tests/test_median.py
- Repair rounds used: 0/3
- Final run: 4 passed, 0 failed, 0 errors, 0 skipped (rc=0) in 0.239s
- Coverage (total): 37.5% -> 100.0% (+62.5 pts)
- Coverage (changed lines, n=6): 16.7% -> 100.0%
- Tokens: 443 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 143 in / 27 out
  - `nvidia/Nemotron-3_5-Lightning`: 1 calls, 205 in / 68 out

## Patch

```diff
diff --git a/tests/test_median.py b/tests/test_median.py
new file mode 100644
--- /dev/null
+++ b/tests/test_median.py
@@ -0,0 +1,16 @@
+import pytest
+
+from stats import median
+
+
+def test_odd_unsorted():
+    assert median([3, 1, 2]) == 2
+
+
+def test_single():
+    assert median([7]) == 7
+
+
+def test_empty_raises():
+    with pytest.raises(ValueError):
+        median([])
```
