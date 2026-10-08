# Complete unified hunks before automatic target selection

Final native product source: `40860534a8fdc760b105ac9bc7d14ac9087172dd`, composed with canonical main `cec50d8df4499ba509615e179d82ef3861379bd2`. All 54 focused current-main checks pass, with one existing skip and seven subtests. Independent receiving passes all 11 native Git/GNU fixtures and four malformed CLI cases; the installed console also passes independent positive/refusal receiving. Earlier negative evidence, including the v2 whole-suite deadline failure, remains unchanged.

## Observed developer failure

Contributor: `hamon-6cc6795e89f4/estate_production`, an external ChatGPT source contributor under Jacob's current HAMON execution mandate. This is not a resident Za identity or a native goal lease.

The baseline is canonical TestPilot commit `eacb9907f51aeb9360da654c60cbbd7cf99ad877`, obtained through an ordinary native Git clone into a separate bare repository and worktree. No existing checkout or service was changed.

A real disposable Git project changes `selected()` from returning one to returning two. Increasing each declared hunk length by one leaves a context record missing. Git rejects that damaged patch with `git apply --reverse --check`. The baseline parser nevertheless counts the empty token after the final LF as a context line and returns a selected target. The native `targets` command succeeds, and the native `run` command generates and executes a passing test, returns exit 0, and publishes its result.

The original result was retained from its first execution without replay. See `baseline-native-run/`: the damaged diff, exact post-change source, two scripted model responses, generated patch, result report and byte/hash receiving manifest. Its report records two scripted model calls, one passing generated test, a complete JUnit result and status `passed`. No provider call or paid inference occurred.

Other baseline failures expose missing file headers, malformed or incomplete ranges, exhausted-side counter underflow, extra body records and a damaged later file reaching source selection. The frozen 24-case receiver reports 20 failed negative assertions and four passing compatibility controls. These are expected before-fix failures, not a passing baseline.

## Source change and behavior

`parse_unified_diff` now checks the complete declared old/new body counts before it returns any file changes. A damaged later hunk rejects the whole automatic selection before source is read, tests start or model calls occur. Header-shaped deleted or added source lines remain body records while their counts are pending.

The parser retains LF record boundaries, including Unicode separators inside source literals. It removes only the synthetic empty token after a terminal LF, keeps an actual final record without LF, supports CRLF records and preserves the existing tolerance for a genuinely blank context record whose leading space was stripped. Complete zero-context insertion/deletion, new/deleted files and Git no-newline markers retain their target identities.

Invalid hunk structure raises `DiffFormatError`, a `ValueError`. The existing `targets` error path returns exit 2 with no success JSON. A narrow additional `run` catch returns exit 2 and a useful input-error message, without a traceback or output directory.

The physical-line, Git filename decoding, source-root boundary, Python encoding, function mapping, model, sandbox and report implementations are unchanged. Explicit `--target` selection remains governed by its existing resolver, which already parses the supplied diff and wraps malformed input as `TargetSelectionError`. It continues to select exactly the named functions; a diff cannot add targets to that request.

This validates unified-hunk structure and declared counts. It does not compare removed/context text against a repository revision, apply a patch, or certify that a syntactically complete patch matches the current checkout. The parser is still a target selector, not a substitute for Git's content/application checks.

## Native qualification

Runtime: Python 3.14.4, pytest 9.0.2 and Git 2.53.0 on ThinkPad.

- `baseline.json` and `baseline.txt` retain the original command, pinned source/test hashes and the complete 20-fail / 4-pass result.
- `candidate-v1-suite.json` and `candidate-v1-suite.txt` retain the exact candidate source hashes and the whole current native suite: **398 passed, 4 skipped, 18 subtests passed; exit 0; 229.11 seconds**.
- The new receiver uses actual Git-generated patches and Git's independent rejection of the corrupted patch. It also invokes the real native file/stdin CLI paths and verifies no success output/result is published for damaged input.
- Existing project tests cover Git-quoted and non-UTF-8 filenames, source encoding cookies, physical lines, source boundaries and explicit target selection. Those modules were not edited to obtain the passing result.
- `git diff --check` passed.

The four skipped cases remain skips; no platform coverage is inferred from them. Native verification is not a deployed-service or model-quality claim.

## Coordination and integration

The sole additive advisory source scope is recorded at `/srv/hamon-estate/coord/hamon-6cc6795e89f4-testpilot-hunks.json`. The parent worker received the proposed boundary before production edits. Current project issues and hunk topic searches, the complete 1,141-leaf current source tree, and native advisory records showed no matching hunk-validation claimant. Existing coverage-option, process-cancellation and saved-run comparison/finder owners retain their paths.

One ordinary GitHub issue creation attempt at 2026-10-08 17:09:41 UTC returned a secondary content-creation rate limit (HTTP 403; request `FD45:22FE9A:1FD6707:68B258B:6AC7CE53`). No issue was created, and no alternate identity, route or immediate retry was used. The refusal is preserved in `github-issue-refusal.json`.

Current state: implemented, independently received and installed through the declared console entry point in a private versioned native environment. Canonical source publication remains a separate parent-owned step. No managed-service deployment or native goal mutation is claimed. Earlier checkpoint evidence and publication refusal remain intact.


## Revision 2: respond to native receiving

The original production candidate and passing whole-suite result remain immutable in commit `9265ae42bde5b6bd559584a11cbb7c30b7849743`. Evidence-only successor `628f9e3eb0a597d79e8fa9ad58fff62c9681d121` retained the original baseline Python bytes as inert `sample.py.txt`; `retained-paths.json` records that relocation without changing the original execution receipt.

Independent receiving found that ten ordinary Git/GNU unified-diff cases preserved the baseline's complete file/function mappings, while a valid Git email patch's terminal signature was rejected. Its missing-script CLI challenge also showed automatic mode loading model configuration before discovering the malformed diff. These original successes and failures are retained separately under `docs/receiving/git-compat-6cc6795e89f4/`; they are not rewritten as passes.

Additional native checks exposed decimal range conversion errors escaping the dedicated input-error class. `oversize-native-run-v1.json` retains the actual CLI exit 1/traceback and absence of an output directory. `range-v1-negative.*` preserves four failing field cases before the numeric fix. `footer-preflight-v1-negative.*` records five failures/four positive controls with only that numeric fix applied: valid mail rejected, a signature accidentally satisfying a missing old record, and model-configuration errors preceding diff rejection.

Revision 2 makes three bounded changes:

- Range integer conversion failures become `DiffFormatError`, so all four old/new start/count fields use the clean invalid-diff error path.
- Automatic CLI mode parses hunk structure before `make_client`, alongside the existing explicit-target preflight. The model implementation and runtime loop are unchanged.
- A standard Git email envelope may carry the exact terminal `-- ` delimiter followed by its Git version signature. That metadata cannot complete a missing body record. An identical deleted source record remains a body record, and a footer-shaped extra deletion outside the envelope is still rejected.

`candidate-v2-targeted.*` records **37 passed, exit 0, 8.18 seconds** with exact frozen source/test hashes. The receiver includes actual Git-generated and Git-accepted email patches, a legitimate deleted `- ` source line, missing old/new/both records, a damaged later file, four oversized range fields, and native preflight against missing model configuration with new and pre-existing output directories. Existing output bytes remain unchanged on refusal.

Compatibility is claimed for ordinary unified diffs and the standard single Git email envelope/version signature exercised here. This is not a general mail/mbox or custom-signature parser. Placement and repetition of `\\ No newline at end of file` markers retain the existing tolerance; this change does not claim full marker-grammar validation. Source counts do not prove that context/deletions match the current checkout.


## Revision 3: qualify the actual custom signature and current main

The independent receiver's original Git mail fixture uses the valid `--signature=HAMON Receiving Fixture` option. Revision 2's version-only footer gate still rejected that exact input. `independent-receiving-v2.json` retains the unresolved mail case alongside ten passing ordinary Git/GNU cases and four clean native CLI refusals. The original receiver patches were not regenerated or weakened.

`custom-signature-v2-negative.*` adds native Git custom-signature controls: two failed assertions and three positive controls before the final fix. The final parser recognizes a terminal plain-text signature under the standard Git envelope. Signature lookahead refuses body/file/hunk prefixes, so a footer cannot conceal a later damaged hunk, and pending counts are rejected before consuming the delimiter. This supports the actual default-version and custom-text fixtures without turning the target parser into a general mail/mbox parser.

Canonical main advanced during receiving through accepted coverage-choice PR #40. It is a single first-parent merge onto the original base, with a CLI `--no-coverage` option and the existing constructor's coverage argument. The final isolated integration worktree merges that accepted source without conflicts; its coverage option and tests are preserved unchanged. The parser and its automatic preflight remain the only new production behavior in this contribution.

`candidate-v3-integrated-targeted.*` records **49 passed, 1 skipped; exit 0; 19.49 seconds** across all 44 hunk cases and the six coverage CLI cases. Its receipt pins the current parser, composed CLI and both test files. The one coverage skip remains a skip; no untested platform result is inferred.

`candidate-v2-suite.*` records the complete earlier frozen v2 run accurately: **1 failed, 410 passed, 4 skipped, 18 subtests passed; exit 1; 301.15 seconds**. The failure was `test_real_pytest_timeout_then_fresh_success`: the child pytest process did not reach its helper marker within the fixture's one-second deadline. No hunk assertion failed in that whole-suite run.

`deadline-isolated-receiving.json` and its two raw outputs retain one controlled sequential replay against original base and current integration. Both pass, with identical `testpilot/sandbox.py` and deadline-test bytes: original base 1 passed in 3.12 seconds; current integration 1 passed in 2.66 seconds. Recorded load averages were roughly 14-16 on eight CPUs. Load is context, not proof of causality, and isolated passes do not relabel the earlier whole-suite failure. Neither the sandbox nor its timeout fixture was edited.

## Final current-main composition and installed native product

Accepted Git display-settings PR #42 advanced canonical main to `cec50d8df4499ba509615e179d82ef3861379bd2`. Its raw Git diff flags and all corresponding tests are preserved unchanged in production source commit `40860534a8fdc760b105ac9bc7d14ac9087172dd`. The only production delta from that canonical base is the unified-hunk parser and automatic CLI preflight.

`candidate-current-main-receiving.json` and its raw output record **54 passed, 1 skipped, 7 subtests passed; exit 0; 62.70 seconds**, covering all hunk cases plus accepted coverage and Git acquisition behavior. Independent v3 evidence in the sibling receiving directory records **11/11** original Git/GNU fixtures and **4/4** clean malformed CLI refusals. These focused results do not replace or relabel the retained v2 full-suite failure.

The declared `testpilot.__main__:main` console is installed at:

```text
/home/jacob/testpilot-native-6cc6795e89f4/40860534a8fd/bin/testpilot
```

The human launch guide is `/home/jacob/testpilot-native-6cc6795e89f4/README.md`. A source archive at the exact production commit was built and installed offline without dependencies or provider calls. All 11 installed Python source files match that archive. Wheel SHA256: `83c756b33833e004c6421c203888c54862a4eb4995dba1e08bfea3128dec9c4b`; installation receipt SHA256: `86d74c235a0d451fb42712015fb60f3a18c52b98407d67104a0b3ae4f974c0f0`.

`native-console/` retains the exact installation logs, byte provenance, launch guide, and actual installed-console execution. Its valid Git fixture completes a scripted run with one generated passing test and a real report. Damaged input returns clean exit 2 before deliberately missing model configuration, with both new output absent and all existing result bytes unchanged. The original native receipt SHA256 is `5b7ccec59416d704a155b082d33147cc12c342a08236acb0a8eee2cba6ba3890`.

`native-console/independent/` preserves an independent prewritten contract, raw receiving receipt and inert receiver source. Outside the source checkout, with PYTHONPATH/PYTHONHOME removed, the installed console passes **2/2** cases: the original real-Git fixture selects all ten expected functions; malformed run exits 2 before missing model setup, pytest or output creation. Its 11 installed Python files and console remain unchanged. Original receipt SHA256: `2c5aa3f6ceccb407ba8cb83160552ffe06c8884a2035a001bbca4c00ab998214`.

The installed console also selects its own final production delta correctly: exactly `testpilot/__main__.py::main` and `testpilot/diff.py::parse_unified_diff`. All executable fixture source retained here uses inert `.py.txt` names so receiving evidence does not become a production target. This evidence-only successor does not change installed product bytes.

## Final test-fixture containment review

Root review at evidence commit `385ded4f4c02b57f98a07ef4beb4a1d2e8a0bf1f` found that the new test helpers inherited Git routing/configuration variables. The retained `fixture-containment-baseline-385ded4.json` records two private sentinel controls: inherited repository/worktree settings changed the sentinel config, and an inherited index path changed the sentinel index. No user repository was used. These baseline failures remain unchanged.

The test-only successor introduces one shared fixture environment helper: discard inherited `GIT_*` variables, disable system config and use the null file as global config. Both Git fixture commands and fixture CLI invocations use that environment. Product and installed package bytes are unchanged. `candidate-fixture-isolation-receiving.*` records **44 passed in 20.73 seconds, exit 0**, with before/after source hashes. Root independent same-method replay on exact test-fix commit `2585b7857b8087a4f96275294482bee4fecfc316` passes **2/2** controls: all private external repository/worktree and index sentinel bytes remain unchanged, and each fixture owns its own Git directory. The original two baseline failures, final candidate receipt and identical receiving method (retained as inert `fixture-containment-receiver.py.txt`) are preserved. Method SHA256: `410434b1b63f468b15c6b70b4460bce4f92e73aaf7779720e9a15fbc3ab8118c`.
