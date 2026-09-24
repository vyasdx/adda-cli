<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `memory` - `src/adda/memory.py`

Last verified: 2026-09-24

**Purpose** - Audit an agent's memory directory the way `audit` checks docs (ADR-0016). A memory directory is markdown notes plus an index the agent loads first; a note the index does not list is invisible however correct, and one fact recorded twice drifts into two facts. Deterministic and structural: it never judges whether a note is true.

## Public surface

`memory_report(directory, index="MEMORY.md") -> (findings, skipped, stats)`. Findings are `{"item", "issue", "severity"[, "ref"]}`; stats are `{"files", "entries", "links"}`.

CLI: `adda memory <dir> [--index NAME] [--json]` - exit 1 on any finding.

## Invariants

- **Every note indexed, exactly once; every index entry real.** `not indexed` (high) - the BUG-ADDA-024 shape, where overwriting the index orphaned three notes. `index entry dangling` (high). `indexed twice` (medium).
- **`[[links]]` resolve by frontmatter `name` or by filename stem** - both are how people write them. Unresolved: `link dangling` (medium) with `file:line`.
- **One fact, one note.** Two notes with the same frontmatter `name` (high) or the same description after normalising case, spacing and a trailing period (medium) - the RF-ADDA-009 shape. Paraphrased duplicates are not caught; that would need judgement, which ADR-0003 rules out.
- **Only real entries count.** Links inside fenced code, external URLs (even ones ending in `.md`) and non-markdown targets are not index entries.
- **No index is reported, never passed.** Without it nothing can be said about what the agent sees, so it goes in `skipped`, and the link and duplicate checks still run.
- **Always states how much it checked** - files, index entries, links - so a check that looked at nothing never reads as clean.
- **Tool-neutral.** Any folder of markdown notes with an index file; the index name is an option. No YAML dependency: only `name` and `description` are read from frontmatter.
- Every rule shown to matter: removing each of eight turns a test red (one first survived and exposed a weak test, then tightened).

## Change Log (newest first)

- [2026-09-24] ENH-ADDA-029 - module created · agent memory drifts like docs: BUG-ADDA-024 orphaned three notes and RF-ADDA-009 found one fact recorded twice, both found by hand. On this project's own memory: 8 files, 8 index entries, 13 links, no drift - the same result RF-ADDA-009 reached by hand, now one command.
