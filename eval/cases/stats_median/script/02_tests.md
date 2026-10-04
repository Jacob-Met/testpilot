```python path=tests/test_median.py
import pytest

from stats import median


def test_odd_unsorted():
    assert median([3, 1, 2]) == 2


def test_single():
    assert median([7]) == 7


def test_empty_raises():
    with pytest.raises(ValueError):
        median([])
```
