<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# ADR-0006: headroom optional (runtime), ponytail build-time only

id: ADR-0006
status: accepted

## Context
Two reference tools sit near ADDA. headroom-ai compresses payloads sent to a model
(runtime). ponytail is a build-time YAGNI discipline. Neither should be a hard runtime
dependency of ADDA, and the two operate at different layers.

## Decision
headroom-ai is an OPTIONAL extra (`pip install ".[headroom]"`) consumed only via the
opt-in `--compress` path, with graceful no-op fallback when absent. ponytail influenced
only how this codebase was written (kept it lean) and has zero runtime presence.

## Consequences
ADDA installs and runs with no compression dependency. ADDA and headroom are complementary
layers — memory (ADDA) vs compression (headroom) — not competitors.
