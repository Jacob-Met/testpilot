# TestPilot target preview — author freeze

Base: `Jacob-Met/testpilot@9f01fcb6de085850eca00db746380795eb548d62`, complete tree `34191a66ec22f8630aea83559cfb16f1e464ab3e`. No AGENTS.md exists in that tree. The local packet contains seven exact native source/config files; it is not a full project checkout.

## Capability

`testpilot targets --repo PROJECT (--diff FILE | --git-base REF) [--json]` exposes the existing changed-function selector before generation. Human output gives quoted source locations. JSON carries the exact native `changed_functions` records, including selected source. Preview neither constructs a model client nor invokes TestPilot's pytest or output writer.

Only `testpilot/__main__.py`, new `tests/test_cli_targets.py`, and new `docs/targets-preview.md` are product changes. The selector, pending source-encoding owner, model, sandbox, loop, interpreter helper, original run parser statements, and entire run tail remain intact.

## Qualification

- Native missing-capability witness: actual Git edit selects one function through the original public API, while the actual `targets` CLI returns parser exit 2. The existing `run` also needs model configuration. This establishes an unavailable inspection capability, not a defect or false-success result.
- Original source against the new interface cases: eight methods, nine failed assertions and one parser exception across seven methods; the existing native run control passes. These expected absences are retained in `evidence/baseline-focused.json`.
- Final candidate: eight methods pass normally and eight with optimized Python, zero failures/errors/skips. Each final run records fifteen actual module CLI children plus one direct main tripwire case. The optimized parent propagates `-O` to every native CLI child.
- Actual Git selection includes a decorated method in a Unicode filename, exact source/range/added-line output, saved-file/stdin equivalence, empty results, input/native selector refusals, and argument help. Top-level source and conftest tripwires remain unexecuted; project bytes remain unchanged.
- The existing generation control uses the actual ScriptedModel/TestPilot/report writer with an empty diff and explicit prepared-interpreter option. It retains `no_changes`, exit 1, zero tokens/calls, and its normal JSON/Markdown/empty patch.
- `evidence/preservation.json` verifies source preservation and an actual `git apply --check` plus apply into a separate native before-image. All three reconstructed files and every supplied unrelated source/config file match.

Production source passed on its first normal run. The first optimized-parent receiver did not propagate `-O` to its child CLIs; that historical result and its exact initial test are retained. Only the test launcher was amended to propagate optimization, then the final exact test ran once in each mode. The production source was unchanged. The baseline uses the preserved initial test; normal child argv is identical across those two test versions.

## Portable replay

Supply an exact TestPilot checkout or the pinned package slice and the final test file:

```sh
python -B evidence/qualify_targets.py --source /path/to/testpilot \
  --test /path/to/test_cli_targets.py --out /path/to/new-normal.json
python -O -B evidence/qualify_targets.py --source /path/to/testpilot \
  --test /path/to/test_cli_targets.py --out /path/to/new-optimized.json
```

The qualifier refuses an existing output file and records source/test hashes before and after, exact native argv/status/stdout/stderr, and the unittest result. In a complete candidate checkout, the normal project-facing command is:

```sh
python -m unittest discover -s tests -p test_cli_targets.py
```

`candidate.patch` is a native Git patch with correct addition headers. It reconstructs all three product files against the exact before-image; the preservation receipt retains the successful native application check. The local `verify_preservation.py` replay expects adjacent `baseline/` and `candidate/` package slices matching their manifests.

## Boundaries and provenance

Python 3.12.14 on Linux was used. The environment has no pytest or coverage package, and no package installation was performed. The new tests use standard-library unittest; no full repository pytest, hosted CI, provider/model execution, account access, installed-source adoption or production effect is claimed.

Git acquisition intentionally uses the existing run command and configured repository behavior. This is not an execution sandbox or a new Git configuration policy. Preview does not pin a later generation run or validate that an externally supplied diff still matches the working tree.

The scope and current ownership read are in `evidence/local-scope.json`. Public coordination is held until the parent's GitHub content-creation backoff clears; no new source branch or PR has been published. The earlier local staging hash-recipe mistake stopped before source was written and is recorded separately in `evidence/setup-note.txt`.
