```python path=tests/test_parse_duration.py
import pytest

from durations import parse_duration


def test_compact():
    assert parse_duration("1h30m") == 5400


def test_spaced():
    assert parse_duration("1h 30m 5s") == 5405


def test_unknown_unit():
    with pytest.raises(ValueError):
        parse_duration("3d")


def test_trailing_number():
    with pytest.raises(ValueError):
        parse_duration("1h30")
```
