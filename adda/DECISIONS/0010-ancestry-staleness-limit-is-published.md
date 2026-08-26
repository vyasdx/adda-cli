<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0010 — The limit of ancestry-based staleness is published, not patched

Date: 2026-08-26
Status: accepted
Issue: DEC-ADDA-010

## Context

`audit` decides staleness by git commit ancestry: a doc whose last commit is an
ancestor of the code's last commit was written first and has not been touched
since. That answers *was this doc left behind?* reliably and offline.

It cannot answer *was this doc updated, but updated wrongly?*

RF-ADDA-005 was exactly that, in this repo. Two module docs contradicted
themselves one day after being written — `audit.md` described a function deleted
in the same commit, `sync.md` listed a stale public surface. Both were committed
alongside their code, so ancestry called them current. The commit gate passed,
`audit` passed, CI was green. A human reviewer found them.

## Decision

State it in the README, in its own section, in the user's language.

It is not patchable. Detecting a *wrong* doc requires understanding what the doc
claims and comparing it to what the code does — that is a model call, and
ADR-0003 keeps `audit` deterministic and offline. Adding one would change what
this tool is.

The alternative — say nothing — lets a user discover the gap themselves and
conclude the whole check is unreliable. A boundary the tool states is a
limitation; a boundary the user finds is a defect.

## Consequences

- README gains "What staleness detection cannot see", covering this plus the two
  related boundaries: undecidable ancestry (reported under `[skipped]`) and
  roots discovery chose to skip (ADR-0009).
- The honest claim narrows: ADDA detects **the doc nobody touched**, not the doc
  someone touched carelessly. The first is the common failure and worth
  automating; the second still needs review.
- If a semantic check is ever wanted it is a new, clearly-separate opt-in
  surface, not a change to `audit`.
