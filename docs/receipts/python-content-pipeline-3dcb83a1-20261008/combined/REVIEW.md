# Independent acceptance: valid Python through the TestPilot pipeline

Accept the composed source on current-main parent `f1a8c8e6e7533eac5a23864ef56f4e769d0d9125`:

| Runtime file | Git blob | SHA256 |
| --- | --- | --- |
| diff.py | `ea74d79d2789919a7a87bff745e3b6bed12e38a7` | `36d5c4d913775d0176ec9c63196beb33042227cfd7930c7e10db6afe47daa278` |
| loop.py | `fc2fa150c7e9c6583f137acc8eb958a92074ac3b` | `05dfdfe3b63f5676d14f3bac1c0dfb24b50d0d3bef658a2d6781a953807ac15f` |

Independent AST comparison confirms changes only to `parse_unified_diff`, `functions_touching`, `_FENCE` and `make_patch`. The composed fence and patch functions match the separately accepted candidates. Every other AST node in both modules, and the four other runtime modules, match current main.

## One combined public consumer

The independently authored executable `receive_combined.py` ran once, SHA256 `0a666413ecb68656346809a2f705e9d8ea32df1a6fbd29dca2c0f9474ac6323b`.

It creates a real committed Git fixture, changes a Python return literal, supplies two authored ScriptedModel response files, then launches the unchanged public CLI as a subprocess with `--backend scripted --git-base HEAD --rounds 0 --timeout 10 --python`. The original source includes a raw Unicode line separator; the changed value and generated assertion include inline triple backticks and a raw paragraph separator. The requested generated-test filename already exists.

All fifteen recorded receiving assertions pass:

- CLI exit 0 and report status passed; two generated tests and three native pytest cases pass.
- The selected source remains complete, with exact function identity, lines 4–5 and changed line 5.
- The original test filename is preserved and the new tests use the established alias.
- Git patch validation and application both return 0; the applied generated file exactly matches the authored model reply bytes.
- A fresh native pytest run in the receiving repository passes all three cases.
- Original source and existing tests remain unchanged before and after controlled patch application, and all ten frozen source/config/regression files retain their bytes.

The real CLI default coverage path ran and its result is retained, rather than disabled or inferred. This receiving check inspects selected source in the public report; separate selector receiving had already checked the actual planner input.

## Separate negative controls retained

The three isolated reviews remain separate, frozen evidence:

- Selector: three methods, original seventeen failed assertions within subtests, candidate no failures. The original scripted pipeline can pass while sending truncated planner source.
- Patch emission: one method, original passed generated tests but emitted a corrupt patch; candidate applies exact bytes and passes receiving pytest.
- Fence boundaries: two methods, original two failures and truncated generated Python; candidate preserves two CRLF/mixed-fence blocks and passes the actual TestPilot consumer.

These independent counts are distinct from the author's focused regression counts. No full-suite repetition was needed for the combined receiving case. No provider or installed-runtime operation occurred.

The prepared source remains unmerged and unpublished while GitHub's shared content-creation block is active. The root worker owns the next normal probe and source release; this acceptance does not imply a hosted-CI result for this candidate.
