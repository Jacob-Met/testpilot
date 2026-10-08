# Independent raw-diff receiving

**Disposition: accepted for the scoped UTF-8/surrogateescape diff transport fix.**

Root inspected the exact scoped CLI patch, candidate CLI and unchanged native selector. The helper reads raw git/file/stdin bytes, keeps the previous universal-newline conversion, and preserves undecodable hunk bytes. A text-only stdin remains supported. Source decoding still belongs to tokenize.open; selector, generation, sandbox and report behavior are not changed by the patch.

Native candidate CLI SHA-256: `83caf8df097902120a0cfbd6adb897d5b6be7ba2407b0217606e7038599b5a5f`. Root's receiver hashes every production Python module before and after execution. The final receipt SHA-256 is `fe66787b444ac8dc37a4803dc96c258c4a040dfa752de9311e5af602b5827acd`.

## Independent behavioral witness

The receiver created a real Git repository with unquoted UTF-8 filename `計測.py`, a CP1252 source encoding cookie, and a euro sign encoded as byte 0x80 inside the changed function. Git's raw diff therefore contains both UTF-8 path bytes and a hunk that cannot be decoded as UTF-8. No raw-diff fixture supplied by the author was reused.

With the CLI console configured to CP1252 and strict text errors:

- Original file input exits 2 on UTF-8 decoding.
- Original stdin input exits 0 but silently returns an empty target list because its text wrapper misdecodes the unquoted UTF-8 path.
- Candidate file and stdin inputs both select the one correct function, exact changed line and correctly decoded Python source.

A real candidate stdin `run`, using a strict UTF-8 console for report output, then generates one test with the scripted provider, executes it with native Python/pytest, and records both the existing and generated tests passing. The report contains the exact generated test text. Original/candidate production sources and fixture source files are unchanged. Final native receiver process 83671 exits 0.

## Preserved first receiver failure

`receive-console-codec.py`, `process.log`, the initial fixture and `run-output/` preserve the first attempted independent run. Its four preview controls reached the assertions successfully, but the scripted editor fixture used unsupported tilde fences, producing a legitimate `no_tests` report. Printing that report then encountered an existing CP1252-console limitation for the Japanese filename. This is not evidence against the raw-diff fix; the report already contains the correct selected target.

The final receiver uses the documented backtick fence and uses UTF-8 for the real run's human-readable report output. Its four preview controls still use CP1252, retaining the independent transport witness. The initial narrow-console report limitation remains recorded and was not repaired in this contribution. No application source changed during receiving.

The author separately preserves its complete original/candidate CLI matrix, regression suite, current-main composition and APFS invalid-filename fixture limitation. This independent packet does not claim to rerun that entire suite.
