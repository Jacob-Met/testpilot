# Diff inputs and Python source encodings

Both `testpilot targets` and `testpilot run` accept the same three input routes:

```sh
python -m testpilot targets --repo PROJECT --git-base REF --json
python -m testpilot targets --repo PROJECT --diff change.diff --json
git -C PROJECT diff REF -- '*.py' | python -m testpilot targets --repo PROJECT --diff - --json
```

Use the corresponding `--git-base`, `--diff FILE` or `--diff -` option with `run` when ready to generate tests. Its existing backend, interpreter and output options remain available.

A Git diff can contain raw non-UTF-8 bytes from a valid Python file, including an encoding cookie such as `# coding: latin-1`. One diff can also contain files that use different source encodings. The CLI preserves those input bytes while interpreting the diff's paths and physical lines; it does not guess a single legacy encoding for the whole diff. UTF-8 content retains its existing meaning.

Selected Python files are still read from the requested working tree with Python's native source decoder. Their encoding cookies and UTF-8 BOMs determine source decoding, and the existing path-containment and AST-selection rules remain in effect. Source files are not rewritten. A transport change does not make an invalid Python source file valid or reserve its contents for a later invocation.

Saved files, Git stdout and ordinary binary stdin use UTF-8 with `surrogateescape` for undecodable bytes. Existing universal-newline handling is retained for LF, CRLF and CR input. Direct callers that supply a text-only stdin object remain supported.
