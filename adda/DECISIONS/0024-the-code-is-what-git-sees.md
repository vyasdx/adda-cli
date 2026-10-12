<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0024 — The code is what git sees, not what the disk holds

Date: 2026-10-12
Status: accepted
Issue: BUG-ADDA-032
Amends: ADR-0022

## Context

`sync.source_roots` decided what counts as code by walking the file system, and ADR-0022's names
corpus walked it too. Neither asked git. On a fresh clone the two agree. On a working tree they do
not: a developer's machine carries git-ignored build output, local experiments, and whole nested
repositories that no clone has.

The first fleet product to roll ADDA out found this on its own machine. Its working tree held a
git-ignored nested repository beside the app, and the first `audit` reported five `doc missing`
for that repository's files. ADDA's own verification had run on fresh clones, so it could not see
the problem. The same blind spot ran the other way in the names corpus: a name defined only in an
ignored file vouched for a doc citing it, so a name the repository does not define could pass.

## Decision

- **A file git ignores is not code.** Both `source_roots` and the names corpus drop what
  `git check-ignore` reports, in one batched call (`sync.git_ignored`, which `refs` now shares for
  its path checks).
- **A nested repository is not this repository's code**, ignored or not. A directory below the root
  that holds its own `.git` is skipped (`sync.in_nested_repo`).
- **Outside git nothing changes.** With no repository to ask, nothing is treated as ignored, as
  before.

## Consequences

- A working tree and a fresh clone of the same commit now map the same files. On the product's real
  working tree, 0.5.2 counted 40 source files, 6 of them inside the nested repository; with this
  change it counts the 34 that are its own.
- Exempting a nested repository by hand, the workaround during wave 1, is no longer needed. It is
  harmless where it already exists.
