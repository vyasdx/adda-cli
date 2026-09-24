<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0018 — `audit --refs` runs in CI as a warning

Date: 2026-09-24
Status: accepted
Issue: DEC-ADDA-013
Supersedes: the "not yet in ADDA's own CI" bullet of ADR-0012

## Context

ADR-0011 and ADR-0012 kept `audit --refs` opt-in and out of this repository's
CI: a new rule earns default status by running clean first, and the instruction
files carry a block synced in from outside the repository, which nobody here can
fix. Since then it has run clean on every commit of this repository, on the
published copy, and on five benchmark repositories after one false-positive fix
(BUG-ADDA-026).

Left out of CI, it only runs when someone remembers to run it - the failure mode
ADDA exists to remove.

## Decision

- **CI runs `adda audit . --refs` on every push, and a finding raises a warning
  annotation, not a failure.** Dead references are visible the day they appear.
- **The plain `audit` step still fails hard**, so doc drift enforcement is
  unchanged.
- **Why not blocking:** a change to the externally synced block that cites a path
  this repository does not have would turn every build red over text nobody here
  can edit. A gate people learn to override is worse than a warning they read.

## Consequences

- If warnings are ignored in practice, the next step is blocking with a way to
  mark a synced region as not-ours - a separate decision, taken on evidence.
- The public repository runs the same workflow and gets the same advisory step.
