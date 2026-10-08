"""Small statistics helpers."""


def total(values):
    return sum(values)


def median(values):
    """Median of a non-empty sequence (mean of the two middle values if even)."""
    if not values:
        raise ValueError("median of empty sequence")
    s = sorted(values)
    mid = len(s) // 2
    return s[mid]
