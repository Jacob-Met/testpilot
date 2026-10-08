# TestPilot report: **passed**

- Changed functions: subject.py::adjusted
- Tests written: 1 in tests/test_adjusted.py
- Repair rounds used: 1/1
- Final run: 2 passed, 0 failed, 0 errors, 0 skipped (rc=0); generated: 1 passed of 1 collected in 0.496s
- Coverage: unavailable
- Tokens: 728 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 98 in / 11 out
  - `nvidia/Nemotron-3_5-Lightning`: 2 calls, 521 in / 98 out

## Patch

```diff
diff --git a/tests/test_adjusted.py b/tests/test_adjusted.py
new file mode 100644
--- /dev/null
+++ b/tests/test_adjusted.py
@@ -0,0 +1,6 @@
+from testpilot_project_only_dependency import record
+from subject import adjusted
+
+def test_zero():
+    record('generated')
+    assert adjusted(0) == 41
```
