# TestPilot

TestPilot takes a git repo and a diff. It writes pytest tests for the Python functions the diff changed, runs them in a sandboxed subprocess with a timeout, and repairs failing tests for up to N rounds. The output is a PR-ready patch, a coverage delta, and a token/cost ledger.

Built for the Nebius x NVIDIA Global AI Hackathon (Coding & Agentic Engineering track). It is designed to run on **Nebius Token Factory** with **NVIDIA Nemotron** models.

> **Status:** everything here runs locally against a deterministic `ScriptedModel` stub. It has **not** been run against Token Factory yet, because no API key exists. The eval numbers below show the pipeline works. They say nothing about model quality.

## How it works

```
diff ──► diff.py (unified diff → changed lines → ast functions)
          │
          ▼
       baseline: sandbox runs existing tests (coverage before)
          │
          ▼
       planner model (Nemotron, large)  → test plan
       editor model  (Nemotron, small)  → tests/test_*.py
          │
          ▼
       sandbox.py: temp copy + pytest + junit + coverage, wall-clock timeout
          │ fail
          ▼
       repair (editor model, ≤ N rounds) ── either rewrites the tests
          │                                 or answers VERDICT: CODE_BUG
          ▼
       testpilot.patch  +  report.md / report.json (coverage delta, ledger)
```

Design choices:

* **Tests are not bent to fit buggy code.** The repair prompt lets the model say `VERDICT: CODE_BUG` instead of weakening an assertion. The loop then stops with status `suspected_code_bug` and keeps the failing tests in the patch, since those tests are the bug report.
* **Planner/editor routing.** One planning call goes to the large model. Generation and repair go to the small, fast model. Routing is set in `RoutingConfig`.
* **Generated files are confined** to `tests/**/test_*.py`. Any path containing `..`, an absolute path, or an unexpected name is rewritten. The sandbox also refuses writes outside its temp dir.
* **Existing tests stay in the run and out of the generated patch.** A suggested filename that already exists, or would traverse a symlink or blocked directory, is moved to an unused `tests/test_<name>_testpilot.py` path (with a numeric suffix when needed). The report's round warnings record the mapping. Repairs can use the suggested name or the displayed generated name; a reply that mentions only some generated files updates those files and keeps the others. TestPilot refuses generation when `tests` itself is a symlink or a file. Its patches add files only, so `git apply` refuses to overwrite a file that appeared after generation.
* **Generated Python module names stay distinct.** Under pytest's default import rules, unpackaged files with the same basename share an import name even in different directories. TestPilot reserves existing and generated module names, adding a `_testpilot` suffix (and a number when needed) inside the requested directory for import-name collisions so local fixtures stay in scope. Distinct regular packages can keep the same basename; path conflicts still use the safe root fallback described above. The scan uses the sandbox's ignore patterns and does not follow directory symlinks.
* **Ledger.** Every model call records its role, model, and prompt/completion tokens. If the API returns `usage`, those counts are used. The stub uses a chars/4 estimate and flags it. Cost is computed only from prices you supply; TestPilot never guesses prices.
* **Generated tests must actually run.** Generated files are added to pytest's configured
  collection alongside the existing suite, including projects whose `testpaths` points
  somewhere other than `tests`. Project fixtures, selection hooks and assertion rewriting
  remain active; ordinary directory/file overlap runs each case once. The native JUnit
  report identifies generated cases by their source file, including parameterized cases.
  A passing result requires the complete selected suite to pass and at least one generated
  case to pass. Helper-only, entirely skipped or entirely deselected output is sent through
  the normal repair loop, then reported as `no_tests` if it remains unqualified. The report
  retains the exact patch and generated-case counts for review. If a timeout or an abrupt
  process exit prevents a complete JUnit report, `final.junit_available` is false and
  `tests_written` retains a static count of authored test definitions; those definitions
  do not count as verified executions or make the result pass.

## Layout

| Path | What |
|---|---|
| `testpilot/diff.py` | Unified-diff parser and `ast` mapping to changed functions/methods (decorators, async, class methods, pure deletions, new/deleted files, `src/` layout) |
| `testpilot/model.py` | `ChatClient` protocol, `ScriptedModel` stub, stdlib `OpenAICompatClient` (retries on 429/5xx), `RoutingConfig`, `make_client` |
| `testpilot/sandbox.py` | `run_pytest`: temp copy, junit parsing, optional `coverage` JSON, process-group kill on timeout, env scrubbed of `*KEY*`/`*TOKEN*`/`*SECRET*` vars |
| `testpilot/loop.py` | `TestPilot.run`: generate → run → repair loop, round limit, token budget, ledger, patch, coverage delta, reports |
| `testpilot/__main__.py` | CLI |
| `eval/cases/*` | 5 toy repos with injected bugs, diffs, ground-truth fixes, scripted model replies |
| `eval/harness.py` | Scores pass@1, tests written, and rounds used. Writes `eval/results/` |
| `tests/` | Unit/integration tests, including generated-file preservation and real `git apply` checks |

## Quickstart (offline, no key)

Requirements: Python 3.12+, `pytest`. `coverage` is optional; without it, coverage is reported as unavailable.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install pytest coverage

python -m pytest                       # run the unit/integration suite
python -m eval.harness                 # eval table → eval/results/results.md

python -m testpilot run \
  --repo eval/cases/calc_clamp/repo \
  --diff eval/cases/calc_clamp/change.diff \
  --script eval/cases/calc_clamp/script \
  --out out/calc_clamp                 # testpilot.patch, report.md, report.json
```

On a real repo, use `--git-base main` instead of `--diff FILE`. Exit codes: 0 means the generated tests pass, 1 means any other outcome, 2 means a config error.

The `--git-base` path requests a raw, uncolored Git patch with standard file
prefixes. Git display preferences such as `diff.noprefix`, `diff.mnemonicprefix`
and forced color therefore keep the same source targets. External diff and
text-conversion helpers are disabled for this read; the repository's Git
configuration stays unchanged. Saved-file and stdin `--diff` inputs retain their
existing decoding and selection behavior.

Add `--no-coverage` to `run` to execute pytest without optional coverage measurement. The choice applies to the baseline, generated tests and every repair round, including when you select a project interpreter with `--python`. Reports then show coverage as unavailable; actual test failures and exit codes still determine the run's result. Omit the flag to keep automatic coverage when the selected interpreter has it installed.

For `run`, `--timeout` must be a positive finite number of seconds (default 60). Invalid limits are rejected as configuration errors before reading the diff, constructing a model client, starting tests or replacing saved reports. Fractional seconds and scientific notation are supported.

## Choose functions explicitly

Use repeated `--target path.py::qualname` flags on `targets` or `run` to select
specific current functions, including unchanged functions affected by a change
you have identified. The supplied diff stays available as context to planning,
generation and repair. Without this option, automatic diff selection is unchanged.
See [explicit targets](docs/EXPLICIT_TARGETS.md) for preview, ordering, refusals,
saved selection context and unchanged-function coverage semantics.

## Review your own run in a browser

Every run also writes **`report.html`** in its output directory. Open that file
directly to review the actual recorded result: selected functions and their
source, the model's plan, final generated files, individual test diagnostics,
each repair round's source snapshot and result, coverage, and the ordered token
and model ledger. Native expandable panels and section links work with keyboard
or touch. Use the browser's Print command for a paper or PDF review.

The file is self-contained. Its **Download exact patch** and **Download report
JSON** links retain the exact sibling artifact bytes even if you move the HTML
elsewhere. It includes the source and diagnostics already recorded in the JSON.
Opening the file needs no server or internet and does not run tests, apply the
patch, contact a model, or use browser storage.

Missing JUnit results keep generated execution counts unavailable; an authored
definition count does not become a verified test count. Missing coverage and
unpriced cost remain explicit. The recorded pytest output is the runner's last
3,000 characters, so it is labeled as a tail. A model-only repair response does
not become another test execution. Passing tests and a suspected-code-bug
message retain their original meanings; the HTML adds no verification or model
quality claim. Source, messages and model text are rendered literally, with
visible escapes for HTML-incompatible controls or surrogate characters. The
embedded original downloads remain unchanged.

## Saving a complete report

Before replacing a saved review, TestPilot prepares all four outputs, checks the
existing final paths, and writes complete staged files on the output filesystem.
If preparation, path checks, or staging fails, the previous final files remain
unchanged and the error propagates. Existing final paths must be regular files:
symlinks (including dangling links), directories and other file types are refused.
Successful output keeps the same filenames, bytes and native text-newline behavior;
existing regular files retain their permission bits. Replacement follows the
output directory's permissions, so a read-only regular file can still be replaced
when its directory permits it. The HTML downloads still
contain the exact JSON and patch bytes that accompany that review.

Publication then replaces each file individually. This is not a transaction across
all four files: a later replacement error or a process/system failure can leave a
mixture of old and new files. Concurrent writers are not coordinated. Use a separate
output directory when separate runs need independent saved results.

## Inspect a saved-test recheck

The model-free `testpilot recheck` command also writes **`recheck.html`** beside
its existing JSON and Markdown. Open it directly to inspect the actual current
cases, diagnostics, retained test source, timing and source identity. Its exact
JSON download travels with the file. Missing JUnit stays unavailable, and the
original report's status stays historical. See the [recheck guide](docs/RECHECK.md)
for the command, execution boundaries and output-delivery limits.

## Running on Nebius Token Factory

Token Factory has an OpenAI-compatible API. Its quickstart (<https://docs.tokenfactory.nebius.com/quickstart>, read 2026-10-04) uses:

```python
base_url="https://api.tokenfactory.nebius.com/v1/"
api_key=os.environ.get("NEBIUS_API_KEY")
```

TestPilot's client posts to `{base_url}chat/completions` with a `Bearer` key. Switching from the stub needs only a backend flag, the base URL (which is the default), and a key:

```bash
export NEBIUS_API_KEY=...                     # never commit this
export TESTPILOT_PLANNER_MODEL=nvidia/nemotron-3-super-120b-a12b
export TESTPILOT_EDITOR_MODEL=nvidia/Nemotron-3_5-Lightning
export TESTPILOT_PRICES='{"nvidia/nemotron-3-super-120b-a12b":[IN,OUT],"nvidia/Nemotron-3_5-Lightning":[IN,OUT]}'  # USD per 1M tokens, from the pricing page

python -m testpilot run --backend tokenfactory --repo . --git-base main --out out/pr
python -m eval.harness --backend tokenfactory
```

The default model IDs come from the Token Factory docs' August 2026 deprecation notice (<https://docs.tokenfactory.nebius.com/august-2026-deprecation-notice>). That page names `nvidia/nemotron-3-super-120b-a12b` and `nvidia/Nemotron-3_5-Lightning` as current replacement models. **Check both against the live model catalog before relying on them.** To use a self-hosted or other OpenAI-compatible endpoint, set `TESTPILOT_BASE_URL`.

## Eval (scripted stub)

Each case has a repo with one injected bug, the PR diff, a hidden `fix/` used only as an oracle, and canned model replies. The scripts are written to exercise every loop path: a first-try diagnosis, an import-error repair followed by a diagnosis, a timeout, exhausting the round limit, and weak tests that miss the bug.

* **bug-revealing**: the final tests fail on the buggy repo and pass with `fix/` applied.
* **solved**: the agent reports `suspected_code_bug` **and** its tests are bug-revealing. With one sample per case, pass@1 = solved / cases. A green suite on buggy code counts as a miss.

| case | agent status | bug-revealing | solved | tests written | repair rounds | model calls | tokens (est.) | changed-line cov before % | after % |
|---|---|---|---|---|---|---|---|---|---|
| calc_clamp | suspected_code_bug | yes | yes | 4 | 1 | 3 | 1051 | 25.0 | 100.0 |
| durations_parse | suspected_code_bug | yes | yes | 4 | 1 | 3 | 1176 | - | - |
| inventory_cart | failed | yes | no | 4 | 3 | 5 | 2337 | 20.0 | 100.0 |
| stats_median | passed | no | no | 3 | 0 | 2 | 443 | 16.7 | 100.0 |
| textutil_slugify | suspected_code_bug | yes | yes | 4 | 2 | 4 | 1641 | 25.0 | 100.0 |

pass@1 = 0.60 (3/5); bug-revealing = 0.80; tests written = 19; repair rounds = 7; tokens = 6648

These numbers are fixed by construction, because the stub replays scripts. `durations_parse` has no coverage because its final run timed out, which was the infinite loop being detected. Token counts are chars/4 estimates.

## Limitations

* The sandbox gives process-level isolation only: a temp copy, a killed process group, and a scrubbed env. Network and filesystem access are **not** blocked. Run untrusted repos inside a container or VM.
* Only Python is supported, and imports are resolved from the repo root or `src/`. Repos that need an install step, such as compiled extensions or heavy dependencies, need their environment prepared first (`--python` hook in `run_pytest`).
* With `coverage`, changed-line coverage counts executable added lines only. Pure deletions affect which functions are selected but not the coverage figure.

## License

Apache-2.0. Copyright 2026 Jacob Scott-Metoyer. See `LICENSE`.
