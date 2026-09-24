# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda doctor — prove the commit gate is on, rather than assume it (ENH-ADDA-030).

The gate fails OPEN by design: a hook whose interpreter has gone exits 0, so a
deleted venv cannot brick every commit. The price is that a broken gate looks
exactly like a working one - a fresh clone has no hook at all, and nothing says
so. That is the failure class ADDA exists to catch, sitting inside ADDA.

Each check below is one way the gate can be installed and still enforce
nothing. Every one is reported as `ok`, `fail` or `n/a`; any `fail` exits 1.
Deterministic, offline, and it never modifies the repo (ADR-0015).
"""

import json
import os
import re
import subprocess
from pathlib import Path

from adda.hook import hooks_dir
from adda.modulemap import MAP_FILENAME

_GATE = "adda.cli hook run"
# `ADDA_PY="..."` in the installed stub, or the one-line form `hook install`
# prints for a repo that already has a hook: exec "<python>" -m adda.cli hook run
_INTERPRETER = re.compile(r'ADDA_PY="([^"]+)"|"([^"]+)"\s+-m\s+adda\.cli\s+hook\s+run')


def _check(name, state, detail):
    return {"check": name, "state": state, "detail": detail}


def _hook_checks(repo: Path, hooks: Path) -> list:
    hook = hooks / "pre-commit"
    try:
        shown = hook.relative_to(repo).as_posix()
    except ValueError:
        shown = str(hook)
    if not hook.is_file():
        default = hooks.resolve() == (repo / ".git" / "hooks").resolve()
        why = "" if default else " - git reads hooks from here because core.hooksPath is set"
        return [_check("pre-commit hook", "fail", f"none at {shown}{why}; run `adda hook install`")]
    out = [_check("pre-commit hook", "ok", shown)]

    body = hook.read_text(encoding="utf-8", errors="replace")
    if _GATE not in body:
        return out + [_check(
            "runs the ADDA gate", "fail",
            f"{shown} exists but never runs `{_GATE}`; add the line `adda hook install` prints",
        )]
    out.append(_check("runs the ADDA gate", "ok", _GATE))

    if os.name == "nt":
        out.append(_check("executable", "n/a", "Windows: git runs the hook via its shebang"))
    elif os.access(hook, os.X_OK):
        out.append(_check("executable", "ok", "mode allows execution"))
    else:
        out.append(_check("executable", "fail", f"git skips a hook it cannot execute: chmod +x {shown}"))

    m = _INTERPRETER.search(body)
    if not m:
        return out + [_check("interpreter", "n/a", "cannot tell which Python the hook runs")]
    python = m.group(1) or m.group(2)
    if not Path(python).exists():
        return out + [_check(
            "interpreter", "fail",
            f"{python} is gone, so the hook exits 0 and checks nothing; re-run `adda hook install --force`",
        )]
    out.append(_check("interpreter", "ok", python))
    try:
        ran = subprocess.run([python, "-c", "import adda.cli"], capture_output=True, timeout=60)
        ok = ran.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    out.append(_check(
        "adda importable", "ok" if ok else "fail",
        "the hook's Python can import adda" if ok
        else f"{python} cannot import adda; install it there or re-run `adda hook install --force`",
    ))
    return out


def _map_check(repo: Path):
    target = repo / "adda" / MAP_FILENAME
    if not target.is_file():
        return _check(
            "MODULE_MAP.json", "fail",
            "absent, so the gate has nothing to enforce; run `adda sync . --map --out adda/MODULE_MAP.json`",
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        mapping = data.get("map") if isinstance(data, dict) else None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return _check("MODULE_MAP.json", "fail", f"cannot be read ({exc.__class__.__name__})")
    if not mapping:
        return _check("MODULE_MAP.json", "fail", "maps no code to any doc, so the gate blocks nothing")
    return _check("MODULE_MAP.json", "ok", f"{len(mapping)} code path(s) mapped")


def diagnose(repo: Path) -> list:
    """Every check, in order: [{check, state, detail}], state ok | fail | n/a."""
    hooks = hooks_dir(repo)
    if hooks is None:
        return [_check("git repository", "fail", f"{repo} is not inside a git repository")]
    checks = [_check("git repository", "ok", str(repo))]
    checks += _hook_checks(repo, hooks)
    checks.append(_map_check(repo))
    skip = os.environ.get("ADDA_SKIP")
    checks.append(_check(
        "ADDA_SKIP", "fail" if skip else "ok",
        "set in this environment, so every commit bypasses the gate" if skip else "not set",
    ))
    return checks
