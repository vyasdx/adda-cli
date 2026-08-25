<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADDA — instructions for AI coding agents

> This file ships to the public repository as `CLAUDE.md`. It is the source of
> truth for the public copy; edit it here, not in the export.

## What ADDA is

A provider-agnostic Python CLI (Typer + pydantic) that gives an AI coding agent
curated, git-versioned **architecture memory** — and detects when that memory has
drifted from the code it describes.

Three parts:

- **ADDA memory** — constraints, modules, decisions (ADRs) and state as markdown
  in `/adda`, versioned in git. You author it. That is the point: it is curated,
  not scraped.
- **OKF (Open Knowledge Format)** — that markdown compiles to small, typed,
  provider-agnostic JSON. Format locked at v0.2 (`OKF_SCHEMA.md`).
- **Context Sentinel + rehydrate** — a token gauge that says *when* to checkpoint
  (60/85/90%), and a command that emits the minimal OKF needed to restore an
  agent's architecture memory after a context compaction.

Closed loop: **monitor → checkpoint → compact → rehydrate.**
Enforcement layer: **`sync --map` → `audit` → `hook`.**

One line: *storing context is solved; knowing it is still true isn't.*

## Scope guards — do not violate

These are locked decisions, recorded as ADRs in `adda/DECISIONS/`. They are not
preferences.

- **Context/memory tool, NOT an LLM executor.** No `adda run <model>`. `adda eval`
  is a deterministic offline metric with no model calls (ADR-0003).
- **OKF and the CLI stay provider-agnostic.** No Claude/Codex/Copilot-specific
  fields in the format (ADR-0005).
- **`headroom-ai` is OPTIONAL** with a graceful no-op fallback. `--compress` is
  opt-in and default output stays faithful, valid OKF (ADR-0004).
- **`audit` is deterministic and offline.** A rule that cannot run is *reported as
  skipped*, never silently passed (ADR-0007).
- **The commit gate is commit-scoped.** It never runs `audit` or `diff` — a gate
  that blocks unrelated commits earns a permanent `--no-verify` and stops
  enforcing anything.
- Every source file carries the authorship header.

## Dogfood discipline

ADDA documents itself in `/adda`, and that is the project's own credential.

Before editing a component under `src/adda/`, read `adda/ARCHITECTURE.md` and the
relevant ADR. After editing, in the **same** change:

1. Update `/adda` (a new decision means a new ADR).
2. Update the module's doc in `docs/modules/`: bump its `Last verified:` line and
   **append** to its `## Change Log (newest first)`. Never overwrite Change Log
   history — git holds the old content; the Change Log surfaces *what changed and
   why* without reading git.

`adda diff .` and `adda audit .` must both stay clean. `okf.json` is generated and
gitignored — regenerate with `adda export`.

## Verifying a change

```bash
python -m pytest -q     # unit tests
adda diff .             # documented modules vs the actual repo
adda audit .            # doc-layer drift: missing, stale, unmapped, orphaned
adda eval .             # rehydration fidelity; load-bearing MUST stay 100%
```

A load-bearing fidelity below 100% means `rehydrate` has lost critical
architecture memory. That is a bug, not a number to record.

## Build discipline

Minimum that works; no speculative code. Mark deliberate simplifications with a
`ponytail:` comment naming the ceiling and the upgrade path.
