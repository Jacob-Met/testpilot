# TestPilot report: **failed**

still failing after 3 repair round(s): 4 passed, 1 failed, 0 errors, 0 skipped (rc=1)

- Changed functions: inventory.py::Cart.total
- Tests written: 4 in tests/test_cart_total.py
- Repair rounds used: 3/3
- Final run: 4 passed, 1 failed, 0 errors, 0 skipped (rc=1) in 0.233s
- Coverage (total): 58.3% -> 100.0% (+41.7 pts)
- Coverage (changed lines, n=5): 20.0% -> 100.0%
- Tokens: 2337 (estimated); cost: unpriced (set TESTPILOT_PRICES)
  - `nvidia/nemotron-3-super-120b-a12b`: 1 calls, 166 in / 43 out
  - `nvidia/Nemotron-3_5-Lightning`: 4 calls, 1593 in / 535 out

## Patch

```diff
diff --git a/tests/test_cart_total.py b/tests/test_cart_total.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cart_total.py
@@ -0,0 +1,27 @@
+import pytest
+
+from inventory import Cart
+
+
+def _cart():
+    c = Cart()
+    c.add("apple", 2.0, qty=5)
+    c.add("pear", 5.0, qty=2)
+    return c
+
+
+def test_no_discount():
+    assert _cart().total() == 20.0
+
+
+def test_ten_percent_discount():
+    assert _cart().total(discount_pct=int(10)) == pytest.approx(18.0)
+
+
+def test_empty_cart():
+    assert Cart().total() == 0
+
+
+def test_bad_discount():
+    with pytest.raises(ValueError):
+        _cart().total(150)
```
