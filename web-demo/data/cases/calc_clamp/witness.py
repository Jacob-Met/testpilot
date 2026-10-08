from calc import clamp

def test_recorded_boundary():
    assert clamp(5, 0, 10) == 5
