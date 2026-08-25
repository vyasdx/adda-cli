<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `hook` - `src/adda/hook.py`

Last verified: 2026-08-18

**Purpose** - The commit gate (the vision's layer 4) - enforcement that is mechanical, not memory. Blocks a commit that stages a code file without staging the doc `MODULE_MAP.json` routes it to. Staged-vs-staged needs no dates and no LLM, so there is nothing to forge and nothing to forget. `adda hook install` writes a pre-commit stub, with the install-time Python interpreter baked in, that invokes `python -m adda.cli hook run` on every commit.

## Public surface

`HOOK_STUB` (the shell script template, `{python}` placeholder) · `hook_body(python) -> str` (renders the stub for a specific interpreter) · `staged_paths(repo) -> [str]` · `check_staged(repo, adda_dir, staged) -> [(code, required_doc)]`

CLI: `adda hook run [path]` (invoked by the installed hook) · `adda hook install [path] [--force]` (writes `.git/hooks/pre-commit`).

## Invariants

- **Blocks, exit 1 - a warning that can be scrolled past is not enforcement.** `hook run` raises `typer.Exit(1)` on any gap; there is no "print and continue" mode.
- **Escapes are `git commit --no-verify` and `ADDA_SKIP=1`, and both are printed in the failure message itself** - discoverable at the exact moment of friction, not buried in a doc the committer isn't reading right now.
- **Commit-scoped only - never runs `audit` or `diff`.** Pre-existing repo-wide drift blocking an unrelated commit is how a gate earns a permanent `--no-verify` and stops enforcing anything at all.
- **A missing `MODULE_MAP.json` must not block.** `check_staged` catches `load_map`'s `FileNotFoundError` and returns no gaps - that repo has not adopted the convention, and reporting it is `audit`'s job, not the gate's.
- **`staged_paths` fails open when git is unavailable** (not a repo, git missing, decode failure) - the one deliberate fail-open in the release. The gate assists committing rather than auditing; a broken git invocation should not brick every commit in every repo that happens to run `adda hook run`.
- **Staged paths are read with `-z` and `encoding="utf-8"`.** Git quotes non-ASCII paths by default (`"src/caf\303\251.py"`); a mangled path matches no `MODULE_MAP` entry, which would let a staged file slip past silently. `-z` gives unquoted, NUL-separated paths; `encoding="utf-8"` is required because `text=True` alone decodes with the locale/console codepage (e.g. Windows cp1252), which mangles a UTF-8 filename differently than the quoting bug it was meant to fix.
- **`install` never clobbers an existing hook without `--force`.** Without it, `hook_install` refuses, prints the exec line for the current interpreter so the user can splice it into their existing hook by hand, and exits 1.
- **The stub delegates to `python -m adda.cli hook run`** rather than embedding the gate logic in the shell script, so hook upgrades ship with the package and never require reinstalling `.git/hooks/pre-commit`.
- **The interpreter path is baked in at install time, so the hook does not depend on `PATH`.** A bare `adda` (or `python`) is not reliably resolvable when git invokes hooks: ADDA is normally installed into a project venv that is not active in that shell, and in ADDA's own repo a bare `adda` can even resolve to the `adda/` architecture-memory *directory* instead of the executable (`exec: adda: cannot execute: Is a directory`). `hook_install` bakes `sys.executable` (forward slashes, since git's bundled `sh` handles `C:/...` but not `C:\...`) into the stub via `hook_body`, and verifies the write by reading the file back and checking for `hook run` before reporting success.
- **The baked-in stub fails OPEN if that interpreter later disappears** (venv deleted or moved) - it prints a warning and `exit 0` rather than blocking every future commit in the repo forever.
- **The hook is untracked and therefore never travels with a clone.** `.git/hooks/pre-commit` is machine-specific and not shared by git, so every clone and every CI image must run `adda hook install` itself to enable enforcement. Without a manual reinstall on each machine, the gate is silently inactive.
- **Reinstall after moving or recreating the venv.** The interpreter path is baked in at install time; if that interpreter disappears, the hook fails open (warns, exits 0) rather than blocking commits. This means enforcement can silently lapse after a venv deletion or relocation, and a periodic `adda audit` run is the backstop to detect drift.
- **Known limitation: renaming a mapped file to an unmapped name (`git mv`) is invisible to the gate**, because only the new path appears in the staged list - the old, still-mapped path is simply absent, not "staged without its doc". `audit` catches it on the next run: the map still points at the vanished old path, so rule 4 (`doc orphaned`) and rule 3 (`code unmapped`) both fire.

## Change Log (newest first)

- [2026-08-18] ENH-ADDA-007 — documented that the hook is per-machine: untracked, interpreter baked in at install time, fails open if that interpreter goes away · enforcement can lapse silently, so `adda audit` is the backstop.
- [2026-08-18] ENH-ADDA-007 — hook stub now execs the install-time interpreter via `-m adda.cli` · `exec adda hook run` needed `adda` on PATH and resolved to ADDA's own `adda/` directory, so the installed hook did not run at all.
- [2026-08-18] ENH-ADDA-007 — module created · the commit gate: enforcement that is mechanical, not memory.
