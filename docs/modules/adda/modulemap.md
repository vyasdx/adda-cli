<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `modulemap` - `src/adda/modulemap.py`

Last verified: 2026-08-26

**Purpose** - `MODULE_MAP.json` load/query - the code->doc routing table `adda audit` walks. Maps each source file to the doc that must change with it.

## Public surface

`MAP_FILENAME = "MODULE_MAP.json"` · `load_map(adda_dir) -> ({code_path: doc_path}, exempt_globs)` · `is_exempt(path, exempt) -> bool` · `load_include(adda_dir) -> list[str]`

## Invariants

- **Explicit mapping over globs.** A hand-editable, greppable, diffable `{code: doc}` dict is reviewable in a way a glob-matching rule set is not; `adda sync --map` generates it, so there is no hand-maintenance burden in practice.
- **`load_map` raises `FileNotFoundError` rather than returning empty when `MODULE_MAP.json` is missing.** An empty map would make every repo look "clean" to `adda audit` - the loudest possible failure (an exception the CLI must catch and explain) is the correct one for a missing map.
- **`is_exempt` uses `fnmatchcase`, not `fnmatch`**, so a pattern match cannot vary by platform (case-insensitive on Windows, case-sensitive elsewhere would otherwise split behavior).
- **Exempt entries are deliberate and written down** in `MODULE_MAP.json`'s `exempt` list - a file is only skipped by `code unmapped` because someone chose to exempt it, not by accident of a generator's exclusion list.
- **`load_include` returns `[]` for a missing map rather than raising**, unlike `load_map`. The loud failure for an absent map is owned in one place; duplicating it would make every caller handle the same error twice.
- **`include` is the written-down override for a guess, mirroring `exempt`.** `exempt` excuses a file from enforcement; `include` drags a whole root back under it when discovery's package heuristic wrongly dropped it (ADR-0009).
- Paths are normalised (`_norm`: backslash to forward slash, stripped) on load, so map entries compare correctly on Windows.

## Change Log (newest first)

- [2026-08-26] DEC-ADDA-009 / BUG-ADDA-020 - added `load_include` · one `__init__.py` anywhere dropped every other Python root repo-wide, and the user had no way to say otherwise. `include` in `MODULE_MAP.json` overrules discovery per root and round-trips through `sync --map`, so regenerating cannot quietly undo it.
- [2026-08-18] ENH-ADDA-007 — module created · v0.3 enforcement layer: the doc-drift check `adda diff` structurally cannot perform.
