<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0031 — Repository text is printed without control characters, and OKF is not marked

Date: 2026-11-15
Status: accepted
Issue: BUG-ADDA-050 (L2, L3, L6)
Relates to: ADR-0030

## Context

The 2026-11-14 security review left three low-severity items open after 0.5.8:

- **L3, part 1.** Text from the repository reaches ADDA's output unchanged.
  A filename or a link target can carry terminal escape codes, which can hide
  or rewrite lines of a report on screen.
- **L3, part 2.** `rehydrate` and `export` pass the project's constraints and
  ADR titles to an agent with nothing saying where they came from.
- **L2.** Matching spans in `refs` takes time quadratic in line length (a
  48 KB line took 5 s), and every repository's `README.md` is read.
- **L6.** The optional `headroom-ai` extra was unpinned, and `--compress`
  hands it the whole OKF.

Marking where OKF text came from would add fields to OKF, and OKF 0.2 is a
locked format (`OKF_SCHEMA.md`).

## Decision

- **Everything the CLI prints goes through `safety.printable`.** It drops C0
  control characters other than tab and newline, plus DEL and C1. Report text
  stays readable and can no longer drive the terminal. Files ADDA writes are
  unchanged. JSON output already escapes C0, so it is unaffected except for C1.
- **OKF is not marked.** No provenance fields are added. The text an agent gets
  from `rehydrate` is the project's own architecture memory, written by the
  people who also write its `AGENTS.md`; marking it would protect against the
  repository's own authors. ADDA itself never acts on that text.
- **`refs` skips what it cannot check in time,** and says so in `skipped`: a
  doc over 1 MB, and any line over 10,000 characters. A long line is blanked,
  not removed, so line numbers in findings stay true.
- **`headroom-ai` is pinned to 0.44.0,** the release `--compress` was checked
  against. It needs Python 3.11, so on 3.10 the extra installs nothing and
  `--compress` stays a no-op.

## Consequences

- A stale name inside a line over 10,000 characters is not found. The
  `skipped` list names the file, so nothing passes as "checked, clean".
- Moving to a newer `headroom-ai` is a deliberate change: check `--compress`
  against it, then move the pin.
- Trigger for marking OKF text: the next OKF format version. Provenance
  (`source` path and commit) is a candidate field for it.
