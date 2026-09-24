# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda restated — a corrected fact left standing elsewhere (ENH-ADDA-031).

When a commit corrects a fact in one file, other files that state the old
version stay wrong, and nothing says so. Given a commit, this lists the files
that still contain, word for word, the prose the commit removed.

How (ADR-0017): every 6-word phrase of prose on a removed line that is gone from
the file afterwards - and was not written somewhere new by the same commit,
which would make it a move - is searched for in the tracked prose files as
they are now (HEAD). Consecutive matches merge into one hit per line.

It finds COPIES, never paraphrases: "not covered by the ops dashboard" and
"outside the ops dashboard's coverage" share nothing it can see, and that is
exactly the case that motivated it. Advisory and run on purpose, not a gate:
a prototype over this repo's last 40 commits found about half its hits needed
an edit and nearly all were worth reading. Deterministic, offline, and it never
checks anything out.
"""

import re
import subprocess
from pathlib import Path

K = 6  # words per phrase: 5 matched code idioms, 8 missed real restatements
_TOKEN = re.compile(r"[a-z0-9]+(?:['._/-][a-z0-9]+)*")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_HISTORY = re.compile(r"change\s*-?\s*log|history", re.I)
_FENCE = re.compile(r"^\s*(```|~~~)")
_RULE = re.compile(r"^\s*\|?\s*:?-{3,}")  # table separator or frontmatter fence
_PROSE = (".md", ".txt", ".rst")
# Append-only records and generated snapshots restate old facts by design.
_SKIP_DIRS = {"log", "logs", "checkpoints"}
# A line, row or file that dates itself is a record of what was believed then.
_DATED = re.compile(r"\[\d{4}-\d{2}-\d{2}\]|\bclosed \d{4}-\d{2}-\d{2}\b", re.I)
_SUPERSEDED = re.compile(r"\bsuperseded\b", re.I)


def _git(repo: Path, *args, data=None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, input=data, capture_output=True, check=True, timeout=60,
    ).stdout


def _searched(path: str) -> bool:
    parts = path.split("/")
    return (path.lower().endswith(_PROSE) and not parts[-1].upper().startswith("CHANGELOG")
            and not any(p.lower() in _SKIP_DIRS for p in parts[:-1]))


def _tokens(text: str) -> list:
    """[(word, line) | None]: prose words, with None at every paragraph break.

    Headings, blank lines, table rows and fences break phrases; fenced code and
    history sections are dropped entirely.
    """
    out, history, fence = [], None, False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            fence = not fence
            out.append(None)
            continue
        if fence:
            continue
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if history is not None and level <= history:
                history = None
            if history is None and _HISTORY.search(heading.group(2)):
                history = level
            out.append(None)
            continue
        stripped = line.strip()
        if history is not None or not stripped or _RULE.match(stripped):
            out.append(None)
            continue
        row = stripped.startswith("|")
        out.extend([None] if row else [])
        out.extend((w, number) for w in _TOKEN.findall(line.lower()))
        out.extend([None] if row else [])
    return out


def _phrases(tokens):
    """(phrase, first line, last line) for every K-word run inside one paragraph."""
    run = []
    for t in tokens:
        if t is None:
            run = []
            continue
        run.append(t)
        if len(run) >= K:
            window = run[-K:]
            yield tuple(w for w, _ in window), window[0][1], window[-1][1]


def _changes(repo: Path, rev: str) -> dict:
    """{old path: {old, new, new_path, removed:{lines}, added:{lines}}} for rev^..rev."""
    raw = _git(repo, "diff", "--no-color", "-M", "--unified=0", "--raw", "-p", "--abbrev=40",
               f"{rev}^", rev).decode("utf-8", "replace")
    files, cur, old_n, new_n = {}, None, 0, 0
    for line in raw.splitlines():
        if line.startswith(":"):
            meta, *paths = line.split("\t")
            parts = meta.split()
            files[paths[0]] = {"old": None if parts[4].startswith("A") else parts[2],
                               "new": None if parts[4].startswith("D") else parts[3],
                               "new_path": paths[-1], "removed": set(), "added": set()}
        elif line.startswith("diff --git"):
            cur = None
        elif line.startswith("--- "):
            cur = line[6:] if line.startswith("--- a/") else None
        elif line.startswith("+++ ") and cur is None and line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            old_n, new_n = int(m.group(1)), int(m.group(2))
        elif cur in files and line[:1] in "-+":
            if line[0] == "-":
                files[cur]["removed"].add(old_n)
                old_n += 1
            else:
                files[cur]["added"].add(new_n)
                new_n += 1
    return files


def _blobs(repo: Path, shas) -> dict:
    """sha -> text (None for binary), read in one `git cat-file --batch`."""
    shas = [s for s in dict.fromkeys(shas) if s]
    if not shas:
        return {}
    out, i, texts = _git(repo, "cat-file", "--batch", data=("\n".join(shas) + "\n").encode()), 0, {}
    for sha in shas:
        eol = out.index(b"\n", i)
        size = int(out[i:eol].split()[2])
        data = out[eol + 1: eol + 1 + size]
        i = eol + 2 + size
        texts[sha] = None if b"\0" in data[:8000] else data.decode("utf-8", "replace")
    return texts


def _touching(phrases, lines):
    for phrase, first, last in phrases:
        if any(first <= n <= last for n in lines):
            yield phrase, first


def restated_report(repo: Path, rev: str = "HEAD", also=()) -> tuple[list, list, list]:
    """Return (current, records, skipped).

    Hits are {file, line, source, words, text}. `records` holds hits on dated
    lines, closed rows and superseded files - history, shown apart so it is not
    mistaken for work. `also` adds untracked directories, such as agent memory.
    """
    if not _git(repo, "rev-list", "--parents", "-n", "1", rev).split()[1:]:
        return [], [], [f"{rev} has no parent commit, so there is nothing it removed to compare"]
    changes = {p: c for p, c in _changes(repo, rev).items()
               if p.lower().endswith(_PROSE) or c["new_path"].lower().endswith(_PROSE)}
    tree = {}
    # Searched as the repo is NOW: "still stated" means today, so a copy fixed
    # after the correction is not reported. Right after a correction rev is HEAD.
    for entry in _git(repo, "ls-tree", "-r", "-z", "HEAD").decode("utf-8", "replace").split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            if meta.split()[1] == "blob" and _searched(path):
                tree[path] = meta.split()[2]
    texts = _blobs(repo, list(tree.values()) + [c[k] for c in changes.values() for k in ("old", "new")])
    targets = {p: texts[s] for p, s in tree.items() if texts.get(s) is not None}
    for d in also:
        for f in sorted(Path(d).rglob("*.md")):
            targets[f"{Path(d).as_posix()}/{f.relative_to(d).as_posix()}"] = (
                f.read_text(encoding="utf-8", errors="replace"))

    # Phrases this commit wrote somewhere they were not before: a removed phrase
    # that reappears there was moved, not retracted.
    written = set()
    for c in changes.values():
        new, old = texts.get(c["new"]) or "", texts.get(c["old"]) or ""
        if new and c["added"]:
            had = {p for p, _, _ in _phrases(_tokens(old))}
            written |= {p for p, _ in _touching(_phrases(_tokens(new)), c["added"])} - had

    hits = []
    for src, c in changes.items():
        old = texts.get(c["old"])
        if old is None or not c["removed"]:
            continue
        kept = {p for p, _, _ in _phrases(_tokens(texts.get(c["new"]) or ""))}
        gone = {}
        for phrase, line in _touching(_phrases(_tokens(old)), c["removed"]):
            if phrase not in kept and phrase not in written:
                gone.setdefault(phrase, line)
        if not gone:
            continue
        for path, text in targets.items():
            if path in (src, c["new_path"]):
                continue
            span = None
            for i, (phrase, first, _) in enumerate(_phrases(_tokens(text))):
                if phrase not in gone:
                    continue
                if span and span["i"] == i - 1:
                    span["i"], span["words"] = i, span["words"] + [phrase[-1]]
                else:
                    if span:
                        hits.append(span)
                    span = {"file": path, "line": first, "source": f"{src}:{gone[phrase]}",
                            "i": i, "words": list(phrase)}
            if span:
                hits.append(span)

    best = {}
    for h in hits:
        key = (h["file"], h["line"])
        if key not in best or len(h["words"]) > len(best[key]["words"]):
            best[key] = h
    current, records = [], []
    for (path, line), h in sorted(best.items()):
        hit = {"file": path, "line": line, "source": h["source"], "words": len(h["words"]),
               "text": " ".join(h["words"])[:200]}
        lines = targets[path].splitlines()
        dated = _DATED.search(lines[line - 1]) or _SUPERSEDED.search("\n".join(lines[:10]))
        (records if dated else current).append(hit)
    return current, records, []
