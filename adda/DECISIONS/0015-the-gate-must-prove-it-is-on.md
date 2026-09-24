<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0015 — The gate must be able to prove it is on

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-030
Extends: ADR-0007

## Context

ADR-0007 made enforcement mechanical and commit-scoped, and the hook stub fails
open: when its interpreter is gone it exits 0, so a deleted venv cannot brick
every commit in the repository. That trade is right, and it has a cost. A gate
that cannot run looks exactly like a gate that ran and found nothing.

This repository has hit that more than once. Hooks are never cloned, so every
fresh clone starts ungated and nothing says so; the 2026-09-14 move to a second
machine had to prove the gate by hand. While designing this check a third case
turned up: with `core.hooksPath` set, `hook install` wrote to a directory git
never reads, printed "Installed", and a commit of undocumented code went through
(BUG-ADDA-027).

This is the failure class ADDA exists to catch, sitting inside ADDA: a check
reporting success while structurally unable to run.

## Decision

- **`adda doctor` checks the gate end to end and exits 1 on any failure.** The
  hook exists where git actually looks (asked of git, not assumed), it runs the
  ADDA gate, it is executable, its baked interpreter exists and can import
  `adda`, the map exists and maps something, and `ADDA_SKIP` is not set.
- **Three states: `ok`, `fail`, `n/a`.** What the checker cannot determine is
  said, never passed.
- **Separate command, not a mode of `hook run`.** `hook run` must stay fast and
  commit-scoped (ADR-0007); starting a second interpreter on every commit to prove
  the first one works would be paid on every commit to catch a rare fault.
- **It never repairs.** Each failure names its fix. A tool that silently rewrites
  your hooks is a second thing to trust.

## Consequences

- A new clone, a recreated venv or a husky-style repo can be proved in one
  command, and the command can run in CI or a setup script.
- It does not make the hook itself fail closed; that trade from ADR-0007 stands.
- BUG-ADDA-027 is detected by `doctor` but not fixed by it: `hook install` still
  needs to write where git reads.
