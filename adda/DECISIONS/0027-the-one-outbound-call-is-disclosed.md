<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0027 — The one outbound call is disclosed where it is triggered

Date: 2026-11-02
Status: accepted
Issue: ENH-ADDA-049, BUG-ADDA-036
Relates to: ADR-0003

## Context

ADDA was described as "offline" on the landing page and in the explainer. One
flow is not: `adda monitor --file F --model claude-*`, with the optional
`anthropic` extra installed and `ANTHROPIC_API_KEY` set, sends F's text to
Anthropic's token-counting endpoint (`src/adda/sentinel.py`). Only the module
doc said so. A user with that key set for other reasons would not expect the
upload, and a security review asks what leaves the network before anything else.

## Decision

Keep the flow (it gives an exact count for Claude models and generates
nothing) and say so where it is triggered and where people look:

- `README.md` has a "What leaves your machine" section: nothing by default,
  the one opt-in flow, its three conditions, and how to stay local
  (`--limit` instead of `--model`).
- The `--file` help text of `monitor` names the same conditions.
- Product-wide claims say "offline by default", never just "offline".
- The same README section states ADDA's regulatory position in one line each.

## Consequences

- A new outbound flow needs this README section updated in the same change,
  or the published claim drifts again; `REVIEW.md` already treats a network
  call as an Important finding.
- No switch to turn the flow off was added: leaving out a `claude-*` model,
  the extra or the key already keeps `monitor` local.
