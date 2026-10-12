<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0025 — Any fleet map shape imports

Date: 2026-10-12
Status: accepted
Issue: ENH-ADDA-046
Amends: ADR-0023

## Context

ADR-0023 imported a product's existing map in one shape, `{"mappings": [{"path", "doc"}]}`, the shape
the first three fleet products used. The second wave showed that this was one shape among several. A
read-only dry run on four more products found that every one keeps a hand map, each in its own schema:

- `modules[{doc, owns: [wildcards]}]` plus an `ignored` list;
- `modules[{doc, covers: [paths]}]` plus `ignored.files_outside_adda`;
- `modules[{file, doc}]`;
- `repos{name: {root, modules[{code, doc}]}}`, a single map covering two repositories.

0.5.3 refused all four, loudly. Without them, these products would have started from ADDA's guess,
with 54, 43, 21 and 1 files at an existing doc. One product's code lives in `scripts/`, which `sync`
does not map by design, so ADDA saw almost none of it.

## Decision

- **Read the shared idea, not each schema.** Any object, at any depth, that names a `doc` and the code
  it covers (`path`, `file`, `code`, `owns` or `covers`; a string or a list) is an entry. ADDA's own
  `{"map": {...}}` is still read as before. A map holding no entry at all is refused.
- **An exact path is that file**, whatever kind it is, if it exists and is not prose. This holds even
  when the path contains `[` or `*`: Next.js routes live in folders named `[id]`.
- **A folder or a wildcard covers the text files git sees under it.** That means tracked or untracked
  but not ignored, minus prose and binaries. A schema or stylesheet the product claimed comes in; its
  images do not. (ADR-0023 expanded folders to source files only, which dropped claimed schemas and
  scripts.) An exact entry beats a folder or wildcard.
- **A section whose `root` is another checkout is not this repository's.** It is skipped with one
  note giving its count.
- **A map's `ignored` or `exempt` lists become exemptions.**
- Every entry left out is still named with its reason.

## Consequences

- On the four wave-2 products, files at an existing doc went 54 -> 96, 43 -> 80, 1 -> 25 and
  21 -> 76. The product whose code is in `scripts/` is covered through its own map, because imported
  entries are kept for any file (BUG-ADDA-031).
- On the three wave-1 products the import still works: 37, 116 (was 111) and 100 (was 79). Folders
  now bring in the scripts and schemas under them.
- Mapping more docs puts more of them under `--refs`: one product's count rose from 2 to 22, and all
  22 are names its docs cite that its code no longer defines.
