"""Admission for whole-number generation limits shared by the CLI and API."""
from __future__ import annotations


def nonnegative_integer(value: int, *, name: str) -> int:
    """Keep an integer count without coercing floats, strings, or booleans."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value
