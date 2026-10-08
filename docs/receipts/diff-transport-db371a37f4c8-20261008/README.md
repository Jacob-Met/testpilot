# Raw diff transport: native receiving

Contribution: [TestPilot #25](https://github.com/Jacob-Met/testpilot/issues/25), estate-db371a37f4c8 / product_execution.

The CLI's Git and saved-file routes rejected real diff bytes from valid Latin-1 and Windows-1252 Python sources. Both commands now share a raw input loader: UTF-8 remains UTF-8, undecodable bytes use `surrogateescape`, and the existing universal-newline behavior is preserved. Binary stdin uses the same path; text-only direct callers remain supported. The selected Python file still passes through the existing `tokenize.open` decoder and containment/AST rules.

Only `testpilot/__main__.py` changes among existing product files. The [scoped patch](source.patch) adds `_read_diff` and replaces the two duplicated acquisition blocks. It retains the exact Git argument list, parser options, selector, model/pytest execution and report behavior.

## Source identities

- Original selected main: `3e745e6b6a2f7e383fc6b43f12e69f7a221fb051`; tree `56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd`.
- Original CLI Git blob: `fc455a5b4866fd27503585a50903a80ff179513e`; SHA-256 `901d0a25802454296107fa6149fc8375b4acc58e144d0a8bd5a4656483ce2bf4`.
- Candidate CLI SHA-256: `83caf8df097902120a0cfbd6adb897d5b6be7ba2407b0217606e7038599b5a5f`.
- Frozen maintained regression SHA-256: `5748cd3aafbd5aa032b98d531a9091d4a91becdce187a514dafffcc271173bab`.
- Frozen standalone receiver SHA-256: `80c669c41d4e6f8903142eb98d5bbfffbad317e81f3881d0b6988ab997c56828`.

Git HEAD in the standalone receiver's `source` field identifies its selected parent. The `source_files` hashes identify the actual working-tree inputs, including the candidate CLI. They must not be interpreted as an assertion that the uncommitted candidate was the parent commit's original source.

## Qualification

| Native surface | Original source | Candidate |
| --- | --- | --- |
| Same 18 actual CLI children: UTF-8, Latin-1 and Windows-1252 through Git/file/stdin | Ten succeed; eight legacy Git/file calls fail | All eighteen succeed; each run reports one executed generated case |
| Seven frozen regression methods | Three pass; four affected methods contain twelve failing assertions/subtests | Seven pass, including strict stdin, mixed encodings, quoted path, exact patch application and receiving pytest |
| Full configured suite on original selected parent plus CLI change | Not broadly rerun | 218 passed, 18 subtests passed, four skipped, two fixture failures |
| Same two failing filesystem fixtures on exact original source | Both fail with APFS Errno 92 before product invocation | Same failures in full suite |

The full native run is not a green-suite claim. macOS refused the inherited tests' raw `0xff` filenames with `Illegal byte sequence` during fixture creation. The exact original 11-file source/test selection reproduces both failures. The installed native runtime is Python 3.13.7 with pytest 9.0.2; optional coverage is absent. Logs, receipts, runtime identity and original failure outputs are retained unchanged.

## Fresh main composition

Main advanced to `ca3d4a83c552ed9c8ea1f1c4e81510111d2c9b1e`, tree `92a8b55034840ba1c84eb97705cb9447c22c3ca8`, incorporating PR #23's generated-collection helper. The complete tree has 798 leaves; its only changed inherited production file is `_pytest_generated.py`.

A separate thin native directory materialized all 91 selected runtime/test/eval/config inputs from that exact parent. Applying the same scoped patch produces the identical candidate CLI bytes. Every other selected original input is preserved. The new seven methods and existing eight target-preview methods pass: **15 tests and 18 subtests**, zero failures/skips, with all receiving inputs unchanged. This focused gate does not relabel the earlier full-suite execution as a run on the newer parent.

## Reproduce and inspect

```sh
python -B -m unittest discover -s tests -p test_cli_diff_transport.py -v
python -B docs/receipts/diff-transport-db371a37f4c8-20261008/receive_diff_transport.py CHECKOUT NEW_OUTPUT_DIRECTORY
```

The native receipts record their exact commands. Use the project's prepared Python environment with pytest and a fresh writable output directory. `original-cli-transcripts.json` and `candidate-cli-transcripts.json` retain exact source/diff/stream/artifact bytes as base64, alongside their original JSON receipts. The standalone receiver writes only authored disposable repositories and uses ScriptedModel. The maintained module additionally verifies actual `git apply --check`, application, receiving pytest, and original project-byte preservation.

## Independent receiving

Root accepted the exact candidate CLI after an independent real Git fixture combined an unquoted UTF-8 Japanese filename with a CP1252 euro byte in the changed hunk. Under a strict CP1252 console the original saved-file route exits 2 and the original stdin route silently returns an empty target list; both candidate routes select the correct function, line and source. A real candidate stdin run under a strict UTF-8 console passes two tests, including one generated case.

The [independent disposition](independent/RECEIVING.md), original failed receiver and corrected receiver are preserved byte for byte. The first scripted receiver used unsupported tilde fences; its resulting no-tests report then met an existing narrow-console output limitation. The corrected harness uses documented backtick fences and UTF-8 for the human-readable run output, with no product source change. The four preview controls retain CP1252. Final independent receipt SHA-256: `fe66787b444ac8dc37a4803dc96c258c4a040dfa752de9311e5af602b5827acd`. The independent manifest SHA-256 is `4438392e56376c232834328c2dc11c6daa1bc399c691fca4550ac23df8546433`; all 23 listed files and that manifest are retained, including raw CP1252 source and diff bytes.

## Publication composition

Publication is composed over direct main `aded01e114080c0bbc9d273f240c6bc2c5119694`, tree `72d8060994dc1a01be240121cecd146c2bf622b3`, with 908 leaves. Since the focused native gate's `ca3d4a83` parent, PR #24 adds HTML reports and PR #22 preserves fenced Python and physical patch lines: only README.md and testpilot/loop.py change among inherited files. The original CLI blob remains exactly `fc455a5b4866fd27503585a50903a80ff179513e`, so the accepted scoped patch produces the same candidate bytes. All current reporting, fenced-code and patch-line code, tests and receiving evidence are preserved.

`publication-composition.json` pins the source delta, and `publication-loop.patch` records the report and Python-content changes inspected for compatibility. This source check does not relabel earlier native execution as a run on the publication parent. Exact-head hosted CI remains a separate final integration gate.

No provider, installed-runtime, deployment or live-account result is claimed here.
