# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda audit — the doc-layer drift sweep `adda diff` structurally cannot do.

`diff` checks that documented module PATHS still exist. It never opens the docs
and ignores docs/ entirely, which is how this repo ran two months with an empty
docs/modules/ while `adda diff` reported "No drift" (2026-08-18). `audit` closes
that hole using MODULE_MAP.json as the routing table.

Five rules:
1) Doc missing: mapped code exists but its doc doesn't (high severity).
2) Map entry stale: both code and doc are gone (low severity).
3) Code unmapped: source escaping the map entirely (medium severity).
4) Doc orphaned: doc exists but its mapped code doesn't (low severity).
5) Doc stale: both exist but the code's last commit is newer than the doc's
   (medium severity). Git history unavailable for either side is never
   treated as fresh — it is recorded in `skipped` instead.

Deterministic and offline — no model calls (ADR-0003). Any rule that cannot run
is REPORTED as skipped, never silently passed: a check that fails quietly is
worse than no check.
"""

import subprocess
from pathlib import Path

from adda.modulemap import is_exempt, load_map
from adda.sync import _map_ignored, discover_modules


def _source_files(repo: Path) -> list[str]:
    """Every source .py under a discovered module, posix-relative to repo."""
    found = []
    for _name, mod_path in discover_modules(repo):
        for py in sorted((repo / mod_path).rglob("*.py")):
            rel = py.relative_to(repo)
            if any(_map_ignored(part) for part in rel.parts[:-1]):
                continue
            found.append(rel.as_posix())
    return found


def _git_out(repo: Path, args: list[str]):
    """Run `git *args` in `repo`; return trimmed stdout, or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return out.stdout.strip()


def last_commit_sha(repo: Path, path: str):
    """Full SHA of the last commit touching `path`; None if unknown.

    None means "cannot tell" (not a git repo, git missing, or untracked) —
    callers must treat it as skipped, never as fresh.
    """
    return _git_out(repo, ["log", "-1", "--format=%H", "--", path])


def _git_rc(repo: Path, args: list) -> int:
    """Exit code of a git command; -1 when git could not be run at all."""
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return -1
    return out.returncode


def _is_ancestor(repo: Path, older: str, newer: str):
    """True / False / None. None means git could not decide, NOT 'no'."""
    rc = _git_rc(repo, ["merge-base", "--is-ancestor", older, newer])
    if rc == 0:
        return True
    if rc == 1:
        return False
    return None  # 128, -1, shallow clone, unknown object: cannot tell


def compare_commits(repo: Path, doc_sha: str, code_sha: str) -> str:
    """'stale' | 'current' | 'unknown' for a doc against its code.

    ponytail: three-state on purpose. A boolean forces 'cannot tell' to
    masquerade as 'not stale', which is a silent pass — the exact defect this
    module exists to catch.
    """
    if doc_sha == code_sha:
        return "current"          # committed together
    if _is_ancestor(repo, doc_sha, code_sha) is True:
        return "stale"            # doc's commit strictly precedes the code's
    if _is_ancestor(repo, code_sha, doc_sha) is True:
        return "current"          # doc's commit follows the code's
    return "unknown"              # divergent, rebased, shallow, or git failed


def audit_report(repo: Path, adda_dir: Path) -> tuple[list[dict], list]:
    """Return (findings, skipped). Findings are {item, issue, severity}."""
    mapping, exempt = load_map(adda_dir)
    findings, skipped = [], []
    unknown = []

    for code, doc in sorted(mapping.items()):
        code_exists = (repo / code).exists()
        doc_exists = (repo / doc).exists()
        # 1) mapped doc was never written (or was deleted)
        if code_exists and not doc_exists:
            findings.append({"item": doc, "issue": "doc missing", "severity": "high"})
        # 2) map entry stale: both code and doc are gone
        elif not code_exists and not doc_exists:
            findings.append({"item": code, "issue": "map entry stale", "severity": "low"})
        # 4) doc outlived the code it documents
        elif doc_exists and not code_exists:
            findings.append({"item": code, "issue": "doc orphaned", "severity": "low"})
        else:
            # doc stale: code changed in a later commit than its doc.
            code_sha, doc_sha = last_commit_sha(repo, code), last_commit_sha(repo, doc)
            if code_sha is None or doc_sha is None:
                unknown.append(doc)
            else:
                result = compare_commits(repo, doc_sha, code_sha)
                if result == "stale":
                    findings.append({"item": doc, "issue": "doc stale", "severity": "medium"})
                elif result == "unknown":
                    unknown.append(doc)

    if unknown:
        skipped.append(
            f"stale-check skipped for {len(unknown)} doc(s): git history unavailable or "
            f"the doc and code commits are not ordered (divergent, rebased, or shallow "
            f"history)"
        )

    # 3) source escaping the map entirely — an explicit map means a new file is
    #    unmapped, and unmapped would otherwise mean silently unenforced.
    for src in _source_files(repo):
        if src not in mapping and not is_exempt(src, exempt):
            findings.append({"item": src, "issue": "code unmapped", "severity": "medium"})

    return findings, skipped
