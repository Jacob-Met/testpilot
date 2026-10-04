# TestPilot report: **suspected_code_bug**

slugify("Hello, World!") returns "hello--world". The docstring promises that each *run* of non-alphanumerics becomes a single '-', but the regex `[^a-z0-9]` has no `+` quantifier. The test expectation is correct; fix the regex to `[^a-z0-9]+`.

- Changed functions: textutil.py::slugify
- Tests written: 4 in tests/test_slugify.py
- Repair rounds used: 2/3
- Final run: 3 passed, 2 failed, 0 errors, 0 skipped (rc=1) in 0.25s
- Coverage (total): 57.1% -> 100.0% (+42.9 pts)
- Coverage (changed lines, n=4): 25.0% -> 100.0%
- Tokens: 1641 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 136 in / 56 out
  - `nvidia/Nemotron-3_5-Lightning`: 3 calls, 1161 in / 288 out

## Patch

```diff
diff --git a/tests/test_slugify.py b/tests/test_slugify.py
new file mode 100644
--- /dev/null
+++ b/tests/test_slugify.py
@@ -0,0 +1,17 @@
+from textutil import slugify
+
+
+def test_simple():
+    assert slugify("Hello World") == "hello-world"
+
+
+def test_punctuation_runs_collapse():
+    assert slugify("Hello, World!") == "hello-world"
+
+
+def test_strip_edges():
+    assert slugify("  --Rock & Roll--  ") == "rock-roll"
+
+
+def test_idempotent():
+    assert slugify("already-a-slug") == "already-a-slug"
```
