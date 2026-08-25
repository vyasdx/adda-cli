<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0004: `--compress` is opt-in; default output stays faithful

id: ADR-0004
status: accepted

## Context
headroom-ai compresses by dropping low-signal content (its SmartCrusher drops JSON
fields). Run blindly on an OKF that must stay valid, it would corrupt the OKF. headroom's
reversibility (CCR) only works inside its proxy + MCP retrieve tool, which ADDA's library
`compress()` call does not wire.

## Decision
Wire headroom behind an opt-in `--compress` flag on `export`/`rehydrate`. Default output
is always faithful, valid OKF. If headroom is absent, `--compress` is a clean no-op.

## Consequences
Default behaviour never produces invalid/lossy OKF. Token savings come primarily from
ADDA's own minimal `rehydrate` (~58% smaller), not from headroom.
