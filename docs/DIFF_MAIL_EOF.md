# Receive an unsigned Git mail patch with a terminal no-newline deletion

TestPilot can inspect an unsigned `git format-patch` message whose last deleted source line is the two-byte text `- ` without a final newline. Previously, the parser mistook that deletion record for the start of a mail signature and rejected the entire valid diff. A Python change earlier in the same message therefore could not be selected.

The correction is limited to the mail-footer predicate in `testpilot/diff.py`. When old-side hunk records remain and the next record is exactly Git's `\ No newline at end of file` annotation, a record containing two hyphens and a space is handled as a source deletion. Existing hunk accounting consumes that deletion once; the annotation consumes no old or new source record. All bytes outside this one source span are preserved from the qualified parent.

## Observable behavior

A real Git patch can end with these bytes:

```python
b'-- \n\\ No newline at end of file\n'
```

The first record is a deletion prefix followed by the old source text. The second records the missing newline in that old file. It is valid for this pair to end an unsigned mail message, including when the deleted file is not Python and a previous file contains the Python change that TestPilot needs to inspect.

Saved mail patches remain usable through the existing file and stdin routes:

```sh
python -m testpilot targets --repo /path/to/project --diff change.patch --json
python -m testpilot targets --repo /path/to/project --diff - --json < change.patch
```

The new tests check exact JSON and stdout parity with the equivalent ordinary diff. They also check that the inspected source and saved input retain their bytes, inode, size and modification time.

A completed hunk can be followed by an intentional signature whose text is itself `\ No newline at end of file`. That remains a signature: the exemption requires a pending old-side record. The parser continues to refuse hunks with missing old or new body records, including after an EOF annotation. It also preserves delimiter-looking source records before a later file, default Git signatures, and signed messages with a preceding source EOF marker.

This is a count-and-record interpretation of Git's text grammar. Identical text that satisfies the declared deletion count and carries the immediate canonical annotation is interpreted as source; the parser cannot infer an author's different intent from identical bytes. This change does not introduce a general MIME or multi-message mail parser.

## Source and regression test

The qualified parent is [b751e1cff2b7902bbebd6e7040f764d49bcb1a46](https://github.com/Jacob-Met/testpilot/commit/b751e1cff2b7902bbebd6e7040f764d49bcb1a46), tree `2057c593b281f4bf7624df41081b57f104697b05`.

| Item | Git blob | Bytes |
| --- | --- | ---: |
| Original `testpilot/diff.py` | `f9970ed6f2a05b259a4f5de6379eb3c041865886` | 13,252 |
| Candidate `testpilot/diff.py` | `0dd10d6adc5df3e2a80640847c70aac00f1037af` | 13,511 |
| New `tests/test_diff_mail_eof.py` | `42d629e9daf5198133ce51bfee6e1a1922886376` | 7,419 |
| Retained source patch | `6492ba0247db22d00bf9b8da1d4941524092cce9` | 824 |

The five new test functions expand to 13 pytest cases. They create disposable local Git repositories and check the actual produced patches with `git apply --reverse --check` before inspection. The API transport cases cover LF and CRLF, with and without a terminal patch LF. The CLI cases cover a CRLF saved file and LF stdin. Damaged-count controls prove refusal before Python source reads.

The exact source change adds two comments and one local predicate value, then extends the existing footer condition. Header parsing, path decoding, source admission, line accounting, function traversal, alias behavior, CLI code, dependencies and workflows are unchanged. A mechanical reversal recovers every original source byte.

## Native qualification

Receiving ran on the existing ThinkPad Linux x86_64 environment with Python 3.14.4, Git 2.53.0 and pytest 9.0.2. No packages were installed. The 23-file parent projection contains all 14 package modules, six selected existing test modules, their conftest, pyproject and the unchanged workflow; the new test makes each received projection 24 files. Both original and candidate projections remained byte-identical to their recorded identities after the courses.

| Course | Original | Candidate |
| --- | --- | --- |
| Producer's three real Git patch witness | Plain and signed select the expected function; unsigned terminal EOF deletion raises `DiffFormatError` | Covered by regression and independent receiving below |
| New 13 pytest cases, normal Python | 7 pass, 6 expected failures | All 13 pass within the 128-case selected course |
| New 13 pytest cases, explicit `-O` | 7 pass, 6 expected failures | 13 pass |
| Six selected existing modules, normal Python | 115 pass | 115 pass within the 128-case selected course |
| Independent six retained actual Git mail patches, normal Python | 5 accepted controls; unsigned source-EOF message refuses | All 6 accepted; exact parsed-change and function parity with plain diffs |

All reported passing courses have zero skips. The original failing pytest subprocesses exit 1; the producer driver exits 0 only after verifying those expected negative results and the passing controls. The candidate pytest subprocesses exit 0.

The selected existing modules are `test_diff.py`, `test_diff_hunk_validation.py`, `test_git_quoted_paths.py`, `test_physical_lines.py`, `test_python_source_encoding.py`, and `test_cli_diff_transport.py`. Their complete received contents are in the producer packet.

The optimized new course explicitly passes `-O` to its four actual CLI subprocesses: a plain-diff control and an unsigned mail invocation for each input route. This claim comes from the new helper and executed command path. The existing modules were received normally, and the independent six-patch receiver was also normal Python only.

These results qualify this selected Python/API/CLI source surface. They do not claim the full repository suite, coverage measurement, Python 3.12 execution, other operating systems, package installation, deployment, or an installed application update. Existing scripted CLI tests use disposable local fixtures; the work did not invoke a paid model or alter a live project.

## Evidence and replay

The qualification directory [diff-mail-eof-20261013](qualification/diff-mail-eof-20261013/) contains:

- [receiving.json](qualification/diff-mail-eof-20261013/receiving.json): producer input source bytes, original witness, raw patches, exact harnesses, test receipts, raw stdout/stderr, JUnit records, source patch, and process provenance.
- [independent-source-review.json](qualification/diff-mail-eof-20261013/independent-source-review.json): runtime_quality's authored acceptance of the exact source, test and patch identities.
- [independent-receiving.json](qualification/diff-mail-eof-20261013/independent-receiving.json): the independent original/candidate course, unchanged driver, retained Git patch fixtures and command streams.

Each packet embeds UTF-8 content with byte length, SHA256 and Git blob identity per record. JSON escaping preserves the meaningful trailing space and absent final source newline. The producer packet includes the complete source projection input, so its selected course is reconstructable without relying on an unrecorded checkout.

Producer process receipts retain original witness PID 2599081, original course PID 2666714 and candidate course PID 2761011, each with a final driver exit of 0. Independent original PID 2647999 and candidate PID 2771444 also exited 0; their one expected original refusal remains explicitly recorded.

The harnesses use private work paths and exclusive output names. To replay, verify the embedded hashes, reconstruct their input files in a fresh owned workspace, and deliberately adapt host paths and output names where necessary. Record the modified harness identity and new result separately. Historical receipts must not be relabeled as executions of a later source composition.

The source is delivered for review on a separate branch. Existing parser and consumer owners remain responsible for their other scopes, and repository integration remains with the established integrator.
