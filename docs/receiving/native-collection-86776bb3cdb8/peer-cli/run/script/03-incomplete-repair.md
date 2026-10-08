```python path=tests/test_generated.py
import pytest
import m
m.FACTOR = 3

@pytest.mark.parametrize("value, expected", [(2, 6), (3, 9)])
def test_generated(value, expected, native_argument):
    assert m.double(value) == expected
```
