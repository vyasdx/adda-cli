# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The repository ADDA reads is untrusted input (ADR-0030).

ADDA runs on repositories its user did not write. Everything here keeps that
repository from steering ADDA into running its code, writing outside it, or
reading outside it.
"""

import os
import tempfile
from pathlib import Path

# BUG-ADDA-045: `python -m adda.cli` and `python -c` put the current directory
# first on the import path, and git runs hooks from the repository root, so a
# repository's own `json.py` or `adda/__init__.py` would run. `-P` fixes that
# only from Python 3.11, and `-I` also drops user-site installs, so the launch
# code removes the current directory itself before importing anything from it.
_SCRUB = 'import sys; sys.path[:] = [p for p in sys.path if p not in ("", ".")]; '
LAUNCH = _SCRUB + 'sys.argv[0] = "adda"; from adda.cli import app; app()'
IMPORT_CHECK = _SCRUB + "import adda.cli"

# BUG-ADDA-047: a repository's own git config can name programs that git runs
# (core.fsmonitor on index refreshes). A plain clone never carries config, an
# archive with a git directory does. Command-line config wins over the repo's.
GIT = ["git", "-c", "core.fsmonitor=false", "-c", "safe.bareRepository=explicit"]


class UnsafeWrite(Exception):
    """A write the repository could have redirected."""


def write_text(target: Path, text: str, root: Path = None, newline: str = None) -> None:
    """Write `text` to `target` without following a link the repository planted.

    BUG-ADDA-046: `Path.write_text` follows symlinks, so a tracked
    `okf.json -> ../../.bashrc` would be overwritten. A symlinked target is
    refused, and a path that sits inside `root` must still resolve inside it
    (a symlinked parent folder cannot move it out). A path the user points
    outside `root` on purpose is theirs. The file is written beside the target
    and renamed into place, so a reader never sees half of it.
    """
    check_target(target, root)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        os.chmod(tmp, _mode(target))  # mkstemp makes it owner-only
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def check_target(target: Path, root: Path = None) -> None:
    """Raise UnsafeWrite if writing `target` could land somewhere the user did not ask for."""
    if target.is_symlink():
        raise UnsafeWrite(f"{target} is a symlink; refusing to write through it")
    if root is not None:
        here = Path(os.path.abspath(target))
        if here.is_relative_to(os.path.abspath(root)) and not target.parent.resolve().is_relative_to(root.resolve()):
            raise UnsafeWrite(f"{target} resolves outside {root}; refusing to write there")


def _mode(target: Path) -> int:
    """The file's current mode, or what a plain open() would have created."""
    if target.exists():
        return target.stat().st_mode & 0o777
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def inside(root: Path, rel: str) -> bool:
    """Does `rel` stay inside `root` once `..`, drive letters and symlinks resolve?"""
    return (root / rel).resolve().is_relative_to(root.resolve())
