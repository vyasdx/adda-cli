<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0009 — Source discovery keeps its heuristic, but reports every root it drops

Date: 2026-08-26
Status: accepted
Issue: DEC-ADDA-009 (gates BUG-ADDA-018, BUG-ADDA-019, BUG-ADDA-020)

## Context

`audit` can only report drift in code that `sync` mapped. Anything discovery
never sees is not "clean" — it is unexamined, and reported as clean. Three
filed bugs were all that failure:

- a flat repo (`main.py`, `utils.py` at the root) mapped **nothing**, and
  `audit` printed "No doc drift" over a project with zero docs (BUG-ADDA-018)
- `src/loose.py` was invisible beside `src/pkg/` (BUG-ADDA-019)
- one `__init__.py` anywhere dropped every other Python root repo-wide, so
  `toolscripts/` vanished because `pkgmod/` existed (BUG-ADDA-020)

The first two are not judgement calls that went wrong. `discover_modules` walks
directories, so a file that is not inside one was never a case the code handled.
Those are plain defects.

The third is a real heuristic: *a Python directory with no `__init__.py` is
examples, not a package.* It exists because fastapi's `docs_src/` is 369
tutorial snippets, and mapping them buries every real finding.

The tempting fix — map everything and require explicit exemption — matches this
project's own stated rule that exemption must be deliberate and written down.
It was rejected: a report nobody can stand to read gets ignored, and an ignored
report is a silent pass wearing a different hat.

The opposite fix — guess better — is what produced this. On 2026-08-24 a false
positive was fixed with a heuristic, and that heuristic created three false
negatives.

## Decision

Fix the two defects, keep the heuristic, and make the heuristic **audible**.

1. Loose source files at the base directory are mapped. They can never carry an
   `__init__.py`, so they are exempt from the package test — otherwise fixing
   BUG-018/019 would re-hide the same files on any repo containing a package.
2. `source_roots` returns `(files, excluded)`. `audit` prints every excluded
   root and the reason, under `[skipped]` — not as a finding, because nothing
   is drifting, but never as silence.
3. `"include"` in `MODULE_MAP.json` overrules the guess for a named root, and
   round-trips through `sync --map` so regeneration cannot quietly undo it.

This is the same three-state shape the staleness check already uses:
`stale` / `current` / **cannot tell**. A rule that cannot decide has to say so.

## Consequences

- A wrong guess now costs a printed line instead of an unenforced directory.
- Mapping loose root files exposed the repo root, which on JS projects is full
  of `.eslintrc.js` and `rollup.config.js`. Dotfiles and `*.config.*` are not
  documentable behaviour and are filtered; `setup.py` and `conftest.py` are
  listed as `exempt`, which is visible, rather than dropped.
- fastapi still reports 41 mapped files rather than 410, and now says out loud
  that it skipped `docs_src/`.
- The limit is unchanged and worth stating: discovery reports what it *chose*
  to skip. It cannot report a root it never reached.
