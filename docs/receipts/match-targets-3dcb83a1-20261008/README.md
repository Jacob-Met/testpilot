# Match/case callable selection

TestPilot previously reported `no_changes` for a changed function defined
inside a valid module-level or class-level `match/case` branch. The unified
diff parser found the changed line, but the AST walker never entered
`ast.Match.cases`, so the existing generation pipeline received no target.

The repair adds three traversal lines in `testpilot/diff.py::_iter_functions`
and updates that function's docstring. Case bodies now use the existing
recursive walker and retain module/class qualified names, decorator boundaries,
async method metadata and diff line mapping. Match statements inside a function
remain attributed to their enclosing callable. Selection is static: subjects,
patterns and guards are not executed, and no claim about which branch will run
is inferred.

## Scope and source identity

The scope was announced before implementation in
[issue #2 comment 6056387396](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6056387396).
The loop-preservation, path-decoder/source-containment, sandbox-timeout and CI
owners retain their work. Product changes are confined to the walker/docstring
and additive `tests/test_match_targets.py`; all evidence is within
`docs/receipts/match-targets-3dcb83a1-20261008/`.

| Item | Exact identity |
| --- | --- |
| Initial tested main | `bc095b47f65805079ee4e9ef97971347fcdfbaa5` |
| Initial tree | `b3d6bfa31fb02e774e15027e9a62fcdf84763ef0` |
| Final composed receiving base | `ca2e6c72743c5d3866f3f14189f1d4c3405f60bf` |
| Final receiving tree | `cd0c4f3033b79138e4a6fa0def03b9208fef1a35` |
| Base diff.py Git blob | `d176701aebb56ce7507ee5f0111245247393f35f` |
| Base diff.py SHA-256 | `d1f22e3b594f9b8c657de6a69e4c44bb32c2a24819165dadb9e8a5a50d0dc5fc` |
| Candidate diff.py Git blob | `425d0712b18a6a72226399a2f9d704193ace1133` |
| Candidate diff.py SHA-256 | `59e5042a548900f234177a281df0b1d6468ce19be79e2f5e84dd205f35394f4e` |
| New regression SHA-256 | `95935deb9d9627f073d6e000675b40c6eb87a1837742e0cb627cda9bf16b40e5` |

The loop owner landed new code during qualification. Earlier baseline/candidate
copies and receipts remain intact. A separate receiving copy incorporated
exact current `loop.py` blob `e94ae5a0ae3f74fdaa7a63dea73f22e50afbe676` and
its new preservation tests; the AST candidate and regression bytes did not
change. Publication inherits the complete final receiving tree, preserving
that owner's source, README and evidence.

## Executed checks

Native execution used CPython 3.14.4 and installed pytest on the ThinkPad.
Every repository, program, diff, model reply and generated test in these
controls was authored synthetic input. No provider request or installed-service
operation was made.

| Check | Observed result |
| --- | --- |
| Original source, frozen new regression | 10 failed / 1 passed; actual pipeline returns `no_changes` |
| Candidate, new regression, normal Python | 11 passed |
| Candidate, same regression, optimized Python | 11 passed; pytest emits its standard warning about assertions outside rewritten test modules |
| Original source, existing source-selection/path suites | 55 passed |
| Initial candidate, existing plus new selection suites | 66 passed |
| Final current-source composition, including newly merged test-preservation suite | 84 passed, zero skips/errors |
| Actual CLI on current baseline | Exit 1, `no_changes`, zero generated tests |
| Actual CLI on current candidate | Exit 0, two passing generated pytest tests; patch passes `git apply --check` |

The focused cases use actual Git diffs. They cover modified/new/deleted files,
decorated async methods under class branches, nested match/if/try/with scopes,
pure deletions, unchanged branches, nonexecution of subjects/guards, and
enclosing-function attribution. The ordinary control passes on the original
source. The pipeline case invokes the real `TestPilot`, `ScriptedModel`,
sandboxed pytest runner and patch producer.

The CLI controls repeat the normal public command against both the initial
and final composed source. Reports, patch files, inputs, replies and commands
are retained under `consumer/`. The original input source remains unchanged;
pytest runs in TestPilot's own temporary copy. The model replies are scripted,
so these results qualify the mechanism and receiving behavior, not model
quality. Coverage was unavailable in this environment and is not claimed.
No full-repository suite result is inferred from the scoped counts above.

## Independent review

This author receipt precedes the separately assigned independent review by
`estate_coordination`. The product source and regression hashes above are
frozen. Consult the pull request's commit-bound review for the current
receiving decision; no independent result is added to the author counts above.
The first publication is a draft while that review is being completed.

## Repeat the tests

From a checkout of the published candidate with its declared pytest dependency:

```bash
python3 -m pytest -q tests/test_diff.py tests/test_git_quoted_paths.py tests/test_diff_source_boundary.py tests/test_match_targets.py tests/test_generated_test_preservation.py
python3 -O -m pytest -q tests/test_match_targets.py
```

For the original negative control, run the unchanged
`tests/test_match_targets.py` against a separate checkout at the initial or
final receiving base. It must retain the ten omissions. The source file is also
preserved as `baseline/diff.py` for exact source-level review.

The retained current CLI fixture can be replayed into a new worker-owned output
directory. Set `packet` to this receipt directory's absolute path:

```bash
python3 -m testpilot run --repo "$packet/consumer/fixture" --diff "$packet/consumer/change.diff" --backend scripted --script "$packet/consumer/script" --rounds 0 --timeout 30 --out /absolute/worker-owned/testpilot-match-output
```

A valid candidate returns `passed`, emits two passing tests and a new-file
patch. Keep model/backend explicit so the replay stays on `ScriptedModel`.
The `--out` directory is supplied by the receiver; the receipt does not install
or activate TestPilot anywhere.

The isolated native work remains under
`/home/jacob/hamon-testpilot-match-3dcb83a1`. `source-manifest.json` records
the initial 59 files; `receiving-source-manifest.json` records the composed
61-file source/test/fixture selection. The Git publication retains the full
repository tree rather than replacing it with this selected local snapshot.
