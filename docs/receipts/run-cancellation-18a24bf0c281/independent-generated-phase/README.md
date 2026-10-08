# Independent generated-verification cancellation receiving

The frozen TestPilot cancellation change is accepted for this independently chosen later-phase CLI scenario. The same pre-frozen receiver reports **12/14 checks on the unchanged current parent** and **14/14 on the exact candidate**. The two original failures are actual owned work still running at caller exit and a worker continuing after a handshake released only after that exit. The candidate resolves both. No production source was edited.

## Exact source and receiver identity

| Item | Identity |
|---|---|
| Repository and scope | Jacob-Met/testpilot, issue #35 |
| Current canonical parent | `7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e` |
| Parent tree | `ea3f7b4170f1515abb7188d31dc269623b9e0738` |
| Canonical size | 1,063 blobs; the native receiving closure contains 14 exact source/context/test files |
| Frozen native candidate | `649dc7d1fd02493af298876eea0697849404bba9` |
| Candidate sandbox blob | `84330f96ebd71b37dc40575fa2ac59ba53cf2a72` |
| Candidate sandbox SHA256 | `0adf5eb81f8fd15ca09170c5328e6ff4165e1a0f903221b9730de3b480be0b1b` |
| Preserved output-staging loop blob | `ed0f5f7f057c217b931a1756bd679ae087247e0a` |
| Independent pre-execution freeze | `0c5eb9caeaaf4b3d014b1ce65eab21f45f49e546` |
| Independent original receiving commit | `9317bdb3a0fda248ffcbabbe94c401a4558a1b41` |
| Unchanged driver SHA256 | `301391fcb3b08eb41d8958d4305a50e95cdee03127a2584357a69d3e35d893f7` |
| Accepted generated-file SHA256 | `121d3bf5dd29e14e9abff37e5e14526ecad74c0507e8daccb75317e217f1e907` |
| Runtime | macOS, Python 3.12.8, pytest 9.1.1; coverage absent |
| Own native directory | `/Users/me/testpilot-independent-interrupt-18a24bf0c281` |

This original run is on **current 7f44**, including the merged output-staging implementation. It does not relabel the author's earlier f3 discovery. The receiver froze its own fixture, manual lifecycle expectations and driver before executing the original. The original negative result was committed before candidate intake. Candidate bytes were then read from immutable Git objects and verified against the author's frozen 16-file manifest.

All nine package modules are included in each source closure. The remaining files are config, README/workflow context and declared tests/docs. The 14-file original and 16-file candidate snapshots are not replacements for the full canonical repository tree. Root preserves the full tree during integration.

The interpreter was reused read-only with explicit owner authorization. Sources, project fixture, model replies, output directory, temporary roots, worker state and process IDs belong to this independent receiver. Python bytecode writes and pytest plugin autoload were disabled. No provider or live project was involved.

## Why this receiver is distinct

The author interrupted the initial existing-test phase. This receiver interrupts the **generated-test verification phase**, after the actual CLI has run the existing suite and accepted its scripted planning and editing replies.

A small real project exposes `combine(left, right)`. Its existing test passes, and the generated file begins by asserting `combine(9, 4) == 13`. The generated test then launches one bounded worker without creating another process group and records:

- its own PID, parent PID and process group;
- the actual generated file path and SHA256 in TestPilot's temporary repository;
- its worker's PID.

The worker independently records its PID, parent and inherited group, then writes a heartbeat. Reaching this readiness proves that the accepted generated file is actually executing, rather than inferring that generation happened from a returned status or a mock.

The actual CLI invocation uses the existing offline `--backend scripted`, `--rounds 0`, `--timeout 30`, and the declared native interpreter. No model-network request is made. This qualification exercises the existing deterministic backend; it makes no model-quality claim.

## Handwritten lifecycle and preservation expectations

The driver and fixture are unchanged between original and candidate. Before either run, the expectations required that:

1. The actual generated file and input assertion match the frozen reply.
2. Pytest leads its separately created process group, and its one worker inherits that group.
3. A real SIGINT delivered to the owning CLI remains a cancellation and exits within three seconds.
4. No owned pytest or worker process remains running at observed caller exit.
5. Only after observing caller exit does the receiver atomically publish a private handshake; an owned worker must be unable to write a continuation marker in response.
6. The four existing output files retain bytes, inode, permission bits and write timestamps, with no extra publication path.
7. The original project, replies and all captured source blobs remain unchanged.
8. Any receiver cleanup is finite and restricted to recorded owned process/group identities.

The existing output directory contains four explicitly **synthetic regular preservation sentinels**, named `report.json`, `report.md`, `report.html` and `testpilot.patch`. Their contents are not presented as a previous complete semantic TestPilot report. They test the actual admitted filesystem setup: current `run` accepts the existing output directory, reaches generated verification, and publishes results only after the run returns. The files have deliberate read-only/read-write modes and fixed historical write timestamps, so preservation is checked independently of byte equality.

The private handshake is written by atomic replacement strictly after the CLI's observed exit. The worker can write its continuation marker only after reading that complete flag. This is evidence of actual post-cancellation work; a zombie/PID-only observation does not qualify as running work.

## Native result

| Observation | Current parent 7f44 | Frozen candidate 649dc7d |
|---|---|---|
| Native execution start, UTC | 2026-10-08 16:04:54 | 2026-10-08 16:10:49 |
| Actual CLI invocations | 1 | 1 |
| Checks | 12 pass, 2 fail | 14 pass, 0 fail |
| CLI PID / group | 5896 / 5896 | 55620 / 55620 |
| Pytest PID / group | 5917 / 5917 | 55653 / 55653 |
| Worker PID / group | 5918 / 5917 | 55654 / 55653 |
| CLI exit after SIGINT | -2 in 0.284665 s | -2 in 0.281482 s |
| Owned work at parent exit | Both pytest and worker running | Neither present |
| Post-parent-exit continuation marker | Written by worker 5918 | Absent |
| Four preexisting output files | Exact identities preserved | Exact identities preserved |
| Receiver cleanup signal | SIGKILL to proven owned group 5917 | No signal needed |
| Owned work remaining at receiver end | None | None |

The observed durations establish the finite receiving bound; this is not a performance comparison.

In the original run, pytest's parent is already PID 1 when the caller has exited. Its worker then writes the handshake-triggered marker about 0.076 seconds after the caller's observed exit. The receiver records both still-live commands and their group before signaling only that owned group. Both are absent at the end of cleanup.

In the candidate, neither owned process is present at caller exit. The receiver releases the same handshake and observes no continuation. It sends no cleanup signal. KeyboardInterrupt remains visible, no publication-success line is printed, and the same four output files retain their complete before/after identities.

All 14 original and all 16 candidate source/context blobs remain exact after their respective runs. No generated file is added to the original project. The complete process observations, commands, outputs and checks are retained in `baseline-report.json` and `candidate-report.json`.

## Independent source review

Only `testpilot/sandbox.py` differs among the original source/context files. The other 13 remain byte-identical, including the merged output-staging loop. The two added candidate paths are the author's focused test and cancellation documentation.

Removing the 15-line KeyboardInterrupt handler and restoring its docstring reconstructs the **entire original sandbox module byte for byte**, SHA256 `8d5aadafff5188473ec45eb1cd8f01fb562836ff05bf12a27939cde83b33472a`. This verifies that the existing timeout path and remaining module bytes are unchanged.

The added POSIX handler kills the launched group, waits at most one second for its leader, closes its stdout and uses a bare re-raise. It does not convert cancellation into success or timeout, enter another model round, or publish a report. The static result and inspected handler are preserved in `static-candidate-review.json`.

This independent review did not replay the author's interrupt matrix, escaped-pipe case, 13 maintained tests or ordinary successful-run control.

## Evidence custody and qualification boundary

`native-receiving.tar.gz` contains the complete 30-file original/candidate source closure, frozen fixture and driver, native environment and intake records, both raw CLI runs, all process and handshake files, and preserved output sentinels. `raw-manifest.json` binds every regular archive member by size and SHA256. Original failures and green candidate receipts remain separately named and unmodified.

The worker has an eight-second natural lifetime, and both actual runs finish with no recorded owned work remaining. The original cleanup verifies current owned command/group identity before signaling and uses a finite one-second observation window. No shared process, service or remote state is touched.

Acceptance is limited to POSIX SIGINT during communication after successful launch, on the exact qualified sources. Escaped sessions, SIGTERM/SIGKILL behavior, pre-launch interruption, Windows signal behavior and hostile-code containment remain outside this scenario. Later landed source compositions require their own read-only dependency assessment; this packet makes no claim about unreceived later changes.

No source repair is requested. The frozen candidate passes this independent later-phase receiving boundary.
