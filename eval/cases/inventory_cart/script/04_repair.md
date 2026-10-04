Maybe the discount is applied per item; recompute.

```python path=tests/test_cart_total.py
import pytest

from inventory import Cart


def _cart():
    c = Cart()
    c.add("apple", 2.0, qty=5)
    c.add("pear", 5.0, qty=2)
    return c


def test_no_discount():
    assert _cart().total() == 20.0


def test_ten_percent_discount():
    assert _cart().total(10) == pytest.approx(2.0 * 5 * 0.9 + 5.0 * 2 * 0.9)


def test_empty_cart():
    assert Cart().total() == 0


def test_bad_discount():
    with pytest.raises(ValueError):
        _cart().total(150)
```
