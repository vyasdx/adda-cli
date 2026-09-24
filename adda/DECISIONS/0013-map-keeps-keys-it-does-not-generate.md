<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0013 — The map keeps keys it does not generate

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-028
Amends: ADR-0012

## Context

ADR-0012 fixed the list of instruction files with no configuration, and said
why: a key in `MODULE_MAP.json` would be silently dropped the next time
`sync --map` regenerated the map. That was true. `sync --map` rebuilt the file
from `map` and `exempt`, and carried over `include` by name — nothing else.

So the one project-specific need the rule could not meet was a file only that
project knows about: an `intent.md`, a `docs/AGENT_RULES.md`. A test written
before the fix confirmed the loss: a map carrying `instructions` came back from
a regenerate without it.

A dropped setting is the worst kind of failure for this tool. It does not error;
the check it configured simply stops running, and the report reads the same as
before.

## Decision

- **`sync --map` carries over every top-level key it does not generate.** It
  still owns and rebuilds `map` and `exempt`; `include` keeps its special
  handling because it changes what is generated. Anything else — `instructions`
  today, a key a later version adds, a key a user adds for their own notes — is
  copied through verbatim.
- **`instructions` in the map lists a project's own instruction files** for
  `audit --refs`. They are checked by exactly the rules ADR-0012 set for the
  conventional files. The conventional files still need no entry.
- **A configured file that does not exist is reported in `skipped`.** An absent
  conventional file means the project does not use that tool. An absent
  configured one is a typo or a rename, and silence would read as "checked,
  clean".
- Paths only, no globs. Nobody has asked for a pattern yet.

## Consequences

- ADR-0012's "no configuration" bullet is superseded for project-specific files.
  Its reasoning stands: the list could not be configured *safely* until the map
  stopped losing keys.
- Hand-edits to `map` and `exempt` are still overwritten by a regenerate. That is
  unchanged and is loud rather than silent: a hand-exempted file comes back as a
  missing doc in `audit`.
- Pinned by tests, each shown to fail when its fix is removed: carry-over, and
  the report of an absent configured file.
