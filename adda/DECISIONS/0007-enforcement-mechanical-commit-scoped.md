<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0007: Enforcement is mechanical and commit-scoped

id: ADR-0007
status: accepted

## Context
`adda diff` reported "No drift: documented modules match the repo" for two months
over an empty `docs/modules/` (2026-08-18) — it checks that documented module PATHS
still exist, never opens the docs, and ignores `docs/` entirely. A rule that cannot
run must never be silently reported as passing; that was the exact failure mode.
v0.3 adds a real doc-layer gate (`modulemap`, `audit`, `hook`) and this ADR records
the shape it had to take.

## Decision
- **Enforcement is mechanical, not remembered.** `hook run` compares staged code
  paths against staged doc paths (git's index vs itself) via `MODULE_MAP.json`. No
  dates, no LLM judgment, nothing that requires a human or a model to recall or
  attest to anything — so there is nothing to forge and nothing to forget.
- **The hook is commit-scoped.** `hook run` only ever inspects what is staged for
  *this* commit; it never runs `audit` or `diff` against the whole repo.
  Repo-wide drift checking belongs to `audit`. A gate that blocks an unrelated
  commit over pre-existing drift it didn't cause is how a team learns to reach
  for `--no-verify` permanently, which enforces nothing ever again.
- **`audit` is deterministic and offline**, extending ADR-0003's guardrail (no
  model calls) from `eval` to the doc-drift sweep: five rules (doc missing, map
  entry stale, code unmapped, doc orphaned, doc stale) computed from the
  filesystem and `git log`/`git merge-base`, reproducible by anyone with the repo.
- **A rule that cannot run is reported, never silently passed.** `audit`'s
  staleness check needs git history on both the code and the doc side; when
  either side's history is unavailable or unordered (shallow clone, divergent
  branches, rebase) the result is recorded in `skipped` and printed, not folded
  into "no drift". `compare_commits` returns a three-state result
  (`stale`/`current`/`unknown`) precisely so "cannot tell" can never masquerade
  as "fine" — that masquerade is what let `docs/modules/` sit empty for two
  months while `adda diff` stayed green.

## Consequences
A commit that adds or changes code without its doc is blocked at commit time,
locally, before it ever reaches CI. Pre-existing repo-wide drift is surfaced by
`audit` (and can gate CI separately) instead of blocking whichever commit happens
to run next. Both checks stay reproducible and free — no network, no model call —
so they can run in a pre-commit hook without cost or nondeterminism.
