<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `okf` - `src/adda/okf.py`

Last verified: 2026-08-18

**Purpose** - The OKF (Open Knowledge Format) pydantic schema, plus the `/adda` markdown to OKF compiler.

## Public surface

`OKF`, `Architecture`, `Module`, `Decision`, `State` (models) · `compile_okf(adda_dir)` · `active_modules(okf)` · `active_decisions(okf)`

## Invariants

- **Schema is LOCKED at v0.2** (`OKF_VERSION = "0.2"`, spec in `OKF_SCHEMA.md`). Adding a field is a schema change and needs an ADR, not a quiet edit.
- **Provider-agnostic.** No Claude/Codex/Copilot-specific fields, ever - the same JSON must feed any LLM.
- **`ACTIVE_DECISION_STATUSES = {"accepted", "active"}` is the single definition of "in force".** `rehydrate` and `evaluate` both read it; do not re-derive the rule locally.
- `Module.path` is what makes a module checkable by `sync` / `diff`. Path-less modules are documented but undiffable.

## Used by

`cli` (export) · `rehydrate` · `diff` · `evaluate`. This is the schema hub - a change here ripples to all four.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
