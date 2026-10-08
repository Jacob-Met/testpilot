from testpilot_project_only_dependency import record
from subject import adjusted

def test_existing():
    record('existing')
    assert adjusted(1) == 42
