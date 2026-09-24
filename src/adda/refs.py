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


def extract_refs(text: str) -> list[tuple[int, str]]:
    """(line number, name) for every code name cited outside history and fences.

    A history section runs from its heading to the next heading at the same or a
    shallower level, so `### notes` inside a Change Log stays history while a
    later `## Section` is checked again.
    """
    refs, history_level, in_fence = [], None, False
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
        if history_level is not None:
            continue
        for span in _SPAN.findall(line):
            name = _code_name(span)
            if name:
                refs.append((number, name))
    return refs


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
        for line, name in extract_refs(text):
            stats["refs"] += 1
            if name not in names:
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
