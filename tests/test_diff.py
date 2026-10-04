import textwrap

from testpilot.diff import changed_functions, is_test_path, module_name, parse_unified_diff

DIFF = textwrap.dedent('''\
    diff --git a/pkg/mod.py b/pkg/mod.py
    index 111..222 100644
    --- a/pkg/mod.py
    +++ b/pkg/mod.py
    @@ -1,8 +1,10 @@
     def a():
    -    return 1
    +    return 2
     
     
     class K:
         def m(self):
    -        x = 1
             return 0
    +
    +def new():
    +    pass
    diff --git a/tests/test_mod.py b/tests/test_mod.py
    --- a/tests/test_mod.py
    +++ b/tests/test_mod.py
    @@ -1 +1 @@
    -x = 1
    +x = 2
    diff --git a/README.md b/README.md
    --- a/README.md
    +++ b/README.md
    @@ -1 +1 @@
    -old
    +new
    ''')

NEW_SRC = textwrap.dedent('''\
    def a():
        return 2


    class K:
        def m(self):
            return 0

    def new():
        pass
    ''')


def test_parse_line_numbers():
    files = parse_unified_diff(DIFF)
    assert [f.path for f in files] == ["pkg/mod.py", "tests/test_mod.py", "README.md"]
    f = files[0]
    assert f.added_lines == {2, 8, 9, 10}
    # the deleted "x = 1" is anchored to the neighbouring new lines 6 and 7
    assert {6, 7} <= f.touched_lines


def test_changed_functions(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text(NEW_SRC)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text("x = 2\n")
    funcs = changed_functions(tmp_path, DIFF)
    assert [f.qualname for f in funcs] == ["a", "K.m", "new"]
    km = funcs[1]
    assert km.is_method and km.import_name == "K" and km.module == "pkg.mod"
    assert km.changed_lines == []  # pure deletion: touched, but no added lines
    assert funcs[0].changed_lines == [2]
    assert "def new" in funcs[2].source
    # test file has no functions, so including tests changes nothing here
    assert len(changed_functions(tmp_path, DIFF, include_tests=True)) == 3


def test_new_and_deleted_files(tmp_path):
    diff = textwrap.dedent('''\
        --- /dev/null
        +++ b/src/lib/x.py
        @@ -0,0 +1,2 @@
        +def f():
        +    return 1
        --- a/gone.py
        +++ /dev/null
        @@ -1,2 +0,0 @@
        -def g():
        -    pass
        ''')
    files = parse_unified_diff(diff)
    assert files[0].is_new and files[0].path == "src/lib/x.py"
    assert files[1].is_deleted
    (tmp_path / "src" / "lib").mkdir(parents=True)
    (tmp_path / "src" / "lib" / "x.py").write_text("def f():\n    return 1\n")
    funcs = changed_functions(tmp_path, diff)
    assert [(f.module, f.qualname) for f in funcs] == [("lib.x", "f")]


def test_removed_line_that_looks_like_header():
    diff = "--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,2 @@\n x = 1\n--- y\n z = 3\n"
    files = parse_unified_diff(diff)
    assert len(files) == 1 and files[0].added_lines == set()


def test_decorated_and_async(tmp_path):
    src = "import functools\n\n@functools.cache\ndef f():\n    return 1\n\nasync def g():\n    return 2\n"
    (tmp_path / "m.py").write_text(src)
    diff = ("--- a/m.py\n+++ b/m.py\n@@ -2,0 +3,1 @@\n+@functools.cache\n"
            "@@ -8 +8 @@\n-    return 3\n+    return 2\n")
    assert [f.qualname for f in changed_functions(tmp_path, diff)] == ["f", "g"]


def test_helpers():
    assert is_test_path("tests/a.py") and is_test_path("x/test_a.py") and is_test_path("a_test.py")
    assert not is_test_path("pkg/testing_utils.py")
    assert module_name("pkg/__init__.py") == "pkg"
    assert module_name("src/pkg/a.py") == "pkg.a"
