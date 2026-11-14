<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `safety` - `src/adda/safety.py`

Last verified: 2026-11-14

**Purpose** - The trust boundary (ADR-0030): the repository ADDA reads is untrusted input. Keeps it from making ADDA run its code, write outside it, or read outside it.

## Public surface

`LAUNCH` (Python `-c` code that drops the current directory from the import path, then runs the CLI; used by the commit hook) · `IMPORT_CHECK` (the same scrub, then `import adda.cli`; used by `doctor`) · `GIT` (the `git` argv prefix that neutralises the repository's own config) · `write_text(target, text, root=None, newline=None)` · `check_target(target, root=None)` · `UnsafeWrite` · `inside(root, rel) -> bool`

## Invariants

- **The repository root is never on the import path when ADDA starts from a hook.** `-m` and plain `-c` put it first; `LAUNCH` removes `""` and `"."` before importing anything from it.
- **No write follows a symlink.** A symlinked target is refused; a target lexically inside `root` must resolve inside it; the text goes to a temp file beside the target and `os.replace` moves it into place, keeping the target's mode.
- **Command-line git config beats the repository's.** Every git call starts with `GIT`.

## Change Log (newest first)

- [2026-11-14] BUG-ADDA-046 — `check_target` split out of `write_text` so `init --force` can check each scaffold file before `copytree` writes it · copytree follows a symlinked destination too.
- [2026-11-14] BUG-ADDA-045, 046, 047, 048 — module added (ADR-0030) · the 2026-11-14 security review: `python -m` ran a committed `json.py`, writes followed repository symlinks, repository git config could name a program for git to run, map paths could leave the repository.
