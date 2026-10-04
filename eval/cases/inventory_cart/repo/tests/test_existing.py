import pytest

from inventory import Cart


def test_add_rejects_zero_qty():
    with pytest.raises(ValueError):
        Cart().add("x", 1.0, qty=0)
