<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `rehydrate` - `src/adda/rehydrate.py`

Last verified: 2026-08-18

**Purpose** - The north-star: build the MINIMAL OKF that restores an LLM's architecture memory after a context compaction.

## Public surface

`minimal_okf(okf) -> dict`

## What survives, and what is dropped on purpose

Kept: `okf_version`, `project`, `version`, `constraints`, **active** modules, **in-force** decisions.

Dropped: overview, domain model, API contracts, state, and every planned / deprecated / superseded item.

## Invariants

- **The dropped set is a deliberate compression trade-off, not an omission.** That is exactly why `adda eval` reports two numbers: overall fidelity is expected to sit below 100%, load-bearing fidelity must be 100%.
- **Load-bearing content must never be dropped.** If a future change loses a constraint, an active module, or an in-force ADR, `eval`'s load-bearing number falls below 100% - that is a real bug, not a tuning knob.
- Active / in-force filtering is delegated to `okf.active_modules` and `okf.active_decisions`. Keep it that way so `evaluate` and `rehydrate` cannot disagree.

## Smallest file in the package, and the most important

24 lines. Every other command exists to feed or to measure this one.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
