# TestPilot report: **passed**

- Changed functions: m.py::double
- Tests written: 2 in tests/test_double_testpilot.py, tests/test_tripled_input.py
- Repair rounds used: 2/2
- Final run: 3 passed, 0 failed, 0 errors, 0 skipped (rc=0) in 0.333s
- Coverage (total): 100.0% -> 100.0% (+0.0 pts)
- Coverage (changed lines, n=2): 100.0% -> 100.0%
- Tokens: 1059 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 92 in / 16 out
  - `nvidia/Nemotron-3_5-Lightning`: 3 calls, 836 in / 115 out

## Patch

```diff
diff --git a/tests/test_double_testpilot.py b/tests/test_double_testpilot.py
new file mode 100644
--- /dev/null
+++ b/tests/test_double_testpilot.py
@@ -0,0 +1,4 @@
+from m import double
+
+def test_generated():
+    assert double(2) == 4
diff --git a/tests/test_tripled_input.py b/tests/test_tripled_input.py
new file mode 100644
--- /dev/null
+++ b/tests/test_tripled_input.py
@@ -0,0 +1,4 @@
+from m import double
+
+def test_generated():
+    assert double(3) == 6
```
