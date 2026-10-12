# Function selection on large Python diffs

The existing `targets` command previews the Python functions selected from a
diff without calling a model or running tests:

```sh
python -m testpilot targets --repo /path/to/project --git-base main --json
```

Function selection orders the touched and added line numbers once per source
file. Each function then uses those ordered numbers to find the entries within
its inclusive source span. This avoids scanning the complete changed-line sets
again for every function in a large file.

The returned records keep their existing meaning and order. A decorator belongs
to its function's span; a nested function belongs to its enclosing function;
methods keep their class-qualified names; and separate definitions with the same
name remain separate records. A deletion can select a surviving function while
its `changed_lines` is empty. Only actual added lines are listed in that field.
Selection parses source without importing or executing it.

For `T` touched lines, `A` added lines and `F` discovered functions, the range
lookup work changes from repeated scans of the line sets to sorting once and
binary searches for each function. The implementation keeps two temporary lists
containing `T + A` references. Source parsing, source-text slicing and output
serialization still have their existing costs. This tradeoff helps dense edits
in files containing many functions; it does not promise faster model calls or
test execution.

The [qualification record](receiving/function-line-index-efcb69c0f058/README.md)
contains complete CLI-output comparisons, raw timings and a reproducer. Its
inputs are fictional Python sources; it does not measure an installed service
or a paid-model generation run.
