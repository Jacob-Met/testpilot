# Execution snapshot: author evidence

Issue: https://github.com/Jacob-Met/testpilot/issues/50

This packet preserves a demonstrated CLI defect, the first candidate's native
qualification, and a later source-only amendment. Those are separate claims.

## What the native receiver established

The original source is `cec50d8df4499ba509615e179d82ef3861379bd2`.
The frozen `receive_snapshot_cli.py` driver uses real Git diff selection,
the actual TestPilot module CLI, ScriptedModel, and native pytest. It edits only
its authored caller fixture after the baseline has copied source returning 2.

| Original case | TestPilot result | Exact emitted patch run on captured source |
| --- | --- | --- |
| Assert 7 after the caller edits 2 to 7 | passed | fails |
| Assert 2 after the same edit | failed | passes |
| Assert 2 with no caller edit | passed | passes |

Each case has two scripted ledger entries, preserved phase observations, raw CLI
stdout/stderr, its exact report JSON and patch, and an independent patch
verification result. The caller edits remain intact. These observations
demonstrate cross-phase source inconsistency; they do not establish atomicity
during the initial copy.

The first eight author tests produced **4 failed, 4 passed** on the original.
The later path/alias selection produced **2 failed, 7 passed, 6 deselected**;
two of its passing cleanup controls overlap the earlier run. The exact original
eight-test prefix was recovered from the retained 15-test source and matched
its recorded SHA256; it was not rerun or rewritten as a new baseline.

The first candidate produced **15 passed in 25.48s**, with unchanged source pins.
Its loop SHA256 is `cb4b92ef79080be4d26af78c861e3604968953c809e7d07bd1f917eb624d60e5`;
its helper SHA256 is `ec1ab4df0b92727defc176d04b1df771aa677195bec0f5502cc62e8d7091f1a3`.
The receipt records every runtime module and the 15-test source hash.

## Source-only amendment and environment block

Review then identified a compatibility concern: the first helper copied
read-only directory modes before rewriting private symlinks. The amendment
temporarily enables owner writes only in its private selection tree and restores
the copied modes in `finally` blocks. It adds one authored read-only-link
positive control. The amended helper and 16-test module passed AST parsing only.

Both attempted native read-only-link executions stopped at fixture directory
creation with `ENOSPC`; TestPilot and pytest were not reached. They are
**environment blocks, not product failures or passes**. No candidate actual-CLI
receipt exists yet. Native writes remained stopped, and no alternate mount,
other-worker cleanup, quota override, or protected-directory permission change
was used.

The amended source, current-main composition, remaining CLI receiver, and
independent controls require the repository's existing hosted CI. See
`author-qualification.json` and `environment-block.json` for the exact
disposition. Independent evidence is owned by the separate receiving worker.

## Composition and scope

Publication is proposed over current main
`513f17454af378ee042ccd29dc930ef332a48734`.
Its original `loop.py` still has Git blob
`a9de8356f3454334578bdfd1af19d6382b8a64a0`, identical to the qualified native
baseline. Its README is the exact current blob
`df07258a3f6e3f4a07eb8d6b5584a9aa39712867` plus one captured-project note.
The timeout and hunk-admission CLI/diff changes are preserved; those paths are
not included in this carrier.

Product edits are the new snapshot helper, TestPilot.run orchestration and
two-root path/module reservations, focused tests, a short README note, and
`docs/EXECUTION_SNAPSHOT.md`. Sandbox process custody, selectors, models,
schemas, output writers, and recheck are outside this change.

Each carrier entry contains exact decoded UTF-8 content, byte count, SHA256,
and Git blob ID. Baseline and candidate artifacts are historical evidence, not
claims of installed runtime adoption, provider model quality, or full-suite
qualification.
