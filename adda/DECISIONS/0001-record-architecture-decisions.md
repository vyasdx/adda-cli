<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0001: Keep architecture decisions in /adda

id: ADR-0001
status: accepted

## Context
LLM coding sessions lose architectural decisions across context compactions.

## Decision
Record every significant decision as an ADR in /adda/DECISIONS/. ADDA compiles
accepted ADRs into the OKF so they survive rehydration.

## Consequences
Decisions are versioned in git and travel with the OKF to any LLM provider.
