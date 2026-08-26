<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `evaluate` - `src/adda/evaluate.py`

Last verified: 2026-08-26

**Purpose** - Rehydration fidelity % - turns `rehydrate` from a vibe into a metric.

## Public surface

`evaluate(okf) -> dict` carrying `overall_fidelity_pct`, `load_bearing_fidelity_pct`, `facts_preserved`, `facts_total`, `payload_reduction_pct`, `minimal_chars`, `full_chars`, `dropped`

## The two numbers

- **`overall_fidelity_pct`** - share of ALL facts retained. Expected below 100%: dropping prose and inactive items is the intended trade-off.
- **`load_bearing_fidelity_pct`** - share of constraints, active modules, in-force ADRs, and project/version retained. **MUST be 100%.** A regression here is a real bug.

## Invariants

- **A scaffold nobody has written into is not scored.** `evaluate(okf, adda_dir)` compares each fact-bearing file against the shipped template; when all of them are still the template, both percentages are `None` rather than a number computed from placeholder text (BUG-ADDA-021). Partly-authored memory IS scored, with the still-unwritten files named. Same three-state shape as the staleness check.
- **Deterministic and offline. No LLM call, ever** (ADR-0003, locked scope guard). That is what makes the number reproducible and keeps ADDA in its lane.
- Baseline facts come from the full OKF, survivors from `rehydrate.minimal_okf` - so `eval` measures the real function rather than a copy of its rules.

## Current dogfood figure

`adda eval D:\ADDA` gives **84.0% overall / 100% load-bearing** (2026-08-18). It was 77.8% before ENH-ADDA-002.

## Change Log (newest first)

- [2026-08-26] BUG-ADDA-021 - `evaluate` gained an optional `adda_dir` and returns `None` percentages plus `unauthored_template_files` · `adda eval` on a fresh `adda init` reported a confident "58.3% overall, 100.0% load-bearing" computed entirely from template placeholders, and that figure is where the README's long-standing stale 58% came from. It measured the template, not the tool.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
