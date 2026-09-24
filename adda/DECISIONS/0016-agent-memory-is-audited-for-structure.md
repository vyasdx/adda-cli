<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0016 — Agent memory is audited for structure, not truth

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-029

## Context

Coding agents now keep memory between sessions: a folder of markdown notes and
an index the agent loads first. It drifts exactly the way documentation does,
and this project has the incidents to prove it. BUG-ADDA-024: rewriting the
index on a second machine orphaned three notes - still on disk, never loaded,
unnoticed for days because empty memory reads like a project with no rules.
RF-ADDA-009: one fact recorded twice, once per machine, and the copy marked for
deletion was the correct one. Both were found by hand.

Nothing in the tools landscape checks this. Memory products store and retrieve;
none ask whether what is stored is still consistent.

## Decision

- **`adda memory <dir>` checks structure, deterministically.** Every note is in
  the index exactly once; every index entry exists; every `[[link]]` resolves;
  no two notes share a `name` or a description. Exit 1 on any finding.
- **It does not judge truth.** Whether a note is still correct needs a reader or
  a model; ADR-0003 keeps model calls out. Paraphrased duplicates are therefore
  out of reach, and the docs say so.
- **Tool-neutral.** A folder of markdown notes plus an index file, name
  configurable. Claude Code's auto-memory is one instance; nothing in the check is
  specific to it (the provider-agnostic scope guard).
- **A separate command, not an `audit` rule.** Memory usually lives outside the
  repository, and `audit` requires the repository's map.
- **Cannot tell is said.** No index means no statement about what the agent
  sees; that is reported in `skipped`, never passed.

## Consequences

- The by-hand check RF-ADDA-009 ran (7 files, 7 entries, 11 links, 0 orphans) is
  now one command; on today's memory it reads 8 / 8 / 13, no drift.
- A note that is wrong but well-formed passes. That is the boundary, as with
  `audit --refs` and omissions (ADR-0011).
