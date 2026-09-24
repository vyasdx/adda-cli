# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda audit --refs — a code name a doc cites must still exist in the code.

Ancestry answers "was this doc left behind?" and nothing else (ADR-0010). It
cannot see a doc that was committed alongside its code but committed wrong -
RF-ADDA-005 was two such docs, and a human found them. This rule catches the
deterministic slice of that gap (ADR-0011): a doc that names an identifier which
no longer appears anywhere in the source. It does not judge whether a doc's
prose is TRUE; that would take a model call, which ADR-0003 rules out.

It is opt-in because a new rule has a new false-positive profile, and a checker
that cries wolf teaches people to stop reading it. Each exclusion below is a
false positive found while prototyping this against ADDA's own docs:

- history sections (a Change Log exists to name code that is gone)
- builtins and keywords (`KeyError` is real, just not ours)
- names defined outside the doc's own module, including in tests
- fenced code blocks (examples, not claims)
- spans that are not code names (`stale`, `--json`, `okf.json`)

Deterministic and offline. Anything undecidable is reported in `skipped`, never
counted as a pass.
"""

import builtins
import keyword
import os
import re
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

from adda.modulemap import load_map
from adda.sync import IGNORE_DIRS, SOURCE_SUFFIXES

# Broader than source discovery, on purpose. Discovery answers "what needs a
# doc?", so it leaves out tests and scripts. This answers "does this name exist
# anywhere in the code?", and a doc may legitimately cite a name that lives in a
# test helper or a script. Searching more code can only turn a flag into a pass,
# which is the safe direction for a rule whose failure mode is false alarms.
_CORPUS_SKIP = IGNORE_DIRS - {"tests", "test", "scripts", "examples"}

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HISTORY = re.compile(r"change\s*log|history", re.I)
# A line naming something in order to say it is gone is accurate, not drift -
# the one-line version of a Change Log. Found in a real instruction file as a
# path followed by "is RETIRED - ignore it" (ENH-ADDA-024).
_GONE = re.compile(
    r"\b(retired|removed|deleted|deprecated|obsolete|no longer|renamed|replaced|formerly)\b", re.I
)
_FENCE = re.compile(r"^\s*(```|~~~)")
_SPAN = re.compile(r"`([^`\n]+)`")
_NAME = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(\(\))?$")
_CAMEL = re.compile(r"[a-z][A-Z]")
_NOT_OURS = set(dir(builtins)) | set(keyword.kwlist)


def _code_name(span: str):
    """The identifier a backticked span names, or None if it is not a code name.

    Only spans shaped like code count: snake_case, CamelCase, or written as a
    call. A bare word like `stale` is prose that happens to be in backticks.
    """
    m = _NAME.match(span.strip())
    if not m:
        return None
    name, called = m.group(1), m.group(2)
    if name in _NOT_OURS or len(name.strip("_")) < 2:
        return None
    if "_" in name or called or _CAMEL.search(name):
        return name
    return None


def _live_lines(text: str):
    """(line number, line) for every line that makes a claim about the present.

    Skipped: fenced code blocks (examples), history sections (a Change Log names
    code that is gone), and single lines that name something to say it is gone.
    A history section runs from its heading to the next heading at the same or a
    shallower level, so `### notes` inside a Change Log stays history while a
    later `## Section` is checked again.
    """
    history_level, in_fence = None, False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if history_level is not None and level <= history_level:
                history_level = None
            if history_level is None and _HISTORY.search(heading.group(2)):
                history_level = level
        if history_level is not None or _GONE.search(line):
            continue
        yield number, line


# A definition at the start of a line inside a fenced example: `def`/`class`/
# `function`/`const`/`let`/`var NAME`, or `NAME:` / `NAME =` (a field or an
# assignment - `==` is a comparison, not a definition).
_DEFINES = re.compile(
    r"^\s*(?:(?:async\s+)?def|class|function|const|let|var)\s+([A-Za-z_]\w*)"
    r"|^\s*([A-Za-z_]\w*)\s*(?::(?!:)|=(?!=))"
)


def _example_defs(text: str) -> set[str]:
    """Names the doc's own fenced examples define (BUG-ADDA-026).

    Prose explaining an example names what the example defines - fastapi's
    README defines `is_offer` in a model, then describes it. That is a claim
    about the example, not the code. Only definitions count: a name an example
    merely *uses* is still checked, so a stale example calling deleted code
    cannot excuse the prose that cites it.
    """
    defs, in_fence = set(), False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence and (m := _DEFINES.match(line)):
            defs.add(m.group(1) or m.group(2))
    return defs


def extract_refs(text: str) -> list[tuple[int, str]]:
    """(line number, name) for every code name cited on a live line."""
    return [
        (number, name)
        for number, line in _live_lines(text)
        for span in _SPAN.findall(line)
        if (name := _code_name(span))
    ]


def _code_names(repo: Path):
    """Every identifier-shaped token in the repo's code, or None if there is no code.

    None is "cannot tell": with nothing to compare against, every cited name
    would read as missing, which is a false alarm, not a finding.
    """
    names, files = set(), 0
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in _CORPUS_SKIP and not d.startswith(".")]
        for filename in filenames:
            if not filename.endswith(SOURCE_SUFFIXES):
                continue
            try:
                text = (Path(dirpath) / filename).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            files += 1
            names.update(_IDENT.findall(text))
    return names if files else None


def refs_report(repo: Path, adda_dir: Path) -> tuple[list[dict], list, dict]:
    """Return (findings, skipped, stats) for every mapped doc that exists.

    Findings are {item, issue, severity, ref}, where item is `doc:line`. Stats
    count the docs read and the names checked, so an empty result can always be
    told apart from a check that looked at nothing.
    """
    mapping, _ = load_map(adda_dir)
    findings, skipped, stats = [], [], {"docs": 0, "refs": 0}

    names = _code_names(repo)
    if names is None:
        skipped.append("refs-check skipped: no source files found to check cited names against")
        return findings, skipped, stats

    unreadable = []
    for doc in sorted(set(mapping.values())):
        path = repo / doc
        if not path.is_file():
            continue  # a missing doc is audit rule 1's finding, not a second one here
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unreadable.append(doc)
            continue
        stats["docs"] += 1
        local = _example_defs(text)
        for line, name in extract_refs(text):
            stats["refs"] += 1
            if name not in names and name not in local:
                findings.append({
                    "item": f"{doc}:{line}", "issue": "ref missing",
                    "severity": "medium", "ref": name,
                })

    if unreadable:
        skipped.append(
            f"refs-check skipped for {len(unreadable)} doc(s) that could not be read "
            f"as UTF-8: {', '.join(unreadable)}"
        )
    return findings, skipped, stats


# --- ENH-ADDA-024 / ADR-0012: instruction files ------------------------------
#
# The files an agent reads before any code. They describe the whole repo rather
# than one path, so they are not mapped docs - ancestry against "all the code"
# would read stale forever. What can be checked mechanically is that the names
# and paths they cite still exist. The conventional files need no
# configuration; a project adds its own under `instructions` in MODULE_MAP.json,
# which `sync --map` carries over since ENH-ADDA-028.

# The files each tool documents reading, verified against its official docs on
# 2026-09-24 (ADR-0014 lists the sources). Patterns are fnmatch, where `*` also
# crosses `/`, so `.cursor/rules/*.mdc` covers nested rule folders too.
# Read in any directory: the tools document picking these up below the root.
_ANY_DIR = (
    "AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "GEMINI.md",
    ".cursor/rules/*.mdc", ".cursor/rules/*.md", ".windsurf/rules/*.md", ".devin/rules/*.md",
)
# Read at the repository root only.
_ROOT_ONLY = (
    "README.md", "AGENT.md", ".rules",
    ".github/copilot-instructions.md", ".github/instructions/*.instructions.md",
    ".claude/CLAUDE.md", ".claude/rules/*.md",
    ".cursorrules", ".windsurfrules",
    ".clinerules", ".clinerules/*.md", ".cline/rules/*.md",
    ".roorules", ".roo/rules/*.md", ".roo/rules-*/*.md",
    ".continue/rules/*.md", ".amazonq/rules/*.md",
    ".junie/AGENTS.md", ".junie/guidelines.md", ".junie/playbook.md", ".junie/rules/*.md",
)
# Dependency, build and cache trees. Unlike the name corpus, docs/ and tests/
# are searched: a `docs/AGENTS.md` is read by the tools like any other.
_WALK_SKIP = IGNORE_DIRS - {"tests", "test", "docs", "doc", "scripts", "examples", ".github"}


def _convention(rel: str):
    """The directory whose tools read `rel` as instructions, or None.

    "" for the root. A nested `pkg/AGENTS.md` returns "pkg", so its paths can be
    resolved from where it sits as well as from the root.
    """
    if any(fnmatchcase(rel, p) for p in _ROOT_ONLY + _ANY_DIR):
        return ""
    for p in _ANY_DIR:
        if fnmatchcase(rel, "*/" + p):
            first = p.split("/")[0]  # `AGENTS.md`, or `.cursor` for a rules folder
            return rel[: rel.rfind("/" + first + ("/" if "/" in p else ""))]
    return None


def _discover(repo: Path) -> list[tuple[str, str]]:
    """(file, its directory) for every conventional instruction file, sorted.

    Names match with exact case, as the tools on a case-sensitive runner would
    see them. Gitignored files are left out: a personal file that exists on one
    machine would make the same commit pass on CI and fail locally.
    """
    found = []
    for here, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in _WALK_SKIP]
        base = Path(here).relative_to(repo).as_posix()
        for name in files:
            rel = name if base == "." else f"{base}/{name}"
            owner = _convention(rel)
            if owner is not None:
                found.append((rel, owner))
    ignored = _ignored_many(repo, [rel for rel, _ in found])
    return sorted(f for f in found if f[0] not in ignored)


def _generic(path: str) -> bool:
    """Does `path` merely name a convention, e.g. a README listing what tools read?"""
    return _convention(path) is not None

# Path-shaped: only path characters, and either a slash or a file extension.
# The character set is also what excludes globs (`*`, `?`, `[`) and
# placeholders (`<today>`): patterns are not paths. Both were false positives
# in ADDA's own instruction files.
_PATH_CHARS = re.compile(r"^[A-Za-z0-9_.{},/-]+$")
_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,6}$")
_BRACES = re.compile(r"\{([^{}]*)\}")


def _expand_braces(path: str) -> list[str]:
    """`src/{a,b}.py` -> [`src/a.py`, `src/b.py`]; nested groups expand in turn."""
    m = _BRACES.search(path)
    if not m:
        return [path]
    head, tail = path[: m.start()], path[m.end():]
    return [p for part in m.group(1).split(",") for p in _expand_braces(head + part + tail)]


def extract_paths(text: str) -> list[tuple[int, str]]:
    """(line number, repo-relative path) for every path cited on a live line.

    Globs and `<placeholders>` are patterns, not paths. A leading `/` means the
    repo root, not the filesystem root. Brace lists are expanded so each member
    is checked on its own.
    """
    out = []
    for number, line in _live_lines(text):
        for span in _SPAN.findall(line):
            span = span.strip()
            if not _PATH_CHARS.match(span):
                continue
            if "/" not in span and not _EXTENSION.search(span):
                continue
            out.extend((number, p) for p in _expand_braces(span.lstrip("/")) if p)
    return out


def _exists_exact(repo: Path, rel: str) -> bool:
    """True only if every segment matches on disk with the exact case.

    A case-insensitive disk would pass `Docs/Guide.md` for `Docs/guide.md` while
    Linux CI fails it; matching exactly gives both machines the same answer.
    """
    here = repo
    for part in [p for p in rel.split("/") if p]:
        try:
            if part not in os.listdir(here):
                return False
        except OSError:
            return False
        here = here / part
    return True


def _ignored(repo: Path, rel: str) -> bool:
    """Is `rel` gitignored? A generated file exists on a working machine and not on
    a clean checkout, so it is neither present nor missing - just not ours to check."""
    try:
        out = subprocess.run(
            ["git", "check-ignore", "-q", rel], cwd=repo, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def _ignored_many(repo: Path, rels: list[str]) -> set[str]:
    """The subset of `rels` that git ignores, in one call. Outside a git repo,
    or if git fails, nothing is treated as ignored."""
    if not rels:
        return set()
    try:
        out = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"], cwd=repo, capture_output=True,
            input="\0".join(rels).encode("utf-8"), timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    return {p for p in out.stdout.decode("utf-8").split("\0") if p}


def instructions_report(repo: Path, extra=()) -> tuple[list[dict], list, dict]:
    """Return (findings, skipped, stats) for the instruction files present.

    `extra` names files a project configured itself. Unlike a conventional file,
    one that is absent is reported: a typo in the config must not read as
    "checked, all clean".

    A path is checked only when its first segment exists in this repo. Anything
    else - another repository, a file relative to some other directory, a slash
    command - is `unresolved`: counted and reported, never flagged, because this
    rule cannot tell those apart and a false alarm costs more than a miss.
    """
    findings, skipped = [], []
    stats = {"files": 0, "refs": 0, "paths": 0, "unresolved": 0}
    configured = list(dict.fromkeys(extra))
    absent = [f for f in configured if not _exists_exact(repo, f)]
    if absent:
        skipped.append(
            f"configured instruction file(s) not found, so not checked: {', '.join(absent)}"
        )
    present = _discover(repo)
    seen = {rel for rel, _ in present}
    present += [(f, "") for f in configured if f not in absent and f not in seen]
    if not present:
        return findings, skipped, stats

    names = _code_names(repo)
    if names is None:
        skipped.append("instruction-file name check skipped: no source files found")
    unreadable = []
    for rel, home in present:
        # Where a cited path may be anchored: the root, and for a nested file
        # its own directory too - tools differ, and few document it.
        bases = [""] + ([home] if home else [])
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unreadable.append(rel)
            continue
        stats["files"] += 1
        if names is not None:
            local = _example_defs(text)
            for line, name in extract_refs(text):
                stats["refs"] += 1
                if name not in names and name not in local:
                    findings.append({
                        "item": f"{rel}:{line}", "issue": "ref missing",
                        "severity": "medium", "ref": name,
                    })
        for line, path in extract_paths(text):
            # Docs about AI tooling list the conventional instruction files by
            # name, generically. Citing one is not a claim that it exists here -
            # found when ADDA's own README tripped this rule on its first run.
            first = path.split("/")[0]
            anchored = [f"{b}/{path}" if b else path for b in bases
                        if _exists_exact(repo, f"{b}/{first}" if b else first)]
            if not anchored or (_generic(path) and not _exists_exact(repo, path)):
                stats["unresolved"] += 1
                continue
            stats["paths"] += 1
            if not any(_exists_exact(repo, p) or _ignored(repo, p) for p in anchored):
                findings.append({
                    "item": f"{rel}:{line}", "issue": "path missing",
                    "severity": "medium", "ref": path,
                })

    if unreadable:
        skipped.append(
            f"instruction-file check skipped for {len(unreadable)} file(s) that could "
            f"not be read as UTF-8: {', '.join(unreadable)}"
        )
    return findings, skipped, stats
