# TestPilot report: **passed**

- Changed functions: calc.py::classify
- Tests written: 1 in tests/test_negative.py
- Repair rounds used: 0/0
- Final run: 2 passed, 0 failed, 0 errors, 0 skipped (rc=0) in 1.195s
- Coverage (total): 75.0% -> 100.0% (+25.0 pts)
- Coverage (changed lines, n=1): 100.0% -> 100.0%
- Tokens: 315 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 107 in / 9 out
  - `nvidia/Nemotron-3_5-Lightning`: 1 calls, 167 in / 32 out

## Patch

```diff
diff --git a/tests/test_negative.py b/tests/test_negative.py
new file mode 100644
--- /dev/null
+++ b/tests/test_negative.py
@@ -0,0 +1,4 @@
+from calc import classify
+
+def test_negative():
+    assert classify(-1) == "negative"
```
