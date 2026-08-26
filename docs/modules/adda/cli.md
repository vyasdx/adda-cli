<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `cli` - `src/adda/cli.py`

Last verified: 2026-08-26

**Purpose** - ADDA's only entrypoint - the Typer app that wires the twelve commands to the library modules.

## Commands

| Command | Does | Calls |
|---|---|---|
| `version` | print package version | - |
| `init [path] [--force]` | copy the seed scaffold to `<path>/adda/` | `templates/adda/` |
| `export [path] [--out] [--compress]` | compile `/adda` markdown into validated OKF JSON (default `<project>/okf.json`) | `okf.compile_okf` |
| `monitor (--tokens or --file) [--model] [--limit]` | print usage % + OK/CHECKPOINT/ALERT/FORCE | `sentinel` |
| `rehydrate [path] [--out] [--compress]` | emit the MINIMAL OKF (stdout by default, so it pipes) | `rehydrate.minimal_okf` |
| `checkpoint [path] [-m]` | snapshot `STATE/CURRENT.md` into `STATE/checkpoints/<UTC stamp>.md` | - |
| `sync [repo] [--out] [--map]` | derive an ARCHITECTURE skeleton from the codebase; `--map` emits MODULE_MAP.json instead | `sync.skeleton_markdown` / `sync.module_map_json` |
| `diff [path]` | report documented-vs-actual module drift | `diff.diff_report` |
| `audit [path] [--json]` | doc-layer drift: missing, stale, unmapped, orphaned docs | `audit.audit_report` |
| `eval [path] [--json]` | rehydration fidelity % | `evaluate.evaluate` |
| `hook run [path]` | block the commit when staged code is missing its staged doc | `hook.check_staged`, `hook.staged_paths` |
| `hook install [path] [--force]` | write `.git/hooks/pre-commit`, delegating to `hook run`; refuses to overwrite without `--force` | `hook.HOOK_STUB` |

## Invariants

- **`diff` exits 1 when drift is found.** That non-zero exit is what makes it usable in a pre-commit hook or in CI. Do not "fix" it to always exit 0.
- **`monitor` requires exactly one of `--tokens` / `--file`.** The XOR guard is deliberate; both or neither is a `BadParameter`.
- **Checkpoint filenames are UTC and colon-free** (`%Y%m%dT%H%M%SZ`) so they stay valid Windows filenames and sort chronologically.
- **`_resolve_adda_dir` accepts either a project root or the `adda/` dir itself.** Every path-taking command routes through it, so argument handling stays uniform.
- **No `adda run <model>`.** ADDA is a context/memory tool, not an LLM executor (locked scope guard).
- **`audit` exits 1 on any finding, matching `diff`'s contract**, so it drops into CI/pre-commit unchanged. A severity the color lookup doesn't recognise falls back to a default color rather than raising `KeyError` - a crash in the drift reporter would be worse than the drift.
- **`cli.py` carries `if __name__ == "__main__": app()`.** `hook_install` bakes `"{sys.executable}" -m adda.cli hook run` into the git hook stub (via `hook.hook_body`), so the module must be runnable with `python -m adda.cli`, not only through the installed console-script entry point.

## Change Log (newest first)

- [2026-08-26] DEC-ADDA-009 - `sync --map --out <path>` reads the existing file's `include` list and carries it forward · an override a routine regeneration erases is not an override.
- [2026-08-26] BUG-ADDA-022 — stdout/stderr are reconfigured to UTF-8 at CLI entry · a REDIRECTED stdout on Windows takes the console codepage, so `adda rehydrate . > out.json` raised UnicodeEncodeError on the OKF's arrows. That is the documented default path of the north-star command; `--out` was unaffected because it writes explicit UTF-8, which is exactly why every local run looked fine.
- [2026-08-26] BUG-ADDA-016/017 — `--out` now creates its parent directory, and `init --force` overwrites scaffold files instead of `rmtree`ing the directory · the first crashed on step 1 of the README quickstart, the second silently deleted MODULE_MAP.json and with it the commit gate's ability to block anything.
- [2026-08-18] ENH-ADDA-007 — re-verified after "bake the interpreter into the hook" (`dfdfa00`) · `hook_install` now imports `hook_body`/`sys` and builds the stub with `sys.executable`; `cli.py` gained a `python -m adda.cli` entrypoint so the baked-in hook stub can invoke it without `adda` on `PATH`. Documented in Invariants.
- [2026-08-18] ENH-ADDA-007 — added `hook install` (writes `.git/hooks/pre-commit`, refuses to clobber without `--force`) · `hook run` added to the Commands table (it existed in code but was undocumented). Command count in Purpose corrected to twelve.
- [2026-08-18] ENH-ADDA-007 — `audit --json` now emits JSON on the missing-MODULE_MAP error path too · a CI script piping to `jq` broke on the one error it most needed to parse. Command count in Purpose corrected.
- [2026-08-18] ENH-ADDA-007 — added `audit` command (`audit.audit_report`) · exposes the doc-layer drift sweep `diff` cannot perform; skipped rules always print, exit 1 matches `diff`.
- [2026-08-18] ENH-ADDA-007 — `sync` gained `module_map_json` / `--map`, deriving code→doc routing from `discover_modules` · one definition of "what is source" across sync, diff and audit.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
