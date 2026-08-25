# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The commit gate (the vision's layer 4) — enforcement that is mechanical, not memory.

Blocks a commit that stages a code file without staging the doc MODULE_MAP.json
routes it to. Staged-vs-staged needs no dates and no LLM, so there is nothing to
forge and nothing to forget.

Deliberately COMMIT-SCOPED: it never runs `audit` or `diff`. Pre-existing
repo-wide drift blocking an unrelated commit is how a gate earns a permanent
`--no-verify` and stops enforcing anything at all.
"""

import subprocess
from pathlib import Path

from adda.modulemap import is_exempt, load_map

HOOK_STUB = """#!/bin/sh
# Installed by `adda hook install` - blocks a commit that changes code without
# changing the doc MODULE_MAP.json routes it to.
#
# The interpreter path is baked in at install time on purpose: `adda` is
# normally installed in a venv that is not active when git runs hooks, and a
# bare `adda` can even resolve to ADDA's own adda/ memory DIRECTORY.
ADDA_PY="{python}"
if [ ! -e "$ADDA_PY" ]; then
  echo "[adda] interpreter $ADDA_PY is gone - doc gate skipped." >&2
  exit 0
fi
exec "$ADDA_PY" -m adda.cli hook run
"""


def hook_body(python: str) -> str:
    """Render the stub for a specific interpreter.

    Fails OPEN when the interpreter has vanished (venv deleted or moved): a
    hook that cannot run must not brick every future commit in the repo.
    """
    return HOOK_STUB.format(python=python.replace("\\", "/"))


def staged_paths(repo: Path) -> list:
    """Posix paths staged for commit. Empty when git is unavailable.

    `-z` gives NUL-separated, UNQUOTED paths. Without it git quotes any path
    containing non-ASCII or control characters (`"src/caf\\303\\251.py"`), which
    then matches no MODULE_MAP entry — a staged file silently slipping past the
    gate. Git already emits posix separators here on every platform, so no
    separator rewriting is needed or wanted.

    Git's output is UTF-8 regardless of platform; `encoding="utf-8"` is required
    because `text=True` alone decodes with the locale/console codepage (e.g.
    Windows cp1252), which mangles a UTF-8 filename into different mojibake
    than the quoting bug it was meant to fix.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            cwd=repo, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return []
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.split("\0") if p]


def check_staged(repo: Path, adda_dir: Path, staged: list) -> list:
    """[(code, required_doc)] for staged code whose mapped doc is not staged.

    A repo with no MODULE_MAP.json has not adopted the convention and must stay
    committable — that is `audit`'s finding to report, not the gate's.
    """
    try:
        mapping, exempt = load_map(adda_dir)
    except FileNotFoundError:
        return []
    staged_set = set(staged)
    return [
        (code, mapping[code])
        for code in sorted(staged_set)
        if code in mapping and mapping[code] not in staged_set and not is_exempt(code, exempt)
    ]
