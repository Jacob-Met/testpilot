# Comparison cleanup qualification — dc06b3a12de5

This receipt qualifies the bounded fix for [TestPilot issue 92](https://github.com/Jacob-Met/testpilot/issues/92). The saved-report writer could publish a complete HTML file and then report failure because removal of its private staging path raised an `OSError`. The same cleanup error could replace the original write or publication exception.

## Exact source and ownership

| Role | Git identity |
|---|---|
| Parent / current main at qualification | `478f68adf01658a94a3ede22526da00f580785bd` |
| Parent tree | `ca0756e20da9c87c90ebd24c45ab494bfa31d47b` |
| Reviewed and tested source | `ac0dc717b854d38401c450a855ea2fdb5b6b0d49` |
| Reviewed source tree | `88feab3d499e3cba547a37e4b24de6417525d899` |

The source commit changes exactly three paths: `testpilot/compare.py`, new `tests/test_compare_cleanup.py`, and the existing `docs/COMPARE.md`. The entire nontruncated Git tree was compared: 1,545 parent leaves became 1,546 source leaves; all 1,543 unrelated leaves and their modes remain exact. There are no deletions. The runtime difference is 141 bytes around the final private-stage unlink; restoring that single block reproduces the complete parent module.

The writer now catches only `OSError` from private-stage cleanup. This preserves a completed return or an active primary exception. A non-`OSError` cleanup exception remains visible. A filesystem error may leave the private stage beside the destination. Report admission, rendering, complete-byte staging, fsync, hard-link publication, overwrite refusal, and CLI dispatch are unchanged.

This qualification commit adds evidence only. The immutable source commit above identifies the implementation that was actually tested and independently reviewed.

## Author qualification on Linux

Python 3.12.14 and pytest 9.1.1 were selected explicitly. Each child printed its actual imported `compare.py` path, SHA256 and optimization setting before pytest. The 22-file baseline and 23-file candidate projections contain the complete 14-module package, both actual archived report fixtures, the comparison guide/configuration and the bounded comparison test closure. These are test projections; the full repository suite was not run.

| Course | Observed result |
|---|---|
| Twelve new cases against original source | 7 failed, 5 passed |
| Twelve new cases against candidate | 12 passed |
| Same twelve under real `python -O`, `PYTHONOPTIMIZE=1` | 12 passed |
| Existing comparison and CLI tests against original | 38 passed |
| Existing tests plus twelve new cases against candidate | 50 passed |

The optimized course emits pytest's standard warning that assertions outside rewritten test modules are disabled. The runtime cleanup guard uses no assertions. Source diagnostics confirm `sys.flags.optimize == 1`; this was an optimized interpreter invocation.

The twelve new cases cover cleanup permission/I/O errors after success; a real occupied destination and original exception identity; fsync/link primary errors; an interrupted publication; visible RuntimeError and KeyboardInterrupt from cleanup; ordinary cleanup; an already-removed stage; primary failure with successful cleanup; and CLI success after completed publication. Input bytes, identity, mode and modification time are checked.

A separate author witness uses exact archived `calc_clamp` and `stats_median` saved reports through the actual API. The original outcomes are ordinary success followed by three broken cleanup outcomes; the candidate satisfies all four contracts. The cleanup failures in that witness are scoped fault injection. Its HTML is exactly 45,291 bytes, SHA256 `da933629cf557783466923150546d9e186aa6d1459bc93e0faa6711760f74253`.

The first attempted pytest launch encountered a missing pytest module. It is retained as rejected environment evidence and contributes no test result. A previously cached pytest distribution and its dependencies were copied into an isolated test-only directory; all 492 available RECORD-hashed payloads verified. No project dependency file or installed runtime was changed. Qualified logs, exact witness outputs and replays are retained separately in the receiving packet.

## Independent static and native receiving

Reviewer `dc06b3a12de5/shared_delivery` froze a four-contract oracle at 2026-10-13 00:27:29 UTC before seeing candidate code. Oracle SHA256 is `64bf9e785e88b2b24df283902e98f6f442c1f487c08fceaa47eb7a12c110d203`. The same 14,628-byte replay, SHA256 `5ea5c97be7d9633d0962bc59ae78f15f673ca268bb7b1048179e4dba423a2bb6`, ran against both exact source versions.

The reviewer separately checked the immutable commit, all three source blobs, full-tree conservation, all new tests, and guide semantics. Static disposition is ACCEPT for this scope.

Native receiving used Python 3.13.7 on the Mac as uid 501. Its first two controls use actual hard links and actual directory mode 0500; an actual unlink returned errno 13. Owned directory modes were restored in `finally`.

| Independent contract | Original | Candidate |
|---|---|---|
| Complete publication followed by real cleanup permission denial | Raises cleanup PermissionError despite complete HTML | Returns the successful output Path with exact HTML |
| Occupied output followed by real cleanup permission denial | Masks the real FileExistsError | Preserves the same original FileExistsError and sentinel |
| Non-OSError cleanup RuntimeError | Remains visible | Remains visible |
| Ordinary publication and stage removal | Pass | Pass |

Both courses preserve all 16 selected package/report files byte for byte, including inode, mode and nanosecond modification time. Native output has the same 45,291-byte length and SHA256 as the Linux witness. Process 32985 (original) and 41103 (candidate) both completed with exit 0 after checking their expected contract patterns: 2/4 and 4/4 respectively.

The three independent JSON files in this directory are the reviewer's original bytes, copied without parsing/reserializing. Integer nanosecond timestamps retain exact precision.

## Replay and interpretation

From a checkout of the reviewed source:

~~~bash
python -B -m pytest -q -p no:cacheprovider \
  tests/test_compare.py tests/test_compare_cli.py tests/test_compare_cleanup.py
PYTHONOPTIMIZE=1 python -O -B -m pytest -q -p no:cacheprovider \
  tests/test_compare_cleanup.py
~~~

For the original regression, place the new test file unchanged into a separate parent checkout; the expected result is seven failures and five passing controls. The native permission replay is distinct evidence and has its own platform/permission applicability check.

The qualification does not execute saved tests, call a provider, assess generated test quality, perform a browser review, or claim a full repository suite. It does not guarantee power-loss durability, directory race immunity, or automatic removal of a stage whose unlink fails. Existing source owners, main, runtime configuration and workflows remain outside this change. Current workflow events were checked before publication; the isolated source proposal uses supported skip markers and its Actions count is checked separately.
