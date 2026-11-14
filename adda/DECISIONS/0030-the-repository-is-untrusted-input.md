<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0030 — The repository ADDA reads is untrusted input

Date: 2026-11-14
Status: accepted
Issue: BUG-ADDA-045, 046, 047, 048
Relates to: ADR-0015, ADR-0027

## Context

ADDA was built to check its own and its owner's repositories, and its code
trusted them. It now runs on repositories its user did not write: the November
case study ran it on 83 public ones, and a reviewer runs the commit hook on
whatever a pull request contains. A security review on 2026-11-14 found four
ways such a repository could steer ADDA:

- `python -m adda.cli` (the commit hook, `doctor`) puts the current directory
  first on the import path, so a committed `json.py` ran (reproduced).
- Output files were written through symlinks the repository controls, so a
  tracked `okf.json -> ../../.bashrc` would be overwritten on Linux or macOS.
- The git commands ADDA runs obey the repository's own git config, which can
  name a program for git to run (`core.fsmonitor`). A clone carries no config;
  an archive with a git directory does.
- `MODULE_MAP.json` paths could point outside the repository, and ADDA read
  and printed what they named.

## Decision

Everything a repository supplies is input, never instructions or locations to
trust. One module, `src/adda/safety.py`, holds the rules:

- **Start without the repository on the import path.** The hook and `doctor`
  start Python with `-c` code that drops the current directory before importing
  anything (`LAUNCH`, `IMPORT_CHECK`). `-P` would do it but needs Python 3.11;
  `-I` would also drop user-site installs. `doctor` fails a hook still using `-m`.
- **Never write through a link the repository planted.** A symlinked target is
  refused; a target inside the repository must resolve inside it; the file is
  written beside the target and renamed into place.
- **Neutralise the repository's git config.** Every git call starts with
  `-c core.fsmonitor=false -c safe.bareRepository=explicit`; the one patch diff
  adds `--no-ext-diff --no-textconv`.
- **Read only inside the repository.** Map entries that resolve outside it are
  dropped.

## Consequences

- Hooks installed before 0.5.8 still use `-m`; `adda doctor` reports them, and
  `adda hook install --force` replaces them.
- A deliberate `--out` outside the repository still works; only a path that
  starts inside and resolves outside is refused.
- A repository that symlinks its docs to a folder outside itself loses those
  entries from the map. A commit-scoped gate cannot check them anyway.
- Text from the repository still reaches the agents ADDA's output feeds,
  unmarked (BUG-ADDA-050, L3). ADDA never acts on it; marking it is open.
