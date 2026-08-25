<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0003: `adda eval` is a deterministic offline metric

id: ADR-0003
status: accepted

## Context
The spec described eval as spinning a fresh context with the rehydrated OKF, asking N
questions, and scoring vs a full-context baseline — i.e. an LLM-judged eval. That brushes
against the scope guard "ADDA is not an LLM executor" and is non-reproducible.

## Decision
Implement `adda eval` as a deterministic, offline content-preservation metric: enumerate
the architecture facts in the full OKF and measure how many survive into the minimal OKF
(`overall_fidelity_pct` + `load_bearing_fidelity_pct`). No model call.

## Consequences
Reproducible, provider-agnostic, free, and in-lane. An LLM-judged variant can live later
in a `benchmarks/` script (gated behind an API key), never in the shipped tool.
