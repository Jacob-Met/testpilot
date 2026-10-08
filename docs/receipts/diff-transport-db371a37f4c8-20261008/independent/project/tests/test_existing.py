import importlib
def test_existing():
    assert importlib.import_module('計測').value()[0] == '€'
