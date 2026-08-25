<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0005: Lock the OKF schema at v0.2 (provider-agnostic)

id: ADR-0005
status: accepted

## Context
OKF is the wedge ("schema.org for architecture context"). v0.2 features (`sync`/`diff`)
need a `path` on each module to map docs to code.

## Decision
Lock the OKF format at `okf_version` 0.2, documented as a first-class artifact in
`OKF_SCHEMA.md` (with the canonical JSON Schema generated from `okf.py`). Add the additive
optional `Module.path`. Keep the format provider-agnostic — no Claude/Codex/Copilot fields.
A drift-guard test keeps `OKF_SCHEMA.md` in sync with the pydantic models.

## Consequences
The format is the centerpiece; ADDA is its reference implementation. Package release version
(0.2.0) and OKF format version (0.2) are intentionally distinct.
