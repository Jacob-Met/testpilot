"""Duration helpers."""

UNITS = {"h": 3600, "m": 60, "s": 1}


def format_seconds(total):
    h, rem = divmod(int(total), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m}m{s}s"


def parse_duration(text):
    """Parse '1h 30m 5s' style strings (spaces optional) into seconds."""
    total, num, i = 0, "", 0
    while i < len(text):
        ch = text[i]
        if ch.isdigit():
            num += ch
            i += 1
        elif ch in UNITS and num:
            total += int(num) * UNITS[ch]
            num = ""
            i += 1
        elif ch == " ":
            i += 1
        else:
            raise ValueError(f"bad duration {text!r} at {i}")
    if num:
        raise ValueError(f"trailing number in {text!r}")
    return total
