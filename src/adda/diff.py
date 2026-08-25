# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda diff — drift DETECTION (spec §6.5 item 1, the headline differentiator).

Compares the documented OKF modules (those that declare a repo `path`) against the
actual current repo and reports where they have diverged. Most context tools only
*store* context; almost none *detect* divergence. Output: a list of
{module, documented, actual, severity} gaps.

- documented module whose path no longer exists  -> HIGH  (docs reference vanished code)
- source dir present in the repo but undocumented -> MEDIUM (code drifted ahead of docs)

Modules without a `path` are not checkable and are skipped (run `adda sync` to add paths).
"""

from pathlib import Path

from adda.okf import compile_okf
from adda.sync import discover_modules


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def diff_report(repo: Path, adda_dir: Path) -> list[dict]:
    """Return drift gaps between documented modules and the actual repo."""
    okf = compile_okf(adda_dir)
    with_path = {_norm(m.path): m for m in okf.architecture.modules if m.path.strip()}
    documented_names = {m.name for m in okf.architecture.modules}

    gaps = []
    # 1) documented modules (that declare a path) whose path has vanished
    for path, module in with_path.items():
        if not (repo / path).exists():
            gaps.append(
                {"module": module.name, "documented": path, "actual": "missing", "severity": "high"}
            )

    # 2) source dirs present in the repo but documented by neither path nor name.
    #    A dir is "covered" if a documented module path lives inside it — this is
    #    how file-level modules (e.g. cli [src/pkg/cli.py]) keep a single-package
    #    src layout clean (ENH-ADDA-002). ponytail: sync still emits dir-level
    #    skeletons; document file-level modules by hand.
    for name, path in discover_modules(repo):
        norm = _norm(path)
        if norm in with_path or name in documented_names:
            continue
        if any(p == norm or p.startswith(norm + "/") for p in with_path):
            continue
        gaps.append(
            {"module": name, "documented": "missing", "actual": path, "severity": "medium"}
        )

    return gaps
