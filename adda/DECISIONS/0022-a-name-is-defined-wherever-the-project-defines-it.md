<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0022 — A name is defined wherever the project defines it

Date: 2026-10-12
Status: accepted
Issue: BUG-ADDA-030
Amends: ADR-0011

## Context

ADR-0011 made `--refs` check that every code name a doc cites still exists "somewhere in the
source", and took source to mean `sync.SOURCE_SUFFIXES`: Python and JavaScript/TypeScript files.
That held on ADDA, whose names all live in Python.

The first run on fleet products did not hold. A read-only dry run on copies of three of them
(HireGEN, BloomAI, discipline-m) produced 60 `--refs` findings, and 51 of them (85%) were false:

- **Names defined outside source code.** BloomAI's docs cite its row-level-security policies,
  defined in SQL migrations (23). discipline-m's cite its Prisma models and the environment
  variables its shell and PowerShell scripts read (20). A workflow defined one more.
- **Paths into `.git/`.** Fleet `CLAUDE.md` files name their installed hooks,
  `.git/hooks/pre-push`. The path's first segment exists, so it was checked, and no checkout's
  tree contains it (6).

ADR-0011's own principle decides this: a checker that cries wolf teaches people to stop reading
it. At 85% false, a rollout would have taught exactly that on day one.

## Decision

- **The names corpus is every text file outside the docs, except prose.** SQL, Prisma, shell,
  PowerShell, YAML, workflow and config files define names as surely as code does. Prose
  (`.md`, `.mdx`, `.markdown`, `.rst`, `.txt`, `.adoc`) is excluded, because a doc citing a name
  must not be vouched for by another doc repeating it. Directories already skipped stay skipped,
  as do files over 1 MB: a vendored bundle or a dump is not a definition.
- **"Is there code at all" still means source code.** A repository with only config and no
  source is skipped, not passed, as before.
- **A path whose first segment is `.git` is unresolved, never missing.** Git's own directory is
  local machine state, not part of the tree, so the rule cannot decide it.

## Consequences

- On the three copies: 60 findings fell to 9, and all 9 are real (BloomAI's docs cite five names
  no code defines, discipline-m's one). ADDA's own repository stays clean, and fastapi's two
  README errors are still found.
- Searching more files can only turn a flag into a pass, which ADR-0011 already named as this
  rule's safe direction. The cost is a name that exists only in config now passes; that is a
  definition, so it should.
