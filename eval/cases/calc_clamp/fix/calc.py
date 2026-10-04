"""Tiny arithmetic helpers."""


def add(a, b):
    return a + b


def clamp(x, lo, hi):
    """Clamp x into the closed interval [lo, hi]."""
    if lo > hi:
        raise ValueError("lo must be <= hi")
    return max(lo, min(hi, x))


def mean(values):
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)
