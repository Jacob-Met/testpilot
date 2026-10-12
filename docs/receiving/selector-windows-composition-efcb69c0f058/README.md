# Combined selector and Windows interruption source

This isolated composition brings two independently reviewed source offers onto
TestPilot main `86617fc90becf79b20d9cf5212b848bff8227147`. It prepares a single
candidate for the integration owner while preserving the newly adopted baseline
runner admission change.

## Inputs and exact preservation

| Input | Commit | Retained contribution |
| --- | --- | --- |
| Current main | `86617fc90becf79b20d9cf5212b848bff8227147` | Baseline runner admission, existing coverage probe and every other current leaf |
| Function-line index | `57ea98545a22974d73d712cf9ae6290bc0f4bbe6` | Exact selector, six maintained regression methods, behavior guide and complete original/independent evidence |
| Windows interruption | `067cf4597c067aad41216ba39c8c29fe3ecd9f3a` | Exact Windows cancellation arm, eight maintained controlled tests and original scope guide |

The two offers share parent `52275f50e672c145d8f69e90cf40948ab28a7d79`. Their
path changes are disjoint. An ordinary local octopus merge completed without
conflicts; it introduces no new production logic.

The complete pre-receipt source tree is
`55e6fa5ce1d72727137493dc1f6ff7642907388e`. [source-scope.json](source-scope.json)
records an exact comparison of every leaf and mode: this tree equals current
main plus the original two offer deltas. Of the 1,517 inherited main leaves,
only `testpilot/diff.py` and `testpilot/sandbox.py` differ. Both whole files are
byte-identical to their respective published offers:

- Selector SHA-256: `60255ce91ded605323ad6d58608ba4681c7c70a1478f1e6da9e89a7675034977`.
- Sandbox SHA-256: `899a454dea73c988645b04cba887b13f7770b824b00f0c0f8be5c179903577e0`.

All three newer main paths—`testpilot/loop.py`,
`tests/test_baseline_runner_admission.py` and
`docs/BASELINE_RUNNER_ADMISSION.md`—retain their exact current-main blobs.
The composition's only further additions are the records in this receiving
directory. Existing guides and historical receipts are not rewritten.

## Focused combined qualification

The actual combined checkout passed **40 tests and 13 subtests** in 4.49 seconds
under CPython 3.12.14, pytest 9.1.1 and coverage 7.16.2. The maintained selection
covers the new selector cases, existing diff and targets CLI behavior, Windows
controlled interruption, the existing coverage probe and the new baseline-runner
admission controls. The latter include real subprocess/CLI failures using a
fresh temporary interpreter without pytest, verifying preserved diagnostics and
zero model calls. The provider is scripted; no external model call is needed.

```bash
python -B -m pytest -q \
  tests/test_function_line_index.py \
  tests/test_sandbox_windows_interrupt.py \
  tests/test_coverage_probe.py \
  tests/test_baseline_runner_admission.py \
  tests/test_diff.py tests/test_cli_targets.py
```

The [focused receipt](focused-receipt.json) records the actual command,
environment, module paths, source/test hashes and exit status. Complete stdout
and stderr are retained beside it. Imports resolved to this combined checkout,
and the selected source and test bytes were unchanged after execution.

This focused run is the combination's qualification. Its Windows cases use
controlled platform/process doubles on Linux; native Windows receiving is a
separate runtime-worker operation against the exact retained sandbox source.
A complete suite was not rerun for this combination. The original selector
offer retains two complete-suite detached-helper observation failures and the
runner limitation that reproduced them; this focused pass does not resolve or
relabel those historical failures. No new benchmark or installed latency result
is claimed here.

## Independent review and delivery boundary

The original selector's independent API/CLI receiving remains under
[its original evidence directory](../function-line-index-efcb69c0f058/README.md).
The [Windows offer review](windows-offer-review.json) is preserved byte-for-byte;
it verifies the retained Windows source and the existing coverage-probe boundary.
Independent review of this exact combination is recorded separately when received.

The current repository has one unchanged workflow, `ci.yml` blob
`86a3236e38155506b5fe6077322d508f7f676649`, which subscribes to main pushes and
pull requests. This contribution prepares an isolated feature branch with skip
markers and does not open a pull request, move main or install a runtime.
Publication receipt, if completed, must identify the exact remote tree and the
all-event Actions result by commit SHA. Default-branch adoption remains with
its existing integration owner.

### Received independent composition review

The [independent review](independent-composition-receipt.json) accepted the
complete source tree `5f2c71beb723d911ef59b9d28cb179bddc0f378e` at
2026-10-12 22:12:33 UTC. It checked all 1,542 candidate leaf bytes and modes,
the exact offer union, the three current-main admission files fetched directly
from GitHub, and the retained focused logs. It reran no tests. The
[complete six-file review packet](independent-composition.tar.gz), including
the reusable reviewer and source inventory, is indexed by its
[member manifest](independent-composition-archive.json). Subsequent edits only
add that exact review packet and this note; production and qualified records
remain unchanged.
