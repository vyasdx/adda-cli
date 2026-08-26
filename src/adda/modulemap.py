# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""MODULE_MAP.json — code->doc routing (the vision's layer 3).

Maps a source file to the doc that must change with it. Explicit mapping, not
glob rules: it is greppable, diffable and reviewable, and `adda sync --map`
generates it so there is no hand-maintenance burden.

ponytail: fnmatch, not a glob engine — `**` falls out of fnmatch's `*`-matches-
everything (separators included). Upgrade path is pathlib globbing if the
patterns ever need real precedence rules. fnmatchcase is used so matching does
not vary by platform.
"""

import json
from fnmatch import fnmatchcase
from pathlib import Path

MAP_FILENAME = "MODULE_MAP.json"


def _norm(path: str) -> str:
    """Windows-safe: 'src\\adda\\cli.py' -> 'src/adda/cli.py'."""
    return path.replace("\\", "/").strip("/")


def load_map(adda_dir: Path) -> tuple[dict[str, str], list[str]]:
    """Return ({code_path: doc_path}, exempt_globs), both posix-normalised.

    Raises FileNotFoundError when MODULE_MAP.json is absent — callers must
    surface that loudly rather than treating an unmapped repo as a clean one.
    """
    target = adda_dir / MAP_FILENAME
    if not target.is_file():
        raise FileNotFoundError(f"No {MAP_FILENAME} in {adda_dir}. Run `adda sync --map`.")
    data = json.loads(target.read_text(encoding="utf-8"))
    mapping = {_norm(k): _norm(v) for k, v in (data.get("map") or {}).items()}
    return mapping, [_norm(g) for g in (data.get("exempt") or [])]


def load_include(adda_dir: Path) -> list[str]:
    """Source roots to map even though the package heuristic would drop them.

    `source_roots` treats a Python directory with no `__init__.py` as examples
    rather than code — a guess that is right for fastapi's 369 tutorial
    snippets and wrong for a plain `toolscripts/`, which vanished repo-wide the
    moment any package existed (BUG-ADDA-020). Per DEC-ADDA-009 the guess now
    reports itself in `audit` output, and this list is how you overrule it:
    deliberate, greppable and diffable, like the rest of the map.

    Absent file returns [] rather than raising — `load_map` already owns the
    loud failure for a missing map, and duplicating it here would make every
    caller handle the same error twice.
    """
    target = adda_dir / MAP_FILENAME
    if not target.is_file():
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return [_norm(p) for p in (data.get("include") or [])]


def is_exempt(path: str, exempt: list[str]) -> bool:
    """True if `path` matches any exempt glob."""
    norm = _norm(path)
    return any(fnmatchcase(norm, pattern) for pattern in exempt)
