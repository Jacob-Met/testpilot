#!/usr/bin/env python3
"""Import the exact fanout receiving bundle into a new local worktree."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys


BUNDLE_BYTES = 353498
BUNDLE_SHA256 = "c018ae94ddb33d6ebaaeac84d82f1af9f5f05db170e60af08a585c3ddea742c0"
BEFORE = "0317b4bc80638a8e952857aa5966b0e20d1fab72"
AFTER = "522c40bd3f40359d598b62cf2947d74b14c20a31"
TREES = {
    BEFORE: "35dc556c1309b394c6f864fd5aaa6f7e7fcc0b22",
    AFTER: "cea4779b5b99e576ba6a4b2ab9f959b797c11f87",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_object(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode()
                        + b"\0" + data).hexdigest()


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class ImportFailure(Exception):
    pass


class GitImport:
    def __init__(self, output: Path):
        self.output = output
        self.worktree = output / "worktree"
        self.logs = output / "operations"
        self.logs.mkdir()
        self.records: list[dict] = []
        self.env = {k: v for k, v in os.environ.items()
                    if not k.upper().startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0")

    def run(self, *args: str, cwd: Path | None = None) -> bytes:
        command = ["git", "--no-replace-objects", "--no-lazy-fetch",
                   "--no-optional-locks", "-c", "core.hooksPath=" + os.devnull,
                   *args]
        directory = cwd or self.worktree
        timed_out = False
        try:
            result = subprocess.run(command, cwd=directory, env=self.env,
                                    capture_output=True, timeout=40)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code = error.stdout or b"", error.stderr or b"", None
            timed_out = True
        index = len(self.records)
        (self.logs / f"{index:02d}.stdout").write_bytes(stdout)
        (self.logs / f"{index:02d}.stderr").write_bytes(stderr)
        self.records.append({"command": command, "cwd": str(directory),
                             "returncode": code, "timed_out": timed_out,
                             "stdout_bytes": len(stdout), "stdout_sha256": sha(stdout),
                             "stderr_bytes": len(stderr), "stderr_sha256": sha(stderr)})
        write_json(self.logs / "operations.json", self.records)
        if code != 0 or timed_out:
            raise ImportFailure(f"Git operation {index} failed; see preserved output")
        return stdout

    def verify_worktree(self) -> dict:
        entries = self.run("ls-tree", "-r", "-z", AFTER)
        source: dict[str, dict] = {}
        for raw in entries.split(b"\0"):
            if not raw:
                continue
            header, raw_name = raw.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split(" ")
            name = raw_name.decode("utf-8")
            relative = PurePosixPath(name)
            if (mode not in ("100644", "100755") or kind != "blob"
                    or relative.is_absolute() or ".." in relative.parts
                    or str(relative) != name or name in source):
                raise ImportFailure("Unexpected entry in the pinned source tree")
            path = self.worktree / name
            if path.is_symlink() or not path.is_file():
                raise ImportFailure("Worktree source is not a regular file: " + name)
            data = path.read_bytes()
            if (git_object("blob", data) != oid
                    or bool(path.stat().st_mode & 0o111) != (mode == "100755")):
                raise ImportFailure("Worktree source differs from Git object: " + name)
            source[name] = {"blob": oid, "bytes": len(data), "sha256": sha(data),
                            "mode": mode}
        actual = set()
        for directory, directories, files in os.walk(self.worktree, followlinks=False):
            if Path(directory) == self.worktree:
                directories.remove(".git")
            for name in directories:
                if (Path(directory) / name).is_symlink():
                    raise ImportFailure("Unexpected linked source directory")
            for name in files:
                actual.add((Path(directory) / name).relative_to(self.worktree).as_posix())
        if (actual != set(source) or len(source) != 116
                or sum(item["bytes"] for item in source.values()) != 1149457):
            raise ImportFailure("Pinned worktree inventory differs")
        return source

    def import_bundle(self, bundle: bytes) -> dict:
        snapshot = self.output / "source.bundle"
        with snapshot.open("xb") as stream:
            stream.write(bundle)
        self.run("init", "--template=", str(self.worktree), cwd=self.output)
        with (self.worktree / ".git" / "shallow").open("x", encoding="ascii") as stream:
            stream.write(BEFORE + "\n")
        self.run("bundle", "unbundle", str(snapshot))
        self.run("checkout", "--detach", AFTER)
        self.run("fsck", "--no-reflogs", "--no-dangling")
        commits = {}
        for commit, tree in TREES.items():
            raw = self.run("cat-file", "commit", commit)
            if (git_object("commit", raw) != commit
                    or raw.splitlines()[0] != ("tree " + tree).encode()):
                raise ImportFailure("Raw source commit or tree identity differs")
            commits[commit] = {"tree": tree, "bytes": len(raw), "sha256": sha(raw)}
        source = self.verify_worktree()
        status = self.run("status", "--porcelain=v1", "--untracked-files=all")
        head = self.run("rev-parse", "HEAD").decode("ascii").strip()
        shallow = (self.worktree / ".git" / "shallow").read_bytes()
        if status or head != AFTER or shallow != (BEFORE + "\n").encode():
            raise ImportFailure("Checkout state or original shallow boundary differs")
        if sha(snapshot.read_bytes()) != BUNDLE_SHA256:
            raise ImportFailure("The captured bundle changed during import")
        return {"source_commits": commits, "detached_head": head,
                "worktree_files": source, "clean_worktree": True,
                "original_shallow_boundary": BEFORE}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="new directory with an existing parent")
    args = parser.parse_args()
    output = args.output.absolute()
    try:
        if args.bundle.is_symlink() or not args.bundle.is_file():
            raise ImportFailure("Bundle must be an existing regular file")
        with args.bundle.open("rb") as stream:
            bundle = stream.read(BUNDLE_BYTES + 1)
        if len(bundle) != BUNDLE_BYTES or sha(bundle) != BUNDLE_SHA256:
            raise ImportFailure("Bundle is not the exact reviewed receiving input")
        if output.is_symlink() or output.exists() or not output.parent.is_dir():
            raise ImportFailure("Output must be new and its parent must exist")
        output.mkdir()
    except (OSError, ImportFailure) as error:
        print(str(error), file=sys.stderr)
        return 2

    receipt: dict = {"schema": "testpilot-fanout-bundle-import/1", "accepted": False,
                    "bundle_bytes": len(bundle), "bundle_sha256": sha(bundle),
                    "worktree": str(output / "worktree"),
                    "scope": "Exact local receiving bundle only. No fetch, install, "
                             "project test execution or earlier-history claim."}
    try:
        importer = GitImport(output)
        receipt.update(importer.import_bundle(bundle))
        receipt["operations"] = len(importer.records)
        receipt["accepted"] = True
    except (OSError, ValueError, ImportFailure) as error:
        receipt["error"] = str(error)
    try:
        write_json(output / "IMPORT.json", receipt)
    except OSError as error:
        print("Cannot preserve final import receipt: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps({"accepted": receipt["accepted"], "receipt": str(output / "IMPORT.json"),
                      "worktree": str(output / "worktree")}))
    return 0 if receipt["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
