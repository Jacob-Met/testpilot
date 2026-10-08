# TestPilot report: **passed**

- Changed functions: module\udcff.py::measure
- Tests written: 1 in tests/test_raw_filename.py
- Repair rounds used: 0/0
- Final run: 2 passed, 0 failed, 0 errors, 0 skipped (rc=0) in 0.208s
- Coverage: unavailable (install `coverage`)
- Tokens: 324 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `P`: 1 calls, 96 in / 13 out
  - `E`: 1 calls, 160 in / 55 out

## Patch

```diff
diff --git a/tests/test_raw_filename.py b/tests/test_raw_filename.py
new file mode 100644
--- /dev/null
+++ b/tests/test_raw_filename.py
@@ -0,0 +1,6 @@
+import os
+import runpy
+
+def test_measure_raw_filename():
+    module = runpy.run_path(os.fsdecode(bytes.fromhex('6d6f64756c65ff2e7079')))
+    assert module['measure'](4) == 6
```
