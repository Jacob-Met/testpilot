# TestPilot report: **passed**

- Changed functions: sample.py::answer
- Tests written: 2 in tests/test_physical_line_consumer.py
- Repair rounds used: 0/0
- Final run: 3 passed, 0 failed, 0 errors, 0 skipped (rc=0); generated: 2 passed of 2 collected in 0.561s
- Coverage: unavailable (install `coverage`)
- Tokens: 320 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `fixture-planner`: 1 calls, 91 in / 18 out
  - `fixture-editor`: 1 calls, 160 in / 51 out

## Patch

```diff
diff --git a/tests/test_physical_line_consumer.py b/tests/test_physical_line_consumer.py
new file mode 100644
--- /dev/null
+++ b/tests/test_physical_line_consumer.py
@@ -0,0 +1,7 @@
+from sample import answer, note
+
+def test_changed_answer():
+    assert answer() == 2
+
+def test_literal_note():
+    assert note == "left\u2028right"
```
