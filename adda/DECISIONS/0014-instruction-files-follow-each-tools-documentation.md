<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0014 — Instruction files follow each tool's documentation

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-028
Amends: ADR-0012

## Context

ADR-0012 checked five files at the repository root. That missed two things.
Most coding agents have their own rules files — Cursor, Windsurf, Cline, Roo,
Continue, Junie, Amazon Q, path-specific Copilot instructions. And several
tools read `AGENTS.md` or `CLAUDE.md` in subdirectories too, so a
`packages/api/AGENTS.md` is as much an instruction as the root one.

The first list of other tools' files was recalled from memory and filed as
unverified. Before any of it was hardcoded, each tool's official documentation
was read on 2026-09-24. Memory was wrong in places: Windsurf is now Devin
Desktop and reads `.devin/rules/` first; Aider reads no file unless configured;
Cursor's own two pages disagree on whether `.md` files in `.cursor/rules` count.

## Decision

Discovery walks the repository and matches each file against two lists, taken
from the documentation:

- **Read in any directory:** `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`,
  `GEMINI.md`, and the rules folders `.cursor/rules/` (`.mdc`, and `.md` since
  Cursor's docs disagree and checking an unread file costs nothing),
  `.windsurf/rules/`, `.devin/rules/`.
- **Read at the root only:** `README.md`, `AGENT.md`, `.rules`,
  `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`,
  `.claude/CLAUDE.md`, `.claude/rules/`, `.cursorrules`, `.windsurfrules`,
  `.clinerules` (file or folder), `.cline/rules/`, `.roorules`, `.roo/rules/`,
  `.roo/rules-*/`, `.continue/rules/`, `.amazonq/rules/`, and Junie's
  `.junie/AGENTS.md`, `guidelines.md`, `playbook.md` and `rules/`.

Rules for the walk:

- **Names match with exact case.** Before this, the root check used
  `Path.is_file()`, which on Windows read `agents.md` as `AGENTS.md` while Linux
  read nothing — the same repository gave two answers. A test pinned it.
- **Dependency, build and cache folders are skipped**; `docs/` and `tests/` are
  not, since tools read an `AGENTS.md` there like anywhere else.
- **Gitignored instruction files are left out.** `CLAUDE.local.md` is meant to be
  gitignored; checking a file that exists on one machine only would make the
  same commit pass on CI and fail locally.
- **A nested file's paths may be anchored at the root or at its own directory.**
  Only Claude Code documents which it is, and only for imports. A path counts as
  present if it exists from either; it is missing only when it anchors in one of
  them and exists in neither.
- **Citing a convention is not a claim it exists.** The generic-name rule from
  ADR-0012 now covers every pattern above, so a README that says "Copilot also
  reads `.github/instructions/*.instructions.md`" is unresolved, not missing.
- **Aider is not listed.** It reads a conventions file only when told to; a
  project that uses one names it under `instructions` (ADR-0013).

## Consequences

- ADDA's own run now also reads `docs/public/CLAUDE.md`, which ADR-0012 never
  saw: 4 files, 61 paths, 0 findings. On the five benchmark repositories it
  found `date-fns/AGENTS.md` and django's `.github/copilot-instructions.md`.
- The lists will age. Tools rename (Windsurf did while this was being written)
  and add folders. They are data, dated, with sources, and cheap to change.
- Sources: cursor.com/docs/context/rules, cursor.com/help/customization/rules,
  docs.devin.ai/desktop/cascade/memories, docs.cline.bot/features/cline-rules,
  aider.chat/docs/usage/conventions.html, docs.github.com (add repository
  instructions), code.claude.com/docs/en/memory,
  learn.chatgpt.com/docs/agent-configuration/agents-md,
  geminicli.com/docs/cli/gemini-md, zed.dev/docs/ai/instructions,
  roocodeinc.github.io/Roo-Code/features/custom-instructions,
  docs.continue.dev/customize/deep-dives/rules,
  junie.jetbrains.com/docs/guidelines-and-memory.html,
  docs.aws.amazon.com/amazonq (context project rules), agents.md.
- Every rule above was shown to matter: removing each one turns a test red.
