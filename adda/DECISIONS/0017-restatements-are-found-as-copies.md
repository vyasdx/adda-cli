<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0017 — Restatements are found as copies, on demand

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-031

## Context

On 2026-09-14 a claim that silo1 sat outside the ops dashboard's coverage had
spread into four places. The correction fixed three; the fourth was found later
by a manual grep. ENH-ADDA-031 asked whether a deterministic check could list
the other places a corrected fact is still stated. The row said to scope before
building, because false alarms were the obvious risk.

A prototype was run over this repository's last 40 commits and every hit was
labelled by hand. The motivating incident turned out to be out of reach: the
fourth copy lived in agent memory, outside git, and the in-repo copies used three
different wordings. But the prototype found two stale statements still live,
including an answered message in the project's internal tracker that a
correction had missed.

## Decision

- **Build it as `adda restated`, advisory and run on purpose, not a gate.** Of 23
  hits, about half needed an edit and nearly all were worth reading. Good enough
  for a check you run after a correction; not good enough to block commits.
- **Six-word copies of prose the commit removed.** Measured: five words matched
  code idioms, eight missed real restatements. Only phrases gone from the file
  afterwards, never ones the same commit wrote elsewhere (a move).
- **Records are shown apart and do not fail the run.** Logs, snapshots,
  changelogs and history sections are not searched; dated lines, closed rows and
  superseded files are grouped as `records`. They restate old facts by design.
- **The repo is searched as it is now (HEAD)**, so re-checking an older correction
  reports only copies still standing today.
- **Untracked directories can be added** (`--also`), because agent memory is
  where the real fourth copy lived.
- **Paraphrase is out of scope, and the output says so every time.** Seeing a
  reworded fact would take a model, which ADR-0003 rules out.

## Consequences

- A correction can now be followed by one command that lists the verbatim copies
  left standing. It would not have caught the incident that motivated it, and the
  docs say that plainly rather than letting a clean run imply more.
- Precision is lower than ADDA's other checks. That is acceptable only because
  it is opt-in and advisory; making it a gate would need a new decision.
