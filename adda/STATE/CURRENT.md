<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Current State

updated: 2026-08-18
summary: v0.4.0 makes every check say what it could not determine. Discovery reports the source roots it deliberately skipped instead of leaving them silently unenforced (ADR-0009), `adda eval` returns n/a rather than a confident number over an unauthored scaffold, and the README states the limit of ancestry-based staleness rather than letting a user find it (ADR-0010). Flat-layout repos and loose files beside a package are mapped for the first time. Packaging and the public mirror are both allowlisted and proven in CI.

## Notes
- Twelve commands; 67/67 tests pass. OKF schema locked at v0.2 (ADR-0005), unchanged by v0.3.
- Enforcement is mechanical and commit-scoped (ADR-0007): `hook` compares staged-vs-staged, no dates, no LLM; `audit` is the deterministic offline repo-wide sweep (extends ADR-0003).
- `adda hook install` is installed on ADDA's own `.git/hooks/pre-commit` — this repo now enforces its own doc-gate on every commit.
- Two adversarial-review passes ran before the v0.1.0 and v0.2.0 tags.
- This `/adda` is ENH-ADDA-001: ADDA documents itself, and that is the project's own credential.
- Keep this /adda current from here on: edit a module's code → update its entry here.
