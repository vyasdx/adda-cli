<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `diff` - `src/adda/diff.py`

Last verified: 2026-08-18

**Purpose** - Drift DETECTION - the headline differentiator. Most context tools only *store* context; almost none detect divergence.

## Public surface

`diff_report(repo, adda_dir) -> [{module, documented, actual, severity}]`

## Severities

| Case | Severity | Means |
|---|---|---|
| documented module's path no longer exists | `high` | docs reference vanished code |
| source dir in the repo, documented by neither path nor name | `medium` | code drifted ahead of docs |

## Invariants

- **Path-less modules are skipped, not flagged.** They are not checkable; `adda sync` is the fix. BUG-ADDA-002 was a false positive from flagging them.
- **Coverage is file-level**: a directory counts as covered when a documented file-path lives under it (ENH-ADDA-002).
- Paths are normalised (backslash to forward slash, then stripped) before comparison - this runs on Windows.
- `cli.diff` turns a non-empty report into exit code 1. Keep the function returning data and the CLI owning the exit code.

## Dogfood gate

`adda diff D:\ADDA` must stay clean. It is the check that proves ADDA's own docs match ADDA's own code.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
