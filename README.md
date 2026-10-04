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
* **Ledger.** Every model call records its role, model, and prompt/completion tokens. If the API returns `usage`, those counts are used. The stub uses a chars/4 estimate and flags it. Cost is computed only from prices you supply; TestPilot never guesses prices.

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
| `tests/` | 36 unit/integration tests |

## Quickstart (offline, no key)

Requirements: Python 3.12+, `pytest`. `coverage` is optional; without it, coverage is reported as unavailable.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install pytest coverage

python -m pytest                       # 36 passed
python -m eval.harness                 # eval table → eval/results/results.md

python -m testpilot run \
  --repo eval/cases/calc_clamp/repo \
  --diff eval/cases/calc_clamp/change.diff \
  --script eval/cases/calc_clamp/script \
  --out out/calc_clamp                 # testpilot.patch, report.md, report.json
```

On a real repo, use `--git-base main` instead of `--diff FILE`. Exit codes: 0 means the generated tests pass, 1 means any other outcome, 2 means a config error.

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
