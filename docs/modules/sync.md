<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `sync` - `src/adda/sync.py`

Last verified: 2026-08-18

**Purpose** - Derive an ADDA architecture *skeleton* from a codebase, so the docs can be refreshed instead of rotting.

## Public surface

`discover_modules(repo) -> [(name, posix path)]` · `discover_deps(repo)` · `skeleton_markdown(repo)` · `module_map_json(repo, doc_dir)`

## Invariants

- **Skeleton generator, not a doc writer.** Output is markdown the user reconciles into `ARCHITECTURE.md` by hand; it never overwrites `/adda`.
- **`discover_modules` is shared with `adda diff`.** It is the single definition of "what counts as a module", so changing it changes drift detection - re-run `adda diff D:\ADDA` after touching it. BUG-ADDA-003 came from exactly this function miscounting dirs whose only files sat in ignored subtrees.
- Prefers a `src/` layout when present; a directory counts only if it contains files.
- A root-level `adda/` is the scaffolded *data* dir and is skipped - but `src/adda` (the package) is kept.
- Dependencies are read from `pyproject.toml` or `package.json`.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-007 — MODULE_MAP generation uses a map-local `MAP_IGNORE_DIRS`; the shared `IGNORE_DIRS` is deliberately left untouched · widening it would drop a real `templates/` source package from `adda diff` in every repo.
- [2026-08-18] ENH-ADDA-007 — `sync` gained `module_map_json` / `--map`, deriving code→doc routing from `discover_modules` · one definition of "what is source" across sync, diff and audit.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
