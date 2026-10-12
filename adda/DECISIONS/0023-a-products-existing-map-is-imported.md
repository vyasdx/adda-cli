<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0023 — A product's existing map is imported, not re-guessed

Date: 2026-10-12
Status: accepted
Issue: ENH-ADDA-044
Extends: ADR-0019, ADR-0021

## Context

ADR-0019 keeps a product's choices once they are in ADDA's map, and ADR-0021 guesses a doc for code
the map has never seen. Both assume the choices start in ADDA's map. On the fleet they do not.
Three products (a hiring app, a school-analytics app and a trading app) have kept code-to-doc maps by hand since June, in
their own format, `{"mappings": [{"path", "doc"}]}` in `docs/MODULE_MAP.json`, and the trading app maps
whole folders (`src/app/api/auth/`). ADDA could read none of it, so a rollout would have started from
ADDA's guess. On those three products the guess put 22, 76 and 61 files at an existing doc, where the
products' own maps already had more, and it disagreed with the product on 12, 14 and 7 files.

The maps also hold things that are not code: `CLAUDE.md`, READMEs, and the operations trackers an
automated assistant rewrites daily (`status.md`), which would read any doc mapped to them as stale every day.

## Decision

`adda sync --map --from <file>` seeds the map from a product's existing one, once.

- **Both formats are read**: the fleet's `mappings` list and ADDA's own `map` object. Anything else
  stops with an error. An import that quietly did nothing would leave the choices to be redone by
  hand, and nobody would notice.
- **A folder entry stands for the source files under it**, and an entry naming one of those files beats
  the folder.
- **Prose is not imported.** A doc is not code (ADR-0012), and the trackers would make a doc stale
  forever.
- **Every entry left out is named with its reason**: prose, a file that is gone, a folder with no
  source in it, a path outside the repository, or a malformed entry. Nothing is dropped without a word.
- **The map's own entries win over the import**, so running it again cannot undo a later choice. After
  the import, ADR-0019 and ADR-0021 apply as before.

## Consequences

- On the three products, files mapped to an existing doc went 22 -> 37, 76 -> 111 and 61 -> 79.
  The hiring app starts with no findings; the trading app starts with 4 stale docs, its
  database-schema doc among them; the school-analytics app's own map turns out to name 2 files that
  no longer exist.
- `PROSE_SUFFIXES` moves to `sync`, so "what is prose" has one definition for both the names corpus
  (ADR-0022) and the import.
- The import is one-way. `docs/MODULE_MAP.json` stays the product's own file and its own hooks keep
  reading it until the product retires them; ADDA does not write it.
