```python path=tests/test_backend.py
from backend import total


def test_total():
    assert total([1, 2]) == 5


def test_empty():
    assert total([]) == 2
```
