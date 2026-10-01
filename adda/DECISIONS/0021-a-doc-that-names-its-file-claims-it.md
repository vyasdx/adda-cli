<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0021 — A doc that names its file claims it

Date: 2026-10-02
Status: accepted
Issue: ENH-ADDA-043 (replaces ENH-ADDA-041)
Extends: ADR-0019

## Context

Adopting ADDA in a product whose docs are named by hand starts with a map where almost nothing
points at a real doc: on one trial repository, 0 of 119 generated paths matched its existing docs,
and every entry had to be pointed by hand. ENH-ADDA-041 proposed mining git history for code and docs
that change together. Scoped before building, it covered 0-13 files per repository — short histories,
renames, and an issue tracker that changes with everything.

The scoping found a better source. Module docs across the products already state which files they
cover, in a `## Files` section or a `**File:**` line. A file named by exactly one module doc was that
doc's file in 4 of 4 checks against this repository's map and 24 of 24 in a hand-checked fleet sample.

## Decision

- **When `sync --map` meets code the map has never seen, and exactly one module doc names it, the
  entry points at that doc.** Otherwise it gets the mirrored default path, as before.
- **Only docs under the module-doc folder count**, and only live lines — not history sections, fenced
  examples or "this was removed" lines. A handover that mentions a file is not its doc; a Change Log
  that says a file moved out does not claim it.
- **A file named by two docs is left unclaimed**: the rule cannot tell which owns it.
- **A product's own choice and its exemptions still win** (ADR-0019).
- `sync --map` says how many new entries came from a naming doc.
- History co-change is not built.

## Consequences

- Across copies of 12 product repositories, entries pointing at an existing doc rose from about 0 to
  37-88% of code files in nine; three gained little or nothing because their docs name files in forms
  that do not match exact paths. This repository's own map is unchanged.
- A doc that names a file it does not really cover now attracts that file. It is visible, not hidden:
  the entry is in the map for review, and `audit` reports the doc as stale when the code moves.
