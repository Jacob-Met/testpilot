"""Reconstruct the final source composition without executing TestPilot."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
import tarfile


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def definitions(data):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(data).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
    manifest = json.loads((root / "source-manifest.json").read_bytes())
    tree = json.loads((root / "current-tree-blobs.json").read_bytes())
    require(tree["sha"] == manifest["canonical_tree"] == "56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd", "canonical tree")
    require(manifest["canonical_base"] == "3e745e6b6a2f7e383fc6b43f12e69f7a221fb051", "canonical parent")
    require(tree["truncated"] is False, "complete tree")
    leaves = {row["path"]: row for row in tree["tree"]}
    require(len(leaves) == len(tree["tree"]) == 728, "728 unique canonical leaves")
    for row in manifest["artifacts"]:
        raw = (root / row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"] and blob(raw) == row["git_blob"], row["path"])
    for row in manifest["canonical_files"]:
        raw = (root / "upstream" / row["path"]).read_bytes()
        require(blob(raw) == row["sha"] == leaves[row["path"]]["sha"], "canonical " + row["path"])

    prior_archive = root.parent / "current-composition" / "pr20-native.tar.xz"
    require(sha(prior_archive.read_bytes()) == "8f480e0b9edb7bfa29c4e75bbcf8f5298e9d735fdc3ca0a65205dd6b3bb0670a", "qualified PR20 archive")
    with tarfile.open(prior_archive, mode="r:xz") as archive:
        prior = {name: archive.extractfile(name).read() for name in ["source/testpilot/loop.py", "upstream/testpilot/loop.py", "source/README.md"]}
        for path in manifest["unchanged_frozen_files"]:
            require((root / "proposed" / path).read_bytes() == archive.extractfile("source/" + path).read(), "unchanged reviewed " + path)
    current_loop = (root / "upstream/testpilot/loop.py").read_bytes()
    proposed_loop = (root / "proposed/testpilot/loop.py").read_bytes()
    old = b'- Coverage: unavailable (install `coverage`)'
    new = b'- Coverage: unavailable'
    require(prior["upstream/testpilot/loop.py"].count(old) == 1, "one canonical wording change")
    require(prior["upstream/testpilot/loop.py"].replace(old, new, 1) == current_loop, "current loop only inherited wording delta")
    require(prior["source/testpilot/loop.py"].replace(old, new, 1) == proposed_loop, "same delta applied to qualified loop")

    old_paths = '    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md"}\n'
    new_paths = '    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",\n             "html": out / "report.html"}\n'
    extra = '    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n'
    text = proposed_loop.decode()
    for addition in ["from .html_report import render_html_report\n", new_paths, extra]:
        require(text.count(addition) == 1, "exact one accepted addition")
    require(text.replace("from .html_report import render_html_report\n", "", 1).replace(new_paths, old_paths, 1).replace(extra, "", 1).encode() == current_loop, "exact final parent reconstructed")
    readme = (root / "proposed/README.md").read_bytes()
    require(readme == prior["source/README.md"], "unchanged qualified README")
    readme_text = readme.decode()
    section = "## Review your own run in a browser\n" + readme_text.split("## Review your own run in a browser\n", 1)[1].split("## Running on Nebius Token Factory", 1)[0]
    require(readme_text.replace(section, "", 1).encode() == (root / "upstream/README.md").read_bytes(), "canonical README reconstructed")
    before = definitions(prior["upstream/testpilot/loop.py"])
    after = definitions(current_loop)
    require(before.keys() == after.keys() and [key for key in before if before[key] != after[key]] == ["render_report"], "only Markdown render definition changed upstream")
    require(all(before[key] == after[key] for key in ["LoopResult", "RoundRecord", "TestPilot", "write_outputs"]), "schema, pipeline, allocator use and writer preserved")
    result = {
        "schema": "testpilot.html_report.publication_parent_reconstruction.v1",
        "canonical_base": manifest["canonical_base"], "canonical_tree": tree["sha"],
        "canonical_leaves": len(leaves), "canonical_files_verified": len(manifest["canonical_files"]),
        "proposed_loop_sha256": sha(proposed_loop), "proposed_readme_sha256": sha(readme),
        "unchanged_reviewed_files": len(manifest["unchanged_frozen_files"]),
        "canonical_loop_and_readme_reconstructed": True,
        "prior_qualified_loop_preserved_except_current_markdown_wording": True,
        "current_loop_other_definitions_exact": len(before) - 1,
        "unchanged_result_and_round_schema": True,
        "canonical_model_and_sandbox_preserved_as_parent_leaves": True,
        "boundary": "Source and archived-evidence reconstruction only. No native product execution was repeated on this final parent; exact-head hosted CI is the final integration gate."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
