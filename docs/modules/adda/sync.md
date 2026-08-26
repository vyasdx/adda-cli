<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `sync` - `src/adda/sync.py`

Last verified: 2026-08-26

**Purpose** - Derive an ADDA architecture *skeleton* from a codebase, so the docs can be refreshed instead of rotting.

## Public surface

`source_files(repo) -> list[str]` (**the shared definition of documentable source, used by `audit` too**) · `discover_modules(repo) -> [(name, posix path)]` · `discover_deps(repo)` · `skeleton_markdown(repo)` · `module_map_json(repo, doc_dir)`

## Invariants

- **Skeleton generator, not a doc writer.** Output is markdown the user reconciles into `ARCHITECTURE.md` by hand; it never overwrites `/adda`.
- **`discover_modules` is shared with `adda diff`.** It is the single definition of "what counts as a module", so changing it changes drift detection - re-run `adda diff D:\ADDA` after touching it. BUG-ADDA-003 came from exactly this function miscounting dirs whose only files sat in ignored subtrees.
- Prefers a `src/` layout when present; a directory counts only if it contains files.
- A root-level `adda/` is the scaffolded *data* dir and is skipped - but `src/adda` (the package) is kept.
- Dependencies are read from `pyproject.toml` or `package.json`.

## Change Log (newest first)

- [2026-08-26] RF-ADDA-005 - added `source_files` to the Public surface, which this file's own Change Log had described as the new shared entry point while the surface list still omitted it.
- [2026-08-26] BUG-ADDA-013/014 — source discovery extracted into a shared `source_files()` used by BOTH the map generator and `audit`, and the package test narrowed to roots that CONTAIN Python · the two had diverged so a new `.ts` file escaped enforcement, and an `all-Python` test was defeated by two stray `.js` files in fastapi's docs_src.
- [2026-08-26] ENH-ADDA-016 — the map generator now covers `.ts/.tsx/.js/.jsx/.mjs/.cjs` as well as `.py`, and excludes `.d.ts`, `.min.js`, `.test.`/`.spec.` files, bare `test.ts`-style stems, and vendored directories · `discover_deps` already read `package.json` while enforcement stopped at Python. Validated on date-fns (1,259 files, 0 collisions) and django, where 62 vendored jQuery/select2 files had been demanding module docs.
- [2026-08-26] ENH-ADDA-017 — `module_map_json` now prefers real Python packages (a dir with `__init__.py`) when the repo has any, falling back to all discovered dirs when it has none · running against fastapi mapped 410 files, 369 of them tutorial snippets under `docs_src/`. Scoped to the generator; `discover_modules` (shared with `adda diff`) is untouched.
- [2026-08-26] BUG-ADDA-011 — `module_map_json` now MIRRORS the source path (`src/payments/utils.py` -> `docs/modules/payments/utils.md`) instead of using the filename stem · stem-only routing sent two same-named files in different packages to ONE doc, so `audit` reported "no doc drift" over a module that had none. Mirroring makes collision impossible by construction.
- [2026-08-18] ENH-ADDA-007 — MODULE_MAP generation uses a map-local `MAP_IGNORE_DIRS`; the shared `IGNORE_DIRS` is deliberately left untouched · widening it would drop a real `templates/` source package from `adda diff` in every repo.
- [2026-08-18] ENH-ADDA-007 — `sync` gained `module_map_json` / `--map`, deriving code→doc routing from `discover_modules` · one definition of "what is source" across sync, diff and audit.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
