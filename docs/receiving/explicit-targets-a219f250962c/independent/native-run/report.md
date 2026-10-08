# TestPilot report: **passed**

- Caller-selected functions: settings.py::Policy.cap, settings.py::accepts
- Selection: Caller selected these targets; no dependency inference was performed.
- Tests written: 2 in tests/test_selected.py
- Repair rounds used: 1/1
- Final run: 3 passed, 0 failed, 0 errors, 0 skipped (rc=0); generated: 2 passed of 2 collected in 0.736s
- Coverage (total): 77.8% -> 100.0% (+22.2 pts)
- Coverage (changed lines, n=0): None% -> None%
- Tokens: 1199 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 265 in / 15 out
  - `nvidia/Nemotron-3_5-Lightning`: 2 calls, 811 in / 108 out

## Patch

```diff
diff --git a/tests/test_selected.py b/tests/test_selected.py
new file mode 100644
--- /dev/null
+++ b/tests/test_selected.py
@@ -0,0 +1,8 @@
+from settings import accepts, Policy
+
+def test_selected_limit():
+    assert accepts(7) is True
+    assert accepts(8) is False
+
+def test_selected_default():
+    assert Policy.cap(20) == 7
```
