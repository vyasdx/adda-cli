<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0012 — Instruction files are checked, not mapped

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-024
Extends: ADR-0011

## Context

`AGENTS.md`, `CLAUDE.md` and their siblings are the files a coding agent reads
before any code. More and more, they are the program: the build steps, the
module list and the rules an agent follows are written there in English. A dead
reference in one is a broken instruction, not a typo.

ADDA did not look at them. `audit` covers mapped module docs, and ADR-0011's name
check covered those same docs. The open question was whether an instruction file
is just another mapped doc. It is not. A module doc describes one code path, so
"was it left behind?" has an answer. An instruction file describes the whole
repository, so ancestry against "all the code" would read it stale after every
commit — a rule that is always red teaches people to ignore it.

A prototype checked every backticked path in ADDA's own `AGENTS.md`, `CLAUDE.md`
and `README.md` for existence. It flagged 30. Every one was a false positive of
the naive check, in seven shapes: paths into another repository, globs,
placeholders like `<today>`, brace lists, a leading `/` meaning the repo root,
bare filenames relative to some other directory, slash commands and `n/a`, and a
retired file named precisely to say it was gone.

## Decision

Instruction files get their own rule under `audit --refs`: every code name and
every repository path they cite must exist. They are not added to the map.

- **Which files: the conventional ones, with no configuration.** `AGENTS.md`,
  `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `README.md`, when
  present at the root. A config key in `MODULE_MAP.json` would be silently dropped
  the next time `sync --map` regenerates the map — the kind of quiet loss this
  tool exists to prevent.
- **A path is checked only when its first segment exists in this repository.**
  Anything else is `unresolved`: counted and printed, never flagged. The rule
  cannot tell another repository from a file named relative to somewhere else,
  and a false alarm costs more than a miss.
- **Brace lists are expanded** and each member checked; a leading `/` means the
  repository root; globs and placeholders are patterns, not paths.
- **A line that names something to say it is gone is skipped**, for names and
  paths, in module docs too — the one-line form of a Change Log.
- **Citing a conventional instruction filename is not a claim it exists.** Docs
  about AI tooling list `AGENTS.md`, `.github/copilot-instructions.md` and the rest
  generically. Found by dogfooding: ADDA's own README tripped the rule on its first
  run, because `.github/` exists for workflows while the Copilot file does not.
  Such a name, when absent, is counted as unresolved. The broader pattern — a
  file named "if present" — is deliberately not handled with qualifier words, since
  markdown wraps lines arbitrarily and a result that changes when a paragraph is
  reflowed is not deterministic.
- **Gitignored paths are excused.** A generated file exists on a working machine
  and not on a clean checkout, so it is neither present nor missing.
- **Existence is matched with exact case.** A case-insensitive disk would pass a
  path that fails on a case-sensitive CI runner; exact matching gives both the
  same answer.
- **Still opt-in, and not yet in ADDA's own CI.** An instruction file can contain
  text synced from outside the repository, which the repository cannot fix. A CI
  gate that fails on text nobody here can change is how a gate gets bypassed.
  Whether and how to enforce it is a separate decision.

## Consequences

- ADDA's own instruction files pass: 51 paths and 2 names checked, 24 spans
  unresolved and reported, 0 findings. The published repository's layout passes
  too.
- The limit from ADR-0011 carries over and showed itself on the change that
  introduced this rule. `CLAUDE.md` lists ADDA's modules in a brace list; adding
  `refs.py` left the list incomplete, and the check passed — it verifies what a
  file cites, and cannot see what it omits. The list was corrected by hand.
- Every exclusion above is pinned by a test, and each test was shown to fail when
  its exclusion is removed. One exclusion was deleted as dead code after that
  exercise showed it could never fire.
