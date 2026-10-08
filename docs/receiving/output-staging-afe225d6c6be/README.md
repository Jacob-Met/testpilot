# TestPilot output-staging qualification

Status: author-qualified source frozen for independent receiving under [issue #29](https://github.com/Jacob-Met/testpilot/issues/29).

## Result and scope

The native writer now prepares the complete patch, JSON, Markdown and HTML, admits the observed final paths, and stages all four files on the output filesystem before replacing any final file. A preparation, admission or staging failure leaves the previous final artifacts unchanged. Symlink, directory and other non-regular final paths are refused. Existing regular permission bits, artifact names, successful bytes and return mapping are retained.

Only `testpilot/loop.py` imports and `write_outputs`, the new `tests/test_output_staging.py`, and one README section change. The integrated fence extraction, physical patch lines and raw CLI diff transport remain exact, as do the renderer, generation/repair, model, sandbox and collector. The retained-test recheck and comparison owners retain their separate work.

The staged UTF-8 byte preparation uses Python's own text stream with its native newline behavior. HTML is rendered from the same prepared JSON and patch bytes that are written as final artifacts. The compatibility oracle executes the former writer's actual text-file operations, including mixed LF/CRLF/CR and literal Unicode inputs.

## Source provenance

The discovery witness is pinned to main `e1d87442eeecc8cf1b44ee3547849d5c1d030876`, tree `1466e2d4a2a1f2ce4fe5293e55e0b7f7e0b3797a`, writer blob `5d58f2dc991e3cdb98f476e08133048b02f91ca4`.

Implementation and repeated native baseline use actual current main `e2285d68b2ea5eb2158c0a7e0d936ce5d56f8ff5`, tree `22da6a890c2befaf72d3826103538491b07793df`, writer blob `3057a9c7c9777a23e73f8b56979670001eb512fd`. The complete canonical tree has 955 leaves. The executing native closure contains all 82 production Python, maintained test, eval-fixture/harness and package/readme/license files required for these controls. All were checked against their canonical Git blobs. Unrelated web-demo and archived receipt files were not materialized or executed.

The candidate adds one maintained test file, for 83 native files. It is delivered as three path-scoped changes against the canonical base, with a separate exact baseline archive for native receiving. There is no synthetic Git commit or claim to have executed all 955 repository leaves. A separate `git apply --check` and application reconstructed all 83 candidate files exactly.

Candidate writer SHA-256: `dde4ee52e0a1fabded9902137ede6dd68aa17f6542c316e5d134b8510495170b`; Git blob: `ed0f5f7f057c217b931a1756bd679ae087247e0a`. The complete three-file freeze and unchanged native paths are in `source-freeze.json`.

## Concrete native failure and changed-input controls

The probes call the unmodified public `LoopResult`, `make_patch` and `write_outputs` routes with authored report data. These reports explicitly say `no_tests`; their static authored definition count is not presented as a generated-test execution. No model, account, provider or external network is called.

Only a newly created owned child receives a 4,096-byte POSIX file-size limit. SIGXFSZ is ignored in that child so Python receives the real `OSError(EFBIG)`. The parent and other processes retain their limits. Every output directory is newly created for the probe.

| Actual control | Original current writer | Frozen staged writer |
| --- | --- | --- |
| Unrestricted changed review | All four artifacts update successfully. | All four artifacts update successfully. |
| Larger patch reaches file-size limit | Old 237-byte patch is replaced by a truncated 4,096-byte new patch; old JSON/Markdown/HTML remain. | Error propagates; all four prior artifacts remain byte-identical. |
| Limit reached only during HTML output | First three artifacts change; old 10,875-byte HTML is truncated to 4,096 bytes. | Error propagates; all four prior artifacts remain byte-identical. |

The original discovery receipt remains unchanged. The current-base and candidate native receipts record each child exit, its actual error, exact before/after sizes and hashes, and the changed artifact set. The candidate failure directories contain only their four original final artifacts after cleanup.

## Maintained test receiving

Python 3.12.14, pytest 9.1.1 and coverage 7.16.2 were reused read-only from an existing native environment. All source/build/test temporary files were in an owned private `/dev` session. Bytecode and unrelated automatic pytest plugins were disabled. There was no dependency installation.

The candidate reports **24 new focused tests passed**, plus **75 inherited tests and 12 subtests passed**. The same 75 inherited controls passed on the exact current baseline before edits. The focused results include all four directory destinations, live and dangling symlinks, a bounded native FIFO child, existing private/group-read permission bits, deterministic legacy byte parity, new nested output directories, unencodable patch and report/HTML preparation failures, both real file-size failures, and propagation of an injected later replacement refusal. The last control intentionally records the partly published set allowed by the documented boundary.

The inherited set covers HTML/data-download semantics, filesystem/text encoding, native loop execution, the recently integrated fence/physical-patch fixes and raw CLI diff transport. This is a focused regression qualification, not a claim that the entire repository suite or web demo was rerun.

Reproduce the maintained checks from an isolated current source checkout:

```sh
python -B -m pytest -q -p no:cacheprovider tests/test_output_staging.py
python -B -m pytest -q -p no:cacheprovider \
  tests/test_html_report.py tests/test_report_text_encoding.py \
  tests/test_loop.py tests/test_fenced_code_boundaries.py \
  tests/test_patch_physical_lines.py tests/test_cli_diff_transport.py
```

The supplied native probe scripts each take one fresh output-root argument. Use the corresponding baseline or candidate package on PYTHONPATH and an owned writable TMPDIR. The size-limit probes and FIFO control require POSIX. The newline oracle was executed on Linux; this packet makes no claim of a Windows run.

## Publication boundary

Individual final replacements occur only after all four staging writes and permission updates finish. Errors after replacement begins still propagate and can leave a mixture of old and new final files. There is no multi-file rollback, whole-set crash atomicity or concurrent-writer guarantee. No directory swap, lock service or recovery framework is introduced.

The initial shared source-copy attempt ran out of space before native execution. A later private materialization helper initially computed the Git header with a literal backslash-zero, failed its first hash assertion, and wrote no source file. Its header calculation was corrected to a NUL byte before materializing and verifying the complete 82-file native closure. These are retained setup limitations, not product failures. All reported native baseline and candidate tests ran only after exact source verification.
