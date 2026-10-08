# TestPilot report: **passed**

- Changed functions: sample.py::selected
- Tests written: 1 in tests/test_testpilot_generated.py
- Repair rounds used: 0/0
- Final run: 1 passed, 0 failed, 0 errors, 0 skipped (rc=0); generated: 1 passed of 1 collected in 1.217s
- Coverage: unavailable
- Tokens: 280 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 93 in / 7 out
  - `nvidia/Nemotron-3_5-Lightning`: 1 calls, 151 in / 29 out

## Patch

```diff
diff --git a/tests/test_testpilot_generated.py b/tests/test_testpilot_generated.py
new file mode 100644
--- /dev/null
+++ b/tests/test_testpilot_generated.py
@@ -0,0 +1,3 @@
+from sample import selected
+def test_selected():
+    assert selected() == 2
```
