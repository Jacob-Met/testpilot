"""Capture one project input while retaining source-path and alias admission."""
from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import tempfile

from .diff import DiffSourceError, _source_path
from .sandbox import IGNORE


def _links(root: Path) -> Iterator[Path]:
    for directory, names, files in os.walk(root, followlinks=False):
        for name in names + files:
            path = Path(directory) / name
            if path.is_symlink():
                yield path


def _selection_view(project: Path, view: Path, source_paths: Sequence[str]) -> None:
    # Keep links until the existing selector has admitted source identity.
    # Materializing them first would turn an outside source into an inside file.
    shutil.copytree(project, view, symlinks=True, ignore=IGNORE)
    complete = {Path(directory) for directory, _, _ in os.walk(view, followlinks=False)}
    pending = deque(_links(view))
    rebound: set[Path] = set()

    @contextmanager
    def private_write(directory: Path) -> Iterator[None]:
        # Only our private copy is adjusted, and only during construction.
        # Source directories can be readable without permitting new entries.
        if directory.is_symlink() or not directory.resolve().is_relative_to(view):
            raise OSError("captured input write escaped its private directory")
        mode = stat.S_IMODE(directory.stat().st_mode)
        writable = mode | stat.S_IWUSR | stat.S_IXUSR
        if writable != mode:
            directory.chmod(writable)
        try:
            yield
        finally:
            if writable != mode:
                directory.chmod(mode)

    def parents(destination: Path) -> None:
        cursor = view
        for part in destination.relative_to(view).parts[:-1]:
            cursor /= part
            if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
                raise OSError(f"captured input parent changed while copying: {cursor.relative_to(view)}")
            with private_write(cursor.parent):
                cursor.mkdir(exist_ok=True)

    def fill(source: Path, destination: Path) -> None:
        """Copy an admitted internal link target omitted by the normal ignore policy."""
        if source.is_symlink():
            if not destination.exists() and not destination.is_symlink():
                parents(destination)
                with private_write(destination.parent):
                    shutil.copy2(source, destination, follow_symlinks=False)
                pending.append(destination)
            return
        if source.is_dir():
            if destination in complete:
                return
            parents(destination)
            if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
                raise OSError(f"captured input target changed while copying: {destination.relative_to(view)}")
            with private_write(destination.parent):
                destination.mkdir(exist_ok=True)
            children = list(source.iterdir())
            ignored = IGNORE(str(source), [child.name for child in children])
            for child in children:
                if child.name not in ignored:
                    fill(child, destination / child.name)
            shutil.copystat(source, destination)
            complete.add(destination)
            return
        if source.exists() and not destination.exists() and not destination.is_symlink():
            parents(destination)
            with private_write(destination.parent):
                shutil.copy2(source, destination)

    def rebind() -> None:
        while pending:
            link = pending.popleft()
            if link in rebound:
                continue
            relative = link.relative_to(view)
            target = (project / relative).parent / link.readlink()
            try:
                resolved = target.resolve()
            except (OSError, RuntimeError):
                # Preserve a dangling/cyclic identity for the ordinary selector
                # or copy operation to refuse, without reading through the link.
                resolved = Path(os.path.abspath(target))
            if resolved.is_relative_to(project):
                captured = view / resolved.relative_to(project)
                fill(resolved, captured)
                rewritten = os.path.relpath(captured, link.parent)
            else:
                # Relative links outside the project must still name their
                # original target after the containing directory moves.
                rewritten = str(resolved)
            with private_write(link.parent):
                link.unlink()
                link.symlink_to(rewritten, target_is_directory=resolved.is_dir())
            rebound.add(link)

    rebind()
    for raw in source_paths:
        try:
            resolved = _source_path(project, raw)
        except DiffSourceError:
            # The unchanged selector supplies the command's normal diagnostic.
            continue
        if not resolved.is_file():
            continue
        fill(resolved, view / resolved.relative_to(project))
        # Explicit or diff-selected source can itself lie under an ignored
        # directory. Preserve its path identity without copying that whole tree.
        original, captured = project, view
        for part in Path(raw).parts:
            original /= part
            captured /= part
            if original.is_symlink():
                fill(original, captured)
                break
            if original.is_dir():
                parents(captured)
                if captured.is_symlink() or (captured.exists() and not captured.is_dir()):
                    raise OSError("captured source parent changed while copying")
                with private_write(captured.parent):
                    captured.mkdir(exist_ok=True)
            else:
                fill(original, captured)
    rebind()


@dataclass
class CapturedProject:
    selection_root: Path
    execution_root: Path

    def materialize(self) -> Path:
        """Freeze the bytes each existing sandbox invocation will copy."""
        shutil.copytree(self.selection_root, self.execution_root, ignore=IGNORE)
        return self.execution_root


@contextmanager
def capture_project(repo: Path, source_paths: Sequence[str]) -> Iterator[CapturedProject]:
    """Yield private selection and execution inputs, cleaning both on every exit.

    This is a finite copy window, not an atomic filesystem snapshot. Source
    selection reads only the private link-preserving view. The execution copy
    then freezes the sandbox's ordinary materialized input, including referenced
    data links; each pytest phase still gets its own fresh disposable worktree.
    """
    project = repo.resolve()
    with tempfile.TemporaryDirectory(prefix="testpilot-capture-") as temporary:
        base = Path(temporary)
        selection = base / "selection" / (project.name or "repo")
        execution = base / "execution" / "repo"
        selection.parent.mkdir()
        execution.parent.mkdir()
        _selection_view(project, selection, source_paths)
        yield CapturedProject(selection, execution)
