```python path=tests/test_generated.py
import pytest
import m

@pytest.mark.parametrize("value, expected", [(2, 4), (3, 6)])
def test_generated(value, expected, native_argument):
    assert m.double(value) == expected
```
