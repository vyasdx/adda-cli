<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Anti-Drift Module Docs

One doc per code path in `src/adda/`. **Read the doc before editing the file; update the doc in the same commit.**

| Doc | Code | What it is |
|---|---|---|
| [cli.md](cli.md) | `src/adda/cli.py` | Typer entrypoint - the eight commands |
| [okf.md](okf.md) | `src/adda/okf.py` | OKF schema (locked v0.2) + markdown compiler |
| [sentinel.md](sentinel.md) | `src/adda/sentinel.py` | Context Sentinel token gauge |
| [rehydrate.md](rehydrate.md) | `src/adda/rehydrate.py` | Minimal OKF - the north-star |
| [compress.md](compress.md) | `src/adda/compress.py` | Optional headroom-ai wrapper |
| [sync.md](sync.md) | `src/adda/sync.py` | Architecture skeleton generator |
| [diff.md](diff.md) | `src/adda/diff.py` | Drift detection |
| [evaluate.md](evaluate.md) | `src/adda/evaluate.py` | Rehydration fidelity metric |

Not documented here: `__init__.py` (version constant only) and `templates/` (seed scaffold data, not code).

## The rule (from `CLAUDE.md`)

Before editing a code path, read its module doc. After editing, **in the same commit**:

1. Bump that doc's `Last verified: YYYY-MM-DD` line.
2. **Append** to its `## Change Log (newest first)`: `- [YYYY-MM-DD] <ISSUE-ID> - what changed · why`.

**Never overwrite Change Log history.** Git holds the old file content; the Change Log exists to surface *what changed and why* without reading git. A new code file needs its own doc, seeded with a Change Log, before the code merges.

## How this differs from `/adda`

`/adda` is the machine-readable architecture memory that compiles to OKF and feeds an LLM after a compaction. These docs are for the *human or agent about to edit a file* - the invariants and scope guards that a diff would not reveal. `adda diff` checks `/adda`; nothing automatically checks these, which is why the same-commit rule matters.
