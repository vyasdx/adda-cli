<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `cli` - `src/adda/cli.py`

Last verified: 2026-09-24

**Purpose** - ADDA's only entrypoint - the Typer app that wires the thirteen commands to the library modules.

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
| `audit [path] [--json] [--refs]` | doc-layer drift: missing, stale, unmapped, orphaned docs; with `--refs`, also code names and paths that docs and instruction files cite but no longer exist | `audit.audit_report`, `refs.refs_report`, `refs.instructions_report` |
| `eval [path] [--json]` | rehydration fidelity % | `evaluate.evaluate` |
| `doctor [path]` | prove the commit gate is on: hook in the directory git reads, runs the ADDA gate, interpreter exists and imports adda, map maps something, `ADDA_SKIP` unset; exit 1 on any failure | `doctor.diagnose` |
| `hook run [path]` | block the commit when staged code is missing its staged doc | `hook.check_staged`, `hook.staged_paths` |
| `hook install [path] [--force]` | write `pre-commit` where git reads hooks (`.git/hooks`, or `core.hooksPath`), delegating to `hook run`; refuses to overwrite without `--force` | `hook.HOOK_STUB` |

## Invariants

- **`diff` exits 1 when drift is found.** That non-zero exit is what makes it usable in a pre-commit hook or in CI. Do not "fix" it to always exit 0.
- **`monitor` requires exactly one of `--tokens` / `--file`.** The XOR guard is deliberate; both or neither is a `BadParameter`.
- **Checkpoint filenames are UTC and colon-free** (`%Y%m%dT%H%M%SZ`) so they stay valid Windows filenames and sort chronologically.
- **`_resolve_adda_dir` accepts either a project root or the `adda/` dir itself.** Every path-taking command routes through it, so argument handling stays uniform.
- **No `adda run <model>`.** ADDA is a context/memory tool, not an LLM executor (locked scope guard).
- **`audit` exits 1 on any finding, matching `diff`'s contract**, so it drops into CI/pre-commit unchanged. A severity the color lookup doesn't recognise falls back to a default color rather than raising `KeyError` - a crash in the drift reporter would be worse than the drift.
- **`cli.py` carries `if __name__ == "__main__": app()`.** `hook_install` bakes `"{sys.executable}" -m adda.cli hook run` into the git hook stub (via `hook.hook_body`), so the module must be runnable with `python -m adda.cli`, not only through the installed console-script entry point.

## Change Log (newest first)

- [2026-09-24] BUG-ADDA-027 - `hook install` asks `hook.hooks_dir` where git reads hooks instead of assuming `.git/hooks`, creates it if needed, names a custom `core.hooksPath` in its output and points at `adda doctor` · a husky-style repo got a gate git never ran.
- [2026-09-24] ENH-ADDA-030 - added `doctor` · the gate fails open and is never cloned, so a broken or absent gate looked exactly like a working one. Prints one `[ ok ]`/`[FAIL]`/`[ -- ]` line per check and a count line; exits 1 on any failure.
- [2026-09-24] ENH-ADDA-028 - `sync --map` passes the whole previous map to `module_map_json`, not just `include`, and ignores a previous file that is valid JSON but not an object; `audit --refs` passes `modulemap.load_instructions` to `instructions_report` · settings the generator does not own now survive a regenerate, which is what makes a configurable instruction-file list safe.
- [2026-09-24] ENH-ADDA-024 - `audit --refs` also runs `refs.instructions_report` · JSON gains an `instructions` count block beside `refs`, and the text output adds a line stating how many names and paths were checked in how many instruction files, and how many path-like spans did not resolve and were left unchecked. Plain `audit` is unchanged.

- [2026-09-24] ENH-ADDA-027 - `audit --refs` wires in `refs.refs_report` · opt-in, so plain `audit` keeps its five rules and exit code for every CI already running it. With the flag, findings and skipped notes merge into the same report, JSON gains a `refs` count block, and the text output always prints how many names were checked, so a rule that looked at nothing never reads as a clean pass.

- [2026-08-26] BUG-ADDA-021 - `adda eval` prints `n/a` with the reason when no architecture file has been authored, and a `[partial]` line naming the scaffold files still unwritten when only some have · a fidelity score over memory nobody wrote is not a low score, it is not a score at all.
- [2026-08-26] DEC-ADDA-009 - `sync --map --out <path>` reads the existing file's `include` list and carries it forward · an override a routine regeneration erases is not an override.
- [2026-08-26] BUG-ADDA-022 — stdout/stderr are reconfigured to UTF-8 at CLI entry · a REDIRECTED stdout on Windows takes the console codepage, so `adda rehydrate . > out.json` raised UnicodeEncodeError on the OKF's arrows. That is the documented default path of the north-star command; `--out` was unaffected because it writes explicit UTF-8, which is exactly why every local run looked fine.
- [2026-08-26] BUG-ADDA-016/017 — `--out` now creates its parent directory, and `init --force` overwrites scaffold files instead of `rmtree`ing the directory · the first crashed on step 1 of the README quickstart, the second silently deleted MODULE_MAP.json and with it the commit gate's ability to block anything.
- [2026-08-18] ENH-ADDA-007 — re-verified after "bake the interpreter into the hook" (`dfdfa00`) · `hook_install` now imports `hook_body`/`sys` and builds the stub with `sys.executable`; `cli.py` gained a `python -m adda.cli` entrypoint so the baked-in hook stub can invoke it without `adda` on `PATH`. Documented in Invariants.
- [2026-08-18] ENH-ADDA-007 — added `hook install` (writes `.git/hooks/pre-commit`, refuses to clobber without `--force`) · `hook run` added to the Commands table (it existed in code but was undocumented). Command count in Purpose corrected to twelve.
- [2026-08-18] ENH-ADDA-007 — `audit --json` now emits JSON on the missing-MODULE_MAP error path too · a CI script piping to `jq` broke on the one error it most needed to parse. Command count in Purpose corrected.
- [2026-08-18] ENH-ADDA-007 — added `audit` command (`audit.audit_report`) · exposes the doc-layer drift sweep `diff` cannot perform; skipped rules always print, exit 1 matches `diff`.
- [2026-08-18] ENH-ADDA-007 — `sync` gained `module_map_json` / `--map`, deriving code→doc routing from `discover_modules` · one definition of "what is source" across sync, diff and audit.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
