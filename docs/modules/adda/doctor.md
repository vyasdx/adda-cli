<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `doctor` - `src/adda/doctor.py`

Last verified: 2026-09-24

**Purpose** - Prove the commit gate is on instead of assuming it (ADR-0015). The hook fails open by design and is never cloned, so an absent or broken gate looks exactly like a working one. `adda doctor` checks each way the gate can be installed and still enforce nothing, and exits 1 if any fails.

## Public surface

`diagnose(repo) -> [{"check", "state", "detail"}]` with `state` in `ok` / `fail` / `n/a` · `hooks_dir(repo) -> Path | None`

Checks, in order: `git repository` · `pre-commit hook` · `runs the ADDA gate` · `executable` · `interpreter` · `adda importable` · `MODULE_MAP.json` · `ADDA_SKIP`.

## Invariants

- **The hooks directory comes from git, never from an assumption.** `git rev-parse --git-path hooks` honours `core.hooksPath` and worktrees. Assuming `.git/hooks` is exactly how `hook install` wrote a gate git never ran (BUG-ADDA-027); a missing hook under a custom path says so in its detail.
- **The interpreter is run, not just found.** A path that exists but cannot `import adda.cli` - a recreated venv without `pip install -e .` - fails like a missing one, because the hook would fail the same way. Tested against a real bare venv, since a non-executable path only exercises the "cannot run" branch.
- **A map that maps nothing is a failure.** Absent, unreadable or empty `MODULE_MAP.json` means the gate has nothing to block; each gets its own fix in the detail.
- **`ADDA_SKIP` set in the environment is a failure**, not a note: every commit from that shell bypasses the gate.
- **Three states, never two.** When the checker cannot tell - no recognisable interpreter line in a hand-written hook, the execute bit on Windows - it says `n/a` rather than passing.
- **Read-only and offline.** It changes nothing in the repo and calls no network; the only process it starts is the hook's own interpreter, with `-c "import adda.cli"`.
- Each check was shown to matter: removing it turns a test red (seven mutations, two of which first survived and exposed weak tests that were then tightened).

## Change Log (newest first)

- [2026-09-24] ENH-ADDA-030 - module created · the gate's fail-open design and the fact that hooks are never cloned meant a fresh clone, a deleted venv or a `core.hooksPath` repo all looked enforced while enforcing nothing. Found while designing it: BUG-ADDA-027, `hook install` ignoring `core.hooksPath`, which this module detects.
