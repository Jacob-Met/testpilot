# TestPilot report: **suspected_code_bug**

The run timed out, and the only input containing a space is "1h 30m 5s". In parse_duration the `elif ch == " ": continue` branch never increments `i`, so the loop spins forever on the first space. The docstring says spaces are allowed, so the test is right; the branch needs `i += 1`.

- Changed functions: durations.py::parse_duration
- Tests written: 4 in tests/test_parse_duration.py
- Repair rounds used: 1/3
- Final run: TIMEOUT after 10s in 10.005s
- Coverage: unavailable (install `coverage`)
- Tokens: 1176 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 231 in / 42 out
  - `nvidia/Nemotron-3_5-Lightning`: 2 calls, 721 in / 182 out

## Patch

```diff
diff --git a/tests/test_parse_duration.py b/tests/test_parse_duration.py
new file mode 100644
--- /dev/null
+++ b/tests/test_parse_duration.py
@@ -0,0 +1,21 @@
+import pytest
+
+from durations import parse_duration
+
+
+def test_compact():
+    assert parse_duration("1h30m") == 5400
+
+
+def test_spaced():
+    assert parse_duration("1h 30m 5s") == 5405
+
+
+def test_unknown_unit():
+    with pytest.raises(ValueError):
+        parse_duration("3d")
+
+
+def test_trailing_number():
+    with pytest.raises(ValueError):
+        parse_duration("1h30")
```
