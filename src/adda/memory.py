# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda memory — an agent's memory drifts like docs do (ENH-ADDA-029).

A memory directory is a set of markdown notes plus an index the agent loads
first (`MEMORY.md` by default). Only the index is read up front, so a note it
does not list is invisible, however correct. This checks the structure
deterministically - it never judges whether a note is TRUE:

- every note is indexed, exactly once; every index entry points at a note
- every `[[link]]` resolves to a note, by frontmatter `name` or filename
- no two notes share a `name` or a description: one fact recorded twice is
  how the two copies drift apart

Each rule is a real incident in this project's own memory: BUG-ADDA-024
orphaned three notes by overwriting the index, and RF-ADDA-009 found a fact
recorded twice where the copy marked for deletion was the correct one.

Tool-neutral: any folder of markdown notes with an index file (ADR-0016).
"""

import re
from pathlib import Path

_FENCE = re.compile(r"^\s*(```|~~~)")
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_WIKI = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
_FIELD = re.compile(r"^(name|description):\s*(.*?)\s*$")


def _live(text: str):
    """(line number, line) outside fenced code blocks."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def _frontmatter(text: str) -> dict:
    """`name` and `description` from a leading `---` block; no YAML dependency."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = _FIELD.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".").lower()


def memory_report(directory: Path, index: str = "MEMORY.md") -> tuple[list[dict], list, dict]:
    """Return (findings, skipped, stats). Findings are {item, issue, severity[, ref]}."""
    findings, skipped = [], []
    notes = sorted(
        p.relative_to(directory).as_posix() for p in directory.rglob("*.md")
        if p.relative_to(directory).as_posix() != index
    )
    texts = {rel: (directory / rel).read_text(encoding="utf-8", errors="replace") for rel in notes}
    meta = {rel: _frontmatter(texts[rel]) for rel in notes}
    stats = {"files": len(notes), "entries": 0, "links": 0}

    # --- the index: every note listed, exactly once, pointing at something real
    index_path = directory / index
    if index_path.is_file():
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        texts[index] = index_text
        seen = {}
        for _, line in _live(index_text):
            for target in _MD_LINK.findall(line):
                if "://" in target or target.startswith("mailto:"):
                    continue
                rel = target.split("#", 1)[0].replace("\\", "/")
                rel = rel[2:] if rel.startswith("./") else rel
                if not rel.endswith(".md"):
                    continue
                stats["entries"] += 1
                seen[rel] = seen.get(rel, 0) + 1
        for rel, count in sorted(seen.items()):
            if rel not in notes:
                findings.append({"item": rel, "issue": "index entry dangling", "severity": "high"})
            elif count > 1:
                findings.append({"item": rel, "issue": "indexed twice", "severity": "medium"})
        for rel in notes:
            if rel not in seen:
                findings.append({"item": rel, "issue": "not indexed", "severity": "high"})
    else:
        skipped.append(f"no {index} in {directory}: cannot check which notes the agent can see")

    # --- [[links]] resolve by frontmatter name or by filename
    known = {Path(rel).stem for rel in notes} | {m["name"] for m in meta.values() if m.get("name")}
    for rel in sorted(texts):
        for number, line in _live(texts[rel]):
            for target in _WIKI.findall(line):
                stats["links"] += 1
                name = target.strip()
                if name not in known and Path(name).stem not in known:
                    findings.append({
                        "item": f"{rel}:{number}", "issue": "link dangling",
                        "severity": "medium", "ref": name,
                    })

    # --- one fact, one note
    for field, issue, severity in (("name", "duplicate name", "high"),
                                   ("description", "duplicate description", "medium")):
        groups = {}
        for rel in notes:
            value = meta[rel].get(field)
            if value:
                groups.setdefault(_norm(value), []).append(rel)
        for rels in groups.values():
            if len(rels) > 1:
                findings.append({"item": ", ".join(sorted(rels)), "issue": issue, "severity": severity})

    return findings, skipped, stats
