# Saved added-line coverage: qualified source handoff

The reader identifies exact changed lines missing from a saved TestPilot report's retained final coverage. It does not rerun generation, tests or repository code. Unrepresented lines remain distinct from lines recorded as missing.

**Disposition:** qualified source handoff. Pull-request and canonical main integration remain held while existing CI would start GitHub Actions. No workflow or merge gate is changed.

## Use and maintained verification

From the checkout with Python 3.12 or later:

~~~sh
python3 -B -m testpilot.coverage_gaps --report saved/report.json --output gaps.json
python3 -B -m unittest discover -s tests -p 'test_coverage_gaps.py' -v
~~~

The output must be new and its parent must exist. Omit --output for JSON on stdout. The API is analyze_report(report: dict) -> dict, with ReportError(ValueError) for invalid or over-limit evidence. The [command guide](../../COVERAGE_GAPS.md) defines complete semantics.

Only final.coverage.files supplies coverage states. Exact recorded labels remain distinct across case/slash variants and are never opened. Unique file/changed-line pairs become executed, missing, not_represented or unknown. Not represented does not establish non-executable, excluded, covered or safe-to-ignore status.

Counts deduplicate overlapping functions while preserving ordinals, order and empty changed-line records. The percentage uses only changed lines present in retained executed/missing arrays; it is not whole-project coverage. Missing evidence and empty denominators remain null.

The authored fixture has six unique lines: one executed, three missing and two unrepresented, yielding 25.0% among known executable lines. It is synthetic reader evidence. A separate genuine previously produced report remains in native receiving custody.

## Exact source and receiving

Base commit: 906ce149fba770a62c9f5f2fbc1b7238b949d423. Base tree: 626557015edc297dfc6ba00028a8de64f7dfdfa9. The four product additions compose to 9ac14779a83ec9d03d49ab2621895f0f26e4c731 before these derived handoff documents.

Fourteen current base files were verified against Git blobs. Complete metadata covers 1,499 existing leaves and 407 reconstructed directories. Existing initializer, CLI, README, producers, selectors, report writers, dependencies, tests and source owners remain unchanged. Exact four-file fingerprints appear in PUBLIC_QUALIFICATION.json.

| Gate | Actual outcome |
| --- | --- |
| Author, Linux/Python 3.14.4 | 16 methods; seven joined CLI children; actual Python exit 0 |
| Original independent gate, Linux/Python 3.14.4 | 122/122 observations; exit 0; 7.07 seconds |
| Separate before-parse witness | Over-8-MiB input refused with exit 2; no decoder call or output; input unchanged |
| Separate integer follow-ups | 2/2 pass: CLI exit 2 and API ReportError; digit limit 4,300 unchanged |
| Final Mac attempt | Memory-floor stop before candidate writes or execution |

The original 122 observations were frozen before candidate exposure. They cover manual classifications, malformed shapes, exact labels, empty/unavailable populations, inclusive and one-over bounds, raw-entry accounting, input/existing-file/symlink/hardlink protection, actual CLI results and a real nonzero broken pipe. Integer cases are explicitly later source-review follow-ups, separate from that blind gate.

Input is capped at 8 MiB, output at 16 MiB, functions/files at 4,096 each, labels at 4,096 characters, and raw line entries at 100,000 before deduplication or association. The API enforces the output bound before return. I/O failures remain nonzero; partial delivery is not promised to roll back.

The author's actual Python result is durable. Its outer transport wrapper session later became unavailable; that wrapper exit is unretained and distinct from the Python result.

## Preserved failures

Version 1's author fixture expected seven unknown lines instead of the correct deduplicated six. The failed receipt remains; only the stale expectation changed.

Version 2 passed 13 maintained methods but scored 121/122 on Mac because the API omitted the output bound. Version 3 added the serialization bound and passed 14 maintained methods plus the original 122 Mac observations.

Later source review found that version 3 leaked builtin ValueError for a 4,301-digit JSON integer and when serializing an otherwise valid empty-changed function with a very large positive span. Both actual failures remain separate.

Version 4 changes only JSON parsing/serialization exception boundaries, two maintained regressions and one documentation paragraph. ReportError identity, output data, classifications, limits and I/O behavior remain intact. The interpreter integer limit is not changed. Final receiving uses unchanged expectations on Linux after the Mac admission stop; earlier Mac results apply to their exact earlier versions.

## Original evidence and this summary

The original producer archive is 1,438,891 bytes, SHA-256 aeb244f273e24546b5dd9d44cc42533299a39b31a000c84a69329f3751d39561, with 148 members. It retains four source histories, current carriers, donor/report, contracts, author streams/receipts, recipes, negatives, root review and the independent packet.

The independent archive is 629,401 bytes, SHA-256 225fd3ed9e882893038645c59ad211ec08eda89e4d4c2148bfd05b9c8310341d, with 122 top-level members and 242 nested closed Mac members. CRC, member and native-byte checks passed without repeating product tests.

Full 16 MiB stress stdout is not retained. Captured length and SHA-256 matched an independent expected hash, with prefix/suffix retained. Normal CLI streams and stderr remain in native custody.

Original archives and runtime paths remain unchanged in ordinary estate custody. [PUBLIC_QUALIFICATION.json](PUBLIC_QUALIFICATION.json) is a newly derived sanitized summary, not an original receipt or replacement archive. Raw archives and unrelated coordination content are not included publicly.

## Integration boundary

Existing ci.yml is 586 bytes, blob 86a3236e38155506b5fe6077322d508f7f676649. It triggers on pushes to main and pull requests. A unique non-main branch without a PR follows existing filters; ref and run count are checked after publication.

Opening a PR or merging main remains held by the current no-Actions instruction. An unrun required gate is not a pass. Qualified source availability does not establish main integration, installation or runtime adoption.
