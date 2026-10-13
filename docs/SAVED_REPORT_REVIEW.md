# Reopen a saved generation report

An older TestPilot output directory may contain `report.json` and
`testpilot.patch` without a browser report. Open that saved pair as a new
self-contained review from a Python 3.12+ checkout:

```sh
python -m testpilot.saved_report --report eval/results/calc_clamp/report.json --patch eval/results/calc_clamp/testpilot.patch --out calc-clamp-review.html
```

Open `calc-clamp-review.html` directly in a browser. It uses the existing
native report renderer: recorded results, generated source, repair history,
selected functions, coverage, and the model ledger. Its new opening section
identifies the exact input bytes by their lengths and SHA-256 digests. The
existing **Download exact patch** and **Download report JSON** controls retain
the selected files byte for byte, so both downloads travel with the page.

The command reads saved artifacts and creates a review. It does not call a
model, execute tests, apply a patch, or recompute the recorded results.
Recorded success and suspected-bug diagnoses remain historical observations.
Use the existing `testpilot recheck` or `testpilot regression` commands when
you intend to execute retained tests under their respective contracts.

## Choose the pair explicitly

Both `--report` and `--patch` are required. The command does not search a
directory, choose the newest report, regenerate a patch, or assume that files
with sibling names belong together. The supplied patch must match the saved
report's complete `patch` text under one of these writer forms:

| Form | Exact required patch bytes |
| --- | --- |
| Recorded UTF-8 | UTF-8 encoding of the report's `patch` string. |
| Native Windows newline expansion | Replace every LF in that string with CRLF, then encode as UTF-8, matching the generation writer's native Windows text conversion. |

The second rule is literal newline expansion, including when an original CR
already precedes an LF. No other newline normalization, trimming, Unicode
normalization, patch parsing, or equivalence rule is used. An empty recorded
patch matches an empty file. If both forms coincide, the receipt labels the
match as recorded UTF-8. The comparison can be exercised on any operating
system; it does not establish that a Windows runtime was tested.

The HTML shows the report's recorded patch text and embeds the selected
patch bytes. Its opening section and command receipt name the matched form.
Hashes identify the bytes actually read; they do not authenticate their
author, prove the report's internal consistency, or establish that the
tests passed.

## Supported input and output

Inputs must be regular files. The JSON report has a 16 MiB byte limit and
the patch has a 4 MiB byte limit. Source admission checks the opened file
descriptor and reads only the explicit bound. On POSIX, opening a substituted
FIFO does not wait for a writer. Reads follow a source symlink to a regular
file, and retain the bytes read from that opened descriptor. Concurrent
changes to its contents are not coordinated into an atomic source snapshot.

The consumer accepts the unversioned generation-report layout used by the
maintained renderer, including the repository's archived examples. It
rejects invalid UTF-8 or JSON, duplicate object keys, non-finite numbers
(including exponent overflow), unsupported report containers, incorrect
boolean types used for rendering decisions, and layouts the native renderer
cannot display. It is a bounded rendering consumer, not a general report
schema validator: it does not reconcile recorded counts, source identities,
diagnoses, or ledger totals. Recheck and regression reports have different
formats and are not accepted here.

`--out` must name a new file in an existing directory. Existing files,
directories, and symlinks are refused, including either source path. The
complete HTML is written to a temporary file in that directory, then linked
exclusively to the chosen name. A concurrently occupied final name is
preserved. This publication requires hard-link support on the destination
filesystem; an unsupported operation refuses without replacing an existing
file. A failure can leave an owned temporary file if cleanup also fails; its
path is reported. The command does not synchronize concurrent source writers
or promise survival of filesystem or system failure.

On success, stdout contains one JSON receipt with the output digest, both
source digests, matched newline form, and recorded status. Exit 0 means a
review was created, regardless of the recorded test outcome. Input or output
refusal returns exit 2. If a complete review was published but its temporary
hard link could not be removed, the success receipt includes a
`cleanup_warning`. Preserve that receipt if you need to remove the named
temporary link later. A console write failure is a separate process error;
it does not roll back an already published page.

## Qualification

The saved-input tests receive the actual archived `calc_clamp`,
`stats_median`, and `durations_parse` pairs through the command, under normal
and optimized Python. They compare exact embedded downloads, source/output
digests, deterministic pages, and the unchanged native renderer body. They
also exercise native newline forms, unavailable results, literal markup and
Unicode, mismatched pairs, malformed inputs, occupied outputs, publication
races, limits, and POSIX FIFO inputs. The native renderer and current
generation writer are unchanged.

```sh
python -m unittest discover -s tests -p test_saved_report.py -v
```

This command is separate from the main `testpilot` subcommand parser and
requires no additional runtime package for rendering. No provider, hardware,
native installed application, or physical-model result is qualified by these
saved-artifact checks.
