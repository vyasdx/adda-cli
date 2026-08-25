<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0002: Ship scaffold templates inside the package

id: ADR-0002
status: accepted

## Context
BUILD_PLAN §5 drew the `adda init` templates at repo-root `templates/`. Repo-root data
does not survive a real `pip install` (only editable installs), so `adda init` would
break for anyone installing the wheel.

## Decision
Place the templates at `src/adda/templates/adda/` (inside the package) and locate them
via `Path(__file__).parent / "templates" / "adda"`.

## Consequences
`adda init` works after a real wheel install, not just editable. §5's intent (tool code
vs scaffolded data kept separate) is preserved; locating them is a one-liner.
