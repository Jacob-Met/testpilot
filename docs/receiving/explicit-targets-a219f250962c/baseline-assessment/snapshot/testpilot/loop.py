"""generate -> run -> repair loop with a round limit and a token/cost ledger.

Flow for one diff:

1. ``diff.changed_functions`` finds changed Python functions.
2. Baseline: run the repo's existing tests in the sandbox (coverage before).
3. Planner model (Nemotron, large) writes a short test plan.
4. Editor model (small/fast) turns plan + sources into pytest file(s).
5. Sandbox runs existing + generated tests. Green -> done.
6. Otherwise the editor model gets the failure report and rewrites the tests,
   up to ``max_repair_rounds`` times. It may instead answer
   ``VERDICT: CODE_BUG`` when the failure looks like a real bug in the code;
   the loop then stops rather than bending tests to fit broken code.
7. Emit a ``git apply``-able patch adding the tests, plus a coverage delta.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from .diff import ChangedFunction, changed_functions
from .html_report import render_html_report
from .model import ChatClient, ModelError, RoutingConfig, Usage
from .sandbox import IGNORE, SandboxResult, run_pytest

SYSTEM_PLANNER = (
    "You are TestPilot's planner. Given changed Python functions from a pull request, "
    "list the behaviours that pytest tests should pin down: normal cases, edge cases, "
    "error cases. Be concise. Do not write code."
)
SYSTEM_EDITOR = (
    "You are TestPilot's test writer. Write pytest tests for the changed functions. "
    "Import the code under test by its module path. Tests must be deterministic, fast, "
    "offline, and must not sleep or touch the network. Output each file as a fenced block "
    "whose info string is `python path=tests/test_<name>.py`. Add new test files; do not "
    "replace the repository's existing tests. Output only test files."
)
SYSTEM_REPAIR = (
    "You are TestPilot's test repairer. The tests below failed. If the TEST is wrong "
    "(bad expectation, import, fixture, timing), output the corrected files in the same "
    "fenced format, using the current generated file paths. Omitted files are kept unchanged; "
    "output only the generated files that need repair. Existing repository tests cannot be "
    "changed by this workflow. If the failure shows a genuine bug in the CODE under test, do not "
    "weaken the test: reply with a line `VERDICT: CODE_BUG` followed by a one-paragraph "
    "explanation."
)

# Closers start a line; keep legacy adjacent close/open fences compatible.
_FENCE = re.compile(
    r"```([^\n`]*)\n(.*?)^[ \t]*(?:`{3,}[ \t]*(?:\r?\n|$)|```(?=```[^\n`]*\n))",
    re.S | re.M,
)
_PATH_IN_INFO = re.compile(r"path\s*=\s*([^\s`]+)")
_PATH_COMMENT = re.compile(r"^#\s*(?:file|path)\s*:\s*(\S+)\s*\n", re.I)
_VALID_TEST_PATH = re.compile(r"^tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py$")
DEFAULT_TEST_PATH = "tests/test_testpilot_generated.py"


class BudgetExceeded(RuntimeError):
    pass


# ---------------------------------------------------------------------- ledger
@dataclass
class LedgerEntry:
    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated: bool
    cost_usd: float


@dataclass
class Ledger:
    routing: RoutingConfig
    max_total_tokens: int | None = None
    entries: list[LedgerEntry] = field(default_factory=list)

    def record(self, role: str, model: str, usage: Usage) -> LedgerEntry:
        e = LedgerEntry(role, model, usage.prompt_tokens, usage.completion_tokens, usage.estimated,
                        round(self.routing.cost(model, usage), 8))
        self.entries.append(e)
        return e

    @property
    def total_tokens(self) -> int:
        return sum(e.prompt_tokens + e.completion_tokens for e in self.entries)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(e.cost_usd for e in self.entries), 8)

    def check_budget(self) -> None:
        if self.max_total_tokens is not None and self.total_tokens >= self.max_total_tokens:
            raise BudgetExceeded(f"token budget {self.max_total_tokens} reached ({self.total_tokens})")

    def by_model(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in self.entries:
            m = out.setdefault(e.model, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})
            m["calls"] += 1
            m["prompt_tokens"] += e.prompt_tokens
            m["completion_tokens"] += e.completion_tokens
            m["cost_usd"] = round(m["cost_usd"] + e.cost_usd, 8)
        return out

    def to_dict(self) -> dict:
        priced = all(self.routing.has_price(e.model) for e in self.entries)
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "cost_is_complete": priced,
            "tokens_estimated": any(e.estimated for e in self.entries),
            "by_model": self.by_model(),
            "entries": [asdict(e) for e in self.entries],
        }


# --------------------------------------------------------------- output parsing
def sanitize_test_path(path: str | None) -> tuple[str, str | None]:
    """Force generated files into ``tests/**/test_*.py``. Returns (path, warning)."""
    if path:
        p = PurePosixPath(path.strip().lstrip("./"))
        cand = p.as_posix()
        if ".." not in p.parts and _VALID_TEST_PATH.match(cand):
            return cand, None
        name = re.sub(r"[^A-Za-z0-9_]", "_", p.stem) or "generated"
        if not name.startswith("test_"):
            name = "test_" + name
        return f"tests/{name}.py", f"rewrote unsafe/invalid test path {path!r} -> tests/{name}.py"
    return DEFAULT_TEST_PATH, None


def parse_test_files(text: str) -> tuple[dict[str, str], list[str]]:
    """Extract ``{path: content}`` from fenced code blocks in a model reply."""
    files: dict[str, str] = {}
    warnings: list[str] = []
    for info, body in _FENCE.findall(text):
        lang = info.strip().split(" ")[0].lower() if info.strip() else ""
        if lang not in ("", "python", "py"):
            continue
        m = _PATH_IN_INFO.search(info)
        path = m.group(1) if m else None
        if path is None:
            cm = _PATH_COMMENT.match(body)
            if cm:
                path, body = cm.group(1), body[cm.end():]
        path, w = sanitize_test_path(path)
        if w:
            warnings.append(w)
        if path in files:
            warnings.append(f"duplicate block for {path}; later block wins")
        files[path] = body if body.endswith("\n") else body + "\n"
    return files, warnings


def parse_verdict(text: str) -> str | None:
    m = re.search(r"VERDICT:\s*CODE_BUG\s*(.*)", text, re.S)
    if m is None:
        return None
    return m.group(1).strip() or "model reported a code bug"


class _GeneratedPathConflict(ValueError):
    pass


def _path_occupied(repo: Path, rel: str) -> bool:
    """A new regular file must not replace a path or traverse a symlink."""
    path = repo
    parts = PurePosixPath(rel).parts
    for i, part in enumerate(parts):
        path = path / part
        if path.is_symlink() or (path.exists() and (i == len(parts) - 1 or not path.is_dir())):
            return True
    return False


def _require_additions(repo: Path, files: dict[str, str]) -> None:
    for rel in files:
        if _path_occupied(repo, rel):
            raise _GeneratedPathConflict(f"cannot add generated tests without replacing repository path {rel!r}")


def _pytest_module_name(repo: Path, rel: str) -> str:
    """Use pytest's default regular-package identity within the copied project."""
    path = repo / rel
    names = [] if path.name == "__init__.py" else [path.stem]
    parent = path.parent
    while (parent != repo.parent and parent.name.isidentifier()
           and (parent / "__init__.py").is_file()):
        names.insert(0, parent.name)
        parent = parent.parent
    return ".".join(names)


def _repository_module_names(repo: Path) -> set[str]:
    """Reserve copied Python modules without walking ignored or symlinked dirs."""
    modules: set[str] = set()
    for root, dirs, files in repo.walk(follow_symlinks=False):
        ignored = IGNORE(str(root), dirs + files)
        dirs[:] = [name for name in dirs if name not in ignored]
        for name in files:
            if name.endswith(".py") and name not in ignored:
                modules.add(_pytest_module_name(repo, (root / name).relative_to(repo).as_posix()))
    return modules


def _merge_test_files(repo: Path, current: dict[str, str], incoming: dict[str, str],
                     aliases: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Apply a partial repair, reserving repository paths and pytest module names.

    Keep aliases for renamed suggestions so a repair using either the original
    suggestion or the displayed generated path updates the same generated file.
    """
    merged, remapped = dict(current), dict(aliases)
    reserved = set(current) | set(incoming) | set(aliases.values())
    reserved_modules = {_pytest_module_name(repo, rel) for rel in reserved}
    occupied_modules = _repository_module_names(repo)
    occupied_modules.update(_pytest_module_name(repo, rel) for rel in current)
    updates: dict[str, str] = {}
    warnings: list[str] = []
    for rel, content in incoming.items():
        target = aliases.get(rel, rel)
        path_conflict = target not in current and _path_occupied(repo, target)
        module_conflict = (target not in current
                           and _pytest_module_name(repo, target) in occupied_modules)
        if path_conflict or module_conflict:
            test_root = repo / "tests"
            if test_root.is_symlink() or (test_root.exists() and not test_root.is_dir()):
                raise _GeneratedPathConflict("cannot add generated tests: repository 'tests' is not a regular directory")
            # Path conflicts retain the safe root fallback; import-name-only
            # conflicts keep local fixtures and relative imports in their scope.
            parent = PurePosixPath("tests") if path_conflict else PurePosixPath(target).parent
            stem = PurePosixPath(rel).stem
            suffix = 1
            while True:
                tag = "" if suffix == 1 else f"_{suffix}"
                target = str(parent / f"{stem}_testpilot{tag}.py")
                module = _pytest_module_name(repo, target)
                if (target not in reserved and not _path_occupied(repo, target)
                        and module not in occupied_modules and module not in reserved_modules):
                    break
                suffix += 1
        if target != rel:
            warnings.append(f"generated suggestion {rel!r} uses {target!r}; kept repository paths and pytest module names")
        if target in updates and updates[target] != content:
            raise _GeneratedPathConflict(f"conflicting repair blocks resolve to generated path {target!r}; kept previous tests")
        updates[target] = content
        remapped[rel] = target
        reserved.add(target)
        module = _pytest_module_name(repo, target)
        reserved_modules.add(module)
        occupied_modules.add(module)
        merged[target] = content
    _require_additions(repo, merged)
    aliases.update(remapped)
    return merged, warnings


# ----------------------------------------------------------------- patch/coverage
def make_patch(repo: Path, files: dict[str, str], *, additions_only: bool = False) -> str:
    """Unified diff; generated patches use additions only so git refuses collisions."""
    chunks = []
    for rel in sorted(files):
        # Git counts LF-delimited lines; other separators remain file content.
        new = re.findall(r"[^\n]*\n|[^\n]+$", files[rel])
        target = repo / rel
        if not additions_only and target.exists():
            old = re.findall(r"[^\n]*\n|[^\n]+$", target.read_text(encoding="utf-8"))
            header = [f"diff --git a/{rel} b/{rel}\n"]
            body = difflib.unified_diff(old, new, f"a/{rel}", f"b/{rel}")
        else:
            old = []
            header = [f"diff --git a/{rel} b/{rel}\n", "new file mode 100644\n"]
            body = difflib.unified_diff(old, new, "/dev/null", f"b/{rel}")
        lines = list(body)
        if lines:
            chunks.append("".join(header + lines))
    return "".join(chunks)


def _changed_line_coverage(res: SandboxResult | None, funcs: list[ChangedFunction]) -> tuple[int, int] | None:
    if res is None or res.coverage is None:
        return None
    hit = total = 0
    for f in funcs:
        executable = res.coverage.executable(f.path)
        executed = res.coverage.executed(f.path)
        for ln in f.changed_lines:
            if ln in executable:
                total += 1
                hit += ln in executed
    return hit, total


def coverage_delta(before: SandboxResult | None, after: SandboxResult | None,
                   funcs: list[ChangedFunction]) -> dict | None:
    if before is None or after is None or before.coverage is None or after.coverage is None:
        return None
    b, a = _changed_line_coverage(before, funcs), _changed_line_coverage(after, funcs)

    def pct(t):
        return round(100.0 * t[0] / t[1], 1) if t and t[1] else None

    return {
        "total_before": round(before.coverage.percent_total, 1),
        "total_after": round(after.coverage.percent_total, 1),
        "total_delta": round(after.coverage.percent_total - before.coverage.percent_total, 1),
        "changed_lines_executable": b[1] if b else 0,
        "changed_lines_before": pct(b),
        "changed_lines_after": pct(a),
    }


# --------------------------------------------------------------------- prompts
def _functions_block(funcs: list[ChangedFunction]) -> str:
    parts = []
    for f in funcs:
        imp = f"from {f.module} import {f.import_name}" if f.module else f"import {f.import_name}"
        parts.append(f"### {f.path}::{f.qualname} (lines {f.lineno}-{f.end_lineno}; import with `{imp}`)\n"
                     f"```python\n{f.source}\n```")
    return "\n\n".join(parts)


def _files_block(files: dict[str, str]) -> str:
    return "\n\n".join(f"```python path={p}\n{c}```" for p, c in sorted(files.items()))


# ------------------------------------------------------------------------ loop
@dataclass
class RoundRecord:
    round: int
    kind: str  # generate | repair
    files: list[str]
    result: dict | None
    warnings: list[str] = field(default_factory=list)
    contents: dict[str, str] = field(default_factory=dict)


@dataclass
class LoopResult:
    status: str  # passed | failed | suspected_code_bug | no_changes | no_tests | budget_exhausted | model_error
    changed_functions: list[dict]
    repair_rounds_used: int
    max_repair_rounds: int
    test_files: dict[str, str]
    tests_written: int
    final: dict | None
    patch: str
    coverage: dict | None
    ledger: dict
    rounds: list[RoundRecord]
    plan: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ok"] = self.ok
        return d


def count_tests(files: dict[str, str], result: SandboxResult | None, existing_ids: set[str]) -> int:
    """Number of generated test cases (from junit when available, else static count)."""
    if result is not None and result.generated_files and result.junit_available:
        return len(result.generated_cases)
    if result is not None and result.cases:
        return sum(1 for c in result.cases if c.nodeid not in existing_ids)
    return sum(len(re.findall(r"^\s*(?:async\s+)?def test_", c, re.M)) for c in files.values())


class TestPilot:
    __test__ = False  # not a pytest class

    def __init__(self, client: ChatClient, routing: RoutingConfig | None = None, *, max_repair_rounds: int = 3,
                 timeout_s: float = 60.0, max_total_tokens: int | None = None, coverage: bool | None = None,
                 python: str | None = None):
        self.client = client
        self.routing = routing or RoutingConfig()
        self.max_repair_rounds = max_repair_rounds
        self.timeout_s = timeout_s
        self.max_total_tokens = max_total_tokens
        self.coverage = coverage
        self.python = python

    def _ask(self, ledger: Ledger, role: str, system: str, user: str) -> str:
        ledger.check_budget()
        model = self.routing.model_for(role)
        resp = self.client.chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}])
        ledger.record(role, model, resp.usage)
        return resp.content

    def _run(self, repo: Path, files: dict[str, str] | None) -> SandboxResult:
        return run_pytest(repo, files, timeout=self.timeout_s, coverage=self.coverage, python=self.python)

    def run(self, repo: str | Path, diff_text: str) -> LoopResult:
        repo = Path(repo)
        ledger = Ledger(self.routing, self.max_total_tokens)
        funcs = changed_functions(repo, diff_text)
        rounds: list[RoundRecord] = []
        files: dict[str, str] = {}
        aliases: dict[str, str] = {}
        plan = ""
        final: SandboxResult | None = None
        repairs = 0
        status, message = "failed", ""

        def result(st: str, msg: str = "", baseline: SandboxResult | None = None) -> LoopResult:
            existing = {c.nodeid for c in baseline.cases} if baseline else set()
            patch = ""
            try:
                _require_additions(repo, files)
                patch = make_patch(repo, files, additions_only=True)
            except _GeneratedPathConflict as e:
                st, msg = "failed", str(e)
            return LoopResult(
                status=st, changed_functions=[f.to_dict() for f in funcs], repair_rounds_used=repairs,
                max_repair_rounds=self.max_repair_rounds, test_files=files,
                tests_written=count_tests(files, final, existing) if files else 0,
                final=final.to_dict() if final else None,
                patch=patch,
                coverage=coverage_delta(baseline, final, funcs), ledger=ledger.to_dict(), rounds=rounds,
                plan=plan, message=msg)

        if not funcs:
            return result("no_changes", "diff touches no Python functions outside tests")

        baseline = self._run(repo, None)
        try:
            plan = self._ask(ledger, "planner", SYSTEM_PLANNER,
                             f"Changed functions:\n\n{_functions_block(funcs)}\n\nWrite the test plan.")
            reply = self._ask(ledger, "editor", SYSTEM_EDITOR,
                              f"Test plan:\n{plan}\n\nChanged functions:\n\n{_functions_block(funcs)}\n\n"
                              "Write the pytest file(s).")
            proposed, warns = parse_test_files(reply)
            if not proposed:
                rounds.append(RoundRecord(0, "generate", [], None, warns + ["no python code block in reply"]))
                return result("no_tests", "model produced no test files", baseline)
            files, path_warnings = _merge_test_files(repo, files, proposed, aliases)
            warns.extend(path_warnings)
            final = self._run(repo, files)
            rounds.append(RoundRecord(0, "generate", sorted(files), final.to_dict(), warns, dict(files)))

            while not final.ok and repairs < self.max_repair_rounds:
                repairs += 1
                reply = self._ask(ledger, "repair", SYSTEM_REPAIR,
                                  f"Changed functions:\n\n{_functions_block(funcs)}\n\nCurrent tests:\n\n"
                                  f"{_files_block(files)}\n\nFailure report:\n{final.failure_report()}")
                verdict = parse_verdict(reply)
                if verdict:
                    rounds.append(RoundRecord(repairs, "repair", sorted(files), None, []))
                    return result("suspected_code_bug", verdict, baseline)
                new_files, warns = parse_test_files(reply)
                if not new_files:
                    warns.append("repair reply had no code block; keeping previous tests")
                    rounds.append(RoundRecord(repairs, "repair", sorted(files), final.to_dict(), warns))
                    continue
                files, path_warnings = _merge_test_files(repo, files, new_files, aliases)
                warns.extend(path_warnings)
                final = self._run(repo, files)
                rounds.append(RoundRecord(repairs, "repair", sorted(files), final.to_dict(), warns, dict(files)))
            if final.ok:
                status = "passed"
            elif (final.generated_files and not final.timed_out and final.returncode in (0, 5)
                  and not final.failed and not final.errors):
                status = "no_tests"
                message = ("no generated test case passed; existing-suite passes do not qualify "
                           f"the generated patch: {final.summary()}")
            else:
                status, message = "failed", f"still failing after {repairs} repair round(s): {final.summary()}"
        except BudgetExceeded as e:
            status, message = "budget_exhausted", str(e)
        except ModelError as e:
            status, message = "model_error", str(e)
        except _GeneratedPathConflict as e:
            status, message = "failed", str(e)
            rounds.append(RoundRecord(repairs, "repair" if repairs else "generate", sorted(files),
                                      None, [message], dict(files)))
        return result(status, message, baseline)


# ---------------------------------------------------------------------- report
def render_report(res: LoopResult) -> str:
    """Render UTF-8 text, visibly escaping unencodable filesystem/string surrogates."""
    lines = [f"# TestPilot report: **{res.status}**", ""]
    if res.message:
        lines += [res.message, ""]
    lines.append(f"- Changed functions: {', '.join(f['path'] + '::' + f['qualname'] for f in res.changed_functions) or 'none'}")
    lines.append(f"- Tests written: {res.tests_written} in {', '.join(sorted(res.test_files)) or '-'}")
    lines.append(f"- Repair rounds used: {res.repair_rounds_used}/{res.max_repair_rounds}")
    if res.final:
        lines.append(f"- Final run: {res.final['summary']} in {res.final['duration_s']}s")
    c = res.coverage
    if c:
        lines.append(f"- Coverage (total): {c['total_before']}% -> {c['total_after']}% ({c['total_delta']:+} pts)")
        lines.append(f"- Coverage (changed lines, n={c['changed_lines_executable']}): "
                     f"{c['changed_lines_before']}% -> {c['changed_lines_after']}%")
    else:
        lines.append("- Coverage: unavailable")
    lg = res.ledger
    cost = f"${lg['total_cost_usd']:.6f}" if lg["cost_is_complete"] else "unpriced (set TESTPILOT_PRICES)"
    lines.append(f"- Tokens: {lg['total_tokens']}{' (estimated)' if lg['tokens_estimated'] else ''}; cost: {cost}")
    for m, s in lg["by_model"].items():
        lines.append(f"  - `{m}`: {s['calls']} calls, {s['prompt_tokens']} in / {s['completion_tokens']} out")
    if res.patch:
        lines += ["", "## Patch", "", "```diff", res.patch.rstrip("\n"), "```"]
    text = "\n".join(lines) + "\n"
    return text.encode("utf-8", errors="backslashreplace").decode("utf-8")


def write_outputs(res: LoopResult, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",
             "html": out / "report.html"}
    paths["patch"].write_text(res.patch, encoding="utf-8")
    paths["json"].write_text(json.dumps(res.to_dict(), indent=2), encoding="utf-8")
    paths["md"].write_text(render_report(res), encoding="utf-8")
    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")
    return paths
