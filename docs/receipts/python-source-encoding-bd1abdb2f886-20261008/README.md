# Receive Python source using its declared encoding

Owner: `chatgpt-astra-bd1abdb2f886-20261008 / estate_source`.
[Existing issue coordination](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6057237310).

## Result and source scope

Selected `.py` files are now read with the standard library's
[`tokenize.open`](https://docs.python.org/3/library/tokenize.html#tokenize.open),
which detects Python's UTF-8 BOM and first/second-line encoding cookies.
The existing resolved-path containment and `is_file` checks still run first.
The file closes before the existing AST selector receives the decoded text.
The change consists of one import, one docstring sentence, and the source read
inside `changed_functions`; all other runtime behavior is inherited.

The original forced UTF-8 read rejected importable BOM, Latin-1 and CP1252
modules, and could ignore an invalid encoding declaration. The revised read
follows Python's strict decoding rules without replacement or encoding guesses.
The regression compares the result with actual Python imports of the authored
files, using their real Git-generated diffs and exact function/line identities.

This scope decodes selected Python source files. The CLI's existing UTF-8
diff-text transport remains unchanged. The authored legacy-encoded fixtures
put non-ASCII bytes outside the changed hunk's context, so their actual Git
diffs are valid UTF-8. These results do not establish arbitrary diff-byte,
filename-byte, provider or installed-runtime support.

## Exact source and receiving environment

Source base: `f350150259c00dd25c43a95d65157022612d15a8`.
Base tree: `1fabd676af1bf4cc8c396fc1962b2ea1bc618b66` (203 leaves).
Original `testpilot/diff.py`: `425d0712b18a6a72226399a2f9d704193ace1133`.
Accepted runtime blob: `d7d4c194c3730e4c7a8093b485491a7873afe814`.
Accepted runtime SHA-256:
`d5fce39356d8fba48557907184b18d55796aa22dce71072cb4b3ec89423d037c`.
Frozen regression SHA-256:
`85196e144916098af0fe677f01382eeb48c6f175008c76446756c438ee741b89`.

All 84 current runtime, test, evaluation-fixture and project-metadata files
matched the pinned Git tree before editing. The candidate preserves the other
83 files exactly. Historical receipt documents were not all copied into the
native receiving directory; publication inherits and verifies the complete
Git tree separately. No AGENTS.md or CODEX_HANDOFF.md exists in that tree.

Native environment: Python 3.12.14, pytest 9.1.1, coverage 7.16.2,
Git 2.51.1, Linux 6.18.44 x86-64 with glibc 2.39.
Tests used the already installed Python environment, an isolated memory-backed
source directory and owned temporary files because the shared disk was full.
Windows was not executed; the new symlink control explicitly marks its
optional Windows privilege requirement.

## Frozen regression and full suite

The complete 15-case new module was written and run before editing runtime
source. Its bytes were then retained unchanged:

| Receiving set | Original | Candidate |
| --- | --- | --- |
| New encoding and open-order module | 8 fail, 7 pass | 15 pass |
| New module plus all existing diff, path, containment and match cases | — | 81 pass |
| Complete configured current repository suite | — | 144 pass in 44.72 s |

There were zero skips in these Linux runs. The original failures comprise six
legal source encodings rejected by the old reader and two invalid declarations
that the old reader incorrectly admitted. Valid default/declared UTF-8,
conflicting BOM/cookie and invalid default-byte controls retain strict behavior.
The accepted cases cover BOM with/without a matching cookie, first/second-line
Latin-1, CP1252, CRLF, exact decoded function source and unchanged original bytes.

Three audit controls observe real Python `open` events, across both old and new
read mechanisms: parent traversal, an absolute path and an outward symlink
are refused before any source open. A following valid in-repository selection
produces an observed open, so the observation is not an unused mock. Each
audit hook is disabled in a `finally` block after its scoped observation.

The test commands used `python -m pytest -q -p no:cacheprovider`, an owned
`TMPDIR`, `PYTHONDONTWRITEBYTECODE=1`, and a distinct `--basetemp` for each run.
The original run selected only `tests/test_python_source_encoding.py`;
the full candidate run used the repository's unchanged pytest configuration.
Raw outputs are retained beside this note.

## Public CLI, real pytest, coverage and patch receiving

`check_encoded_workflow.py` is a standalone authored receiver. It creates two
real Git repositories, writes BOM and second-line Latin-1 Python source,
commits the original, changes the return value, and supplies the actual UTF-8
Git diff to `python -m testpilot run` with the existing ScriptedModel backend.
The baseline and candidate use byte-identical source, existing tests and diffs.
Both actual Python imports return 17 before TestPilot is invoked.

For each fixture the original exits 1 with a source exception and no report.
The candidate exits 0, writes one new generated test, and runs two passing
pytest tests. Changed-line coverage goes from 0% to 100%. The two existing
planner/editor calls are scripted; no external model is contacted. Each patch
passes `git apply --check`, the original source/test hashes stay unchanged,
and the generated file remains absent from the input repository.
The complete JSON receipts retain command lines, original errors, Git diffs,
candidate reports, source hashes and generated patches.

## Independent disposition

The root agent independently read the exact runtime and the entire frozen
regression module, including current parser/containment context, and accepted
the change with no blocking source defect. It verified that native source
decoding follows resolution/containment and that strict errors and AST
path/line behavior are retained. The native commands above were executed by
the implementation/receiving lane; this separate disposition is source review.

`receipt.json` records file identities and verification results. Repository
status and required-check readback at integration remain distinct from native
receiving; this packet does not imply a hosted-CI result.
