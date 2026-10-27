<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0026 — REVIEW.md is an instruction file

Date: 2026-10-27
Status: accepted
Issue: ENH-ADDA-048
Amends: ADR-0014

## Context

Claude Code Review reads `REVIEW.md` as its review instructions: what counts as
Important, paths to skip, a cap on nits, checks to always run. A path in it that
no longer exists is a skip rule or a check that silently stopped applying, the
same broken instruction ADR-0012 exists to catch. ADDA wrote its own `REVIEW.md`
(ENH-ADDA-047), and `audit --refs` did not read it.

The question asked was whether ADDA should generate a product's `REVIEW.md` or
check it. What failure looks like in a repository is the owner's judgement, and
writing it would take a model (ADR-0003). Checking that what it cites exists is
mechanical, which is ADDA's ground.

## Decision

`REVIEW.md` joins the files read in any directory. Its documentation, read on
2026-10-27 (code.claude.com/docs/en/code-review-customize), puts it at the root
and lets a subdirectory add its own for changes under that path.

Everything ADR-0012 and ADR-0014 say about instruction files applies unchanged:
paths and names checked for existence, unresolved spans counted and never
flagged, gitignored files left out, and a file that only names `REVIEW.md` as a
convention is not claiming one exists.

## Consequences

- ADDA's own run reads its `REVIEW.md` with the other instruction files.
- The same documentation says the local `/code-review` command reads `CLAUDE.md`
  and not `REVIEW.md`; only the hosted service reads it. The check is still worth
  having, since the file is a published instruction either way, but a repository
  that reviews only locally gets its rules applied by pointing to the file.
- `@file` include lines inside `REVIEW.md` are not followed. An included file
  sits beside it at the root, where it is a plain markdown file ADDA does not read
  as instructions; add it under `instructions` in the map if it should be checked.
