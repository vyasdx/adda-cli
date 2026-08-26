<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `audit` - `src/adda/audit.py`

Last verified: 2026-08-26

**Purpose** - Doc-layer drift detection - the check `adda diff` structurally cannot perform. `diff` only confirms documented module *paths* still exist; it never opens a doc or checks whether it is current. `audit` uses `MODULE_MAP.json` as the code->doc routing table and catches drift `diff` is blind to: missing docs, stale docs, unmapped source, orphaned docs, and stale map entries.

## Public surface

`audit_report(repo, adda_dir) -> (findings, skipped)` · `last_commit_sha(repo, path)` · `compare_commits(repo, doc_sha, code_sha) -> "stale" | "current" | "unknown"` · `_is_ancestor(repo, older, newer) -> True | False | None` · `_git_rc(repo, args) -> int`

Findings are `{"item": str, "issue": str, "severity": str}`. Five issues: `doc missing` (high), `doc stale` (medium), `code unmapped` (medium), `doc orphaned` (low), `map entry stale` (low).

## Invariants

- **Deterministic and offline - no model calls (ADR-0003).** `audit` is a locked scope guard, same as every other ADDA command.
- **Exits 1 on any finding, matching `diff`'s contract**, so `adda audit` drops into CI/pre-commit unchanged.
- **A rule that cannot run is reported as skipped, never silently passed.** Staleness needs git history on both sides; when either side's SHA is unavailable (not a git repo, git missing, file untracked) that doc is recorded in `skipped`, never treated as clean. A check that fails quietly is worse than no check.
- **Rule 3 (`code unmapped`) exists so a new file cannot escape enforcement.** Without it, a source file simply never added to the map would never be checked by anything.
- **Source discovery is imported from `sync.source_roots`, never reimplemented here**, so the auditor and the map generator apply the identical definition of "what is source" - a file `module_map_json` refuses to map can never show up here as a false-positive `code unmapped`.
- **Staleness uses commit ancestry (`compare_commits` via `git merge-base --is-ancestor`), not timestamps.** `%ct` has 1-second resolution, so two commits landing in the same second tie and a genuinely stale doc reads as clean - a silent pass. Ancestry has no such gap.
- **Staleness is three-state, not a boolean.** `compare_commits` returns `"stale"` only when the doc's commit is a strict ancestor of the code's commit; identical SHAs mean doc and code were committed together, so that's `"current"`; anything undecidable - divergent branches, a rebase, a cherry-pick, or a git failure - is `"unknown"` and routes to `skipped`, never assumed current. A boolean would force "cannot tell" to masquerade as "not stale", which is a silent pass.
- **Known limitation: shallow clones can misreport `unknown` as `current`.** `git merge-base --is-ancestor` exits 1 both for "genuinely not an ancestor" and for "ran out of history to walk" - git gives no distinct exit code for the shallow-history case. A staleness check against a shallow clone can therefore read `current` without being skipped. Run `audit` against full history. **In CI this is a configuration requirement, not a caveat:** `actions/checkout` clones shallow by default, so the workflow sets `fetch-depth: 0`. Without it every staleness result here is an undetermined skip.
- `load_map` (from `modulemap.py`) raises `FileNotFoundError` when `MODULE_MAP.json` is absent; the CLI surfaces that message (which names `adda sync --map`) rather than treating an unmapped repo as clean.

## Change Log (newest first)

- [2026-08-26] DEC-ADDA-009 - `audit` now prints every source root discovery chose to skip, under `[skipped]` · `audit` can only report drift in code `sync` mapped, so an unreached root was being reported as clean rather than as unexamined. Not a finding (nothing is drifting), never silence.
- [2026-08-26] RF-ADDA-005 - corrected an invariant that still named `_source_files`, deleted earlier the same day - the file contradicted its own Change Log two sections below. Caught by review, not by `audit`: both docs were committed alongside the code, so git ancestry called them current. Ancestry sees an untouched doc, never a wrongly-updated one (DEC-ADDA-010).
- [2026-08-26] BUG-ADDA-013 — `_source_files` deleted; discovery now imported from `sync` · it globbed `*.py` while the map covered ts/js, so a TypeScript file added after the map was written was invisible to the unmapped-code rule and escaped enforcement entirely.
- [2026-08-26] ENH-ADDA-011 — recorded that CI must check out with `fetch-depth: 0` · the documented shallow-clone limitation stops being theoretical the moment `audit` runs on a runner, where shallow is the default.
- [2026-08-18] ENH-ADDA-007 — doc corrected: staleness is `compare_commits` (three-state ancestry), not the removed `is_strictly_later` · the doc had drifted from the code within the same day, which is the exact defect this module detects.
- [2026-08-18] ENH-ADDA-007 — module created · v0.3 enforcement layer: the doc-drift check `adda diff` structurally cannot perform.
