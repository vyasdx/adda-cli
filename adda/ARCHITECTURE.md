<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Architecture

ADDA is a provider-agnostic Python CLI (Typer + pydantic) that gives AI coding
assistants a persistent, git-versioned memory of a project's architecture. Markdown
in `/adda` compiles to a small JSON format (OKF); `rehydrate` emits the minimal OKF
to restore memory after a compaction; the Context Sentinel says when to checkpoint;
`diff`/`eval` measure drift and rehydration fidelity. v0.3 adds an enforcement
layer: `sync --map` derives `MODULE_MAP.json` (code->doc routing), `audit` sweeps
the whole repo for doc-layer drift against that map, and `hook` blocks a commit
that stages code without its doc. Closed loop: monitor → checkpoint → compact →
rehydrate → audit/enforce.

## Constraints

- ADDA is a context/memory tool, not an LLM executor: no `adda run <model>`; `adda eval` is a deterministic offline metric (no model calls).
- OKF and the CLI stay provider-agnostic: no Claude/Codex/Copilot-specific fields in the format.
- headroom-ai is an OPTIONAL dependency with graceful no-op fallback; `--compress` is opt-in and default output stays faithful, valid OKF.
- Net-new tool: imports zero source from any internal project.
- Every source file carries the authorship header.

## Modules

- cli: Typer entrypoint wiring all twelve commands. (active) [src/adda/cli.py]
- okf: OKF pydantic schema + markdown→OKF compiler. (active) [src/adda/okf.py]
- sentinel: Context Sentinel token gauge + count_tokens fallback. (active) [src/adda/sentinel.py]
- rehydrate: minimal-OKF emitter (the north-star). (active) [src/adda/rehydrate.py]
- compress: optional headroom-ai wrapper (graceful no-op). (active) [src/adda/compress.py]
- sync: codebase → ARCHITECTURE skeleton generator. (active) [src/adda/sync.py]
- diff: drift detection (documented modules vs repo). (active) [src/adda/diff.py]
- evaluate: rehydration-fidelity metric (`adda eval`). (active) [src/adda/evaluate.py]
- modulemap: MODULE_MAP.json code->doc routing (active) [src/adda/modulemap.py]
- audit: doc-layer drift sweep (active) [src/adda/audit.py]
- hook: pre-commit doc gate (active) [src/adda/hook.py]
