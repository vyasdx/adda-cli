<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0020 — Markdown links are checked exactly, and reported

Date: 2026-10-02
Status: accepted
Issue: ENH-ADDA-040
Extends: ADR-0012, ADR-0014

## Context

`audit --refs` checked paths written in backticks. The most common way a README or an agent
instruction file points at a file is a markdown link, `[setup](docs/setup.md)`, and those were never
read. The gap surfaced while studying another tool (GIT-387), which parses the same links and
silently drops the ones whose target does not exist.

A backticked path is ambiguous — relative to the repository root, the file's folder, or another
repository entirely — so ADR-0012 checks one only when its first segment exists here. A link is not
ambiguous: markdown resolves it against the file it is written in.

## Decision

- **Inline links, images and reference definitions are checked** in every instruction file
  `--refs` reads. URLs, other schemes and `#anchors` are not files; a `#fragment` or `?query` is
  cut; percent-encoding and `<...>` wrapping are undone.
- **A link resolves from its own file's folder; a leading `/` means the repository root.** No
  first-segment guess is needed, so a dead link inside the repository is always reported, as
  `link missing`.
- **A link that leaves the repository is unresolved** — counted and printed, never flagged.
- Links in code spans, fenced blocks, history sections and "this was removed" lines are skipped,
  and gitignored targets are excused, exactly as for backticked paths.
- **Reported, never dropped** — the opposite of the tool that suggested the idea.
- HTML `<a href>` and `<img src>` are not read. Nobody has needed them yet.

## Consequences

- Run across ADDA, its public tree, five benchmark repositories and 22 fleet repositories: one
  finding, and it is real — fastapi's root README is generated from `docs/en/docs/index.md`, and a
  link that resolves there (`tutorial/`) is broken once copied to the root. Checking links from
  the file's own folder is what makes that visible.
- Every rule was shown to matter by removing it; one branch was dead code and was deleted.
