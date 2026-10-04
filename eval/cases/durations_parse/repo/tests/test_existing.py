from durations import format_seconds


def test_format_seconds():
    assert format_seconds(3725) == "1h2m5s"
