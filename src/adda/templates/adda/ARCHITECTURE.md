<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Architecture

One-paragraph overview of how the system fits together. Replace this with your own.

## Constraints

<!-- Hard rules the LLM must never violate. One per `- ` line. These are emitted into
     every OKF and into every `adda rehydrate`. -->
- Keep architecture docs in /adda up to date before changing code.
- Do not introduce a new dependency without recording an ADR in DECISIONS/.

## Modules

<!-- One module per line: `- name: description (status)`.
     status is `active` (default) | `planned` | `deprecated`.
     Only `active` modules are emitted by `adda rehydrate`. -->
- core: Core domain logic. (active)
- api: Public HTTP interface. (active)
- worker: Background job processing. (planned)
