<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `compress` - `src/adda/compress.py`

Last verified: 2026-08-18

**Purpose** - Optional headroom-ai wrapper. Best-effort, never load-bearing.

## Public surface

`available() -> bool` · `compress_text(text, model=None) -> (text_out, info)`

## Invariants

- **headroom-ai is NOT a dependency.** Absent, broken, or throwing - `compress_text` returns the input unchanged with `info["applied"] = False`. Compression must never break the caller.
- **Compression is LOSSY** (headroom's SmartCrusher drops low-signal JSON items), so it is wired behind an opt-in `--compress` flag only. **Default `export` / `rehydrate` output stays faithful, valid OKF** (ADR-0004, locked scope guard).
- The upgrade path, if a guaranteed-reversible payload is ever needed, is headroom's CCR mode.

## Used by

`cli._maybe_compress` only, which reports either the saving or the reason compression was skipped.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
