# Received toolkit refresh

This composition receives current main `cea306b8ccdf4ff060d1dc617daf26ebd5c05257`
and the accepted toolkit/example chain `4919222c61347af3e48e255b7623cf42c6946dfe`.
Current main is the first parent. Its recheck implementation, README, maintained
tests and unrelated source remain exact. The only overlapping runtime path is
the CLI; its diff from current main consists of the three accepted progress
spans. The configuration helper, bounded sandbox and progress module retain
their previously accepted bytes.

## Use

Use Python 3.12 or later with pytest 8 or newer. This refresh was received with
Python 3.12.14 and pytest 9.1.1. From this repository root:

```sh
python -m testpilot --version
python -m testpilot run --help
python -m testpilot recheck --repo /path/to/project \
  --report /path/to/saved/report.json --out /path/to/new-recheck
```

The package version remains 0.1.0; use the commit and file hashes to identify
this composed source. The version query finishes before provider configuration
or project work. Root START_HERE.md gives the complete scripted
generation → patch adoption → native recheck example.

Recheck executes the exact retained tests with zero model calls. It stages
Markdown, JSON and HTML before exclusively creating the final output directory.
A staging write failure leaves that final destination absent and available for
an explicitly requested corrected retry. The command does not retry
automatically. Parent directories may be created. Later individual move
failures can still leave a partial final directory; occupied paths are not
silently replaced. This is not an all-or-nothing publication guarantee.

## Receiving

The maintained course passed 24 cases plus 12 subtests: current-main
version/staging/HTML cases and existing progress CLI interactions. An earlier
FD-capture attempt exited 120 with empty output and supplies no test result.
The uncaptured (-s) execution is the accepted receipt. No full-suite rerun is
claimed.

Independent actual CLI receiving completed native pytest before injecting a
real /dev/full ENOSPC only at the JSON write. The old toolkit claimed a partial
final directory and refused an explicit retry to that destination. The refreshed
source cleaned staging, left the final destination absent and then passed one
retained native test with zero model calls on an explicit retry. Three actual
native pytest executions occurred across the two sources. Original project,
saved report and source bytes remained unchanged.

The new version command succeeded despite unusable provider settings; the old
toolkit refused --version. Progress remains available with its exact accepted
implementation. Earlier broader generation, scientific and configuration
courses retain their original attribution.

## Optional comparative receiver

The included comparative receiver requires POSIX /dev/full and an owned /dev
temporary directory. It is optional evidence; ordinary users can use recheck
directly. With the previous accepted toolkit materialized separately:

```sh
python -B docs/receiving/toolkit-refresh-7cb7e049e2c0/receive_testpilot_refresh.py \
  --baseline /path/to/old-toolkit --candidate . \
  --python /path/to/qualified/python --out /path/to/new-receiving
```

No installed-consumer, Windows or fresh full generation/scientific execution is
claimed here. Earlier immutable packets and examples remain intact. Source
delivery uses an inert feature branch, without a PR, main/tag update, workflow
edit or Actions execution.
