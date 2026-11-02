<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0029 — Names and paths are looked up the way real repositories write them

Date: 2026-11-02
Status: accepted
Issue: BUG-ADDA-041, BUG-ADDA-042
Amends: ADR-0012, ADR-0022 (the "only `.github`" rule from BUG-ADDA-033)

## Context

Round 3 of the case study (ENH-ADDA-056) ran `--refs` on 28 public repositories from AI labs,
AI-native tool companies, enterprise and services firms, Indian product companies and individual
practitioners. 274 findings were checked by hand: 85 real, 189 false. 108 of the false ones came
from eight mechanical causes in how ADDA looked things up, not from hard prose.

## Decision

The names corpus (BUG-ADDA-041):

- **Skips only dependency, environment and cache trees** (`node_modules`, `.venv`, `site-packages`,
  `dist`, tool caches). `docs`, `doc`, `build` and dot-folders are read: they hold real code
  (`apps/docs/next.config.ts`, Go's `internal/build`, `.storybook/preview.tsx`). Build output and
  caches are gitignored, and ADR-0024 already drops what git ignores. This replaces "of the
  dot-folders only `.github`".
- **A file's name is a name.** A command or a test is cited by its file (`reingest_signal_report`).

Backticked paths in instruction files (BUG-ADDA-042):

- **`{model}` is a placeholder**, so `src/models/{model}.py` is a pattern; `{a,b}` still expands.
- **An extensionless path matches a source file or package index** of that name (`lib/api` is
  `lib/api.ts`), the way imports name modules. Markdown links stay exact (ADR-0020).
- **A nested file's path, once checked, may be found from any folder between it and the root**:
  a sub-project's file cites paths from its package root. Whether a path is checked at all still
  depends only on the root and the file's own folder.
- **A path inside a git submodule is unresolved**, never missing: it is another repository's tree.

## Consequences

- Each rule has a test built from a round-3 line, and each test fails on the code before it.
- Anchoring from the ancestor folders too was tried first and added 86 false findings on round 3:
  npm subpath imports (`agents/client`) became "paths" because `packages/agents` exists. What gets
  checked and where it may be found are separate questions. With that split, searching more and
  resolving more only turns a flag into a pass. Round 3: 274 findings (85 real) to 178 (84 real),
  no new ones. The cost: a moved file that still exists under an ancestor folder, or a name that survives only as
  a file name, no longer flags.
- Not done, with a known ceiling: names from other tools and services (38 of the remaining false
  findings: MCP tool names, Angular APIs, Kubernetes keys) cannot be told apart from a deleted
  name without knowing every external API; Windows checkouts of git symlinks (3).
