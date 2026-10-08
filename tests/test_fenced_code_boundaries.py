"""Keep inline backticks inside complete generated Python code blocks."""
import pytest

from testpilot.loop import parse_test_files


FENCE = chr(96) * 3
BODIES = [
    f'def test_inline():\n    assert "{FENCE}" == "{FENCE}"\n',
    f"def test_format():\n    assert f'{FENCE}{{1}}' == '{FENCE}1'\n",
    f"def test_comment():\n    # Keep marker {FENCE} in the comment.\n    assert True\n",
    f'def test_long():\n    assert "{FENCE * 2}" == "{FENCE * 2}"\n',
    f"def test_info_line():\n    value = '''\n{FENCE}python\nexample\n'''\n    assert 'python' in value\n",
]


def block(path, body):
    return FENCE + f"python path={path}\n" + body + FENCE + "\n"


@pytest.mark.parametrize("body", BODIES, ids=["literal", "fstring", "comment", "long_ticks", "info_line"])
def test_backticks_inside_python_body_do_not_close_fence(body):
    compile(body, "authored-valid-test.py", "exec")
    files, warnings = parse_test_files(block("tests/test_body.py", body))
    assert warnings == []
    assert files == {"tests/test_body.py": body}
    compile(files["tests/test_body.py"], "received-test.py", "exec")


@pytest.mark.parametrize("newline,closing", [
    ("\n", FENCE + "\n"),
    ("\r\n", FENCE + "\r\n"),
    ("\n", FENCE),
    ("\n", FENCE + chr(96) + "\n"),
    ("\n", FENCE + " \t\n"),
], ids=["lf", "crlf", "end_of_text", "longer_closer", "trailing_space"])
def test_complete_fence_endings_keep_ordinary_code(newline, closing):
    body = newline.join(["def test_ok():", "    assert True", ""])
    reply = FENCE + "python path=tests/test_ok.py" + newline + body + closing
    files, warnings = parse_test_files(reply)
    assert warnings == []
    assert files == {"tests/test_ok.py": body}


def test_multiple_code_blocks_survive_inline_literal_and_ignored_language():
    first = BODIES[0]
    second = "def test_second():\n    assert 2 + 2 == 4\n"
    reply = (
        block("tests/test_first.py", first)
        + FENCE + "javascript\nvoid 0;\n" + FENCE + "\n"
        + block("tests/test_second.py", second)
    )
    files, warnings = parse_test_files(reply)
    assert warnings == []
    assert files == {"tests/test_first.py": first, "tests/test_second.py": second}


def test_inline_backticks_cannot_complete_an_unclosed_block():
    reply = FENCE + "python path=tests/test_open.py\n" + BODIES[0]
    files, warnings = parse_test_files(reply)
    assert files == {}
    assert warnings == []


@pytest.mark.parametrize("reverse", [False, True])
def test_directly_adjacent_fences_keep_legacy_compact_boundaries(reverse):
    first = ("tests/test_first.py", BODIES[0])
    second = ("tests/test_second.py", "def test_second():\n    assert True\n")
    pairs = [second, first] if reverse else [first, second]
    # Existing repair callers concatenate a closing and opening fence directly.
    reply = "".join(block(path, body).removesuffix("\n") for path, body in pairs)
    files, warnings = parse_test_files(reply)
    assert warnings == []
    assert files == dict(pairs)
