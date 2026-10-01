<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Current State

updated: 2026-10-02
summary: v0.5.1 adds the two rollout accelerators: `audit --refs` checks markdown links in instruction files (ADR-0020), and `sync --map` points new code at the module doc that already names it (ADR-0021). v0.5.0 extends the checks beyond module docs and proves the gate is on. `audit --refs` checks the names and paths cited in docs and in every coding agent's instruction files (ADR-0011, 0012, 0014); `doctor` proves the commit gate is installed where git reads hooks and can run (ADR-0015); `memory` audits an agent's memory folder (ADR-0016); `restated` lists copies of text a correction removed (ADR-0017). `sync --map` keeps a product's own doc choices across regenerates (ADR-0013, 0019), which the fleet rollout depends on. v0.4.0 made every check say what it could not determine; that still holds.

## Notes
- Fifteen commands. The test count is not recorded here - CI derives it (`scripts/check_counts.py`); a hand-kept number drifted five times. OKF schema locked at v0.2 (ADR-0005).
- Enforcement is mechanical and commit-scoped (ADR-0007): `hook` compares staged-vs-staged, no dates, no LLM; `audit` is the deterministic offline repo-wide sweep (extends ADR-0003).
- `adda hook install` is installed on ADDA's own `.git/hooks/pre-commit` — this repo now enforces its own doc-gate on every commit. `adda doctor .` proves it on any clone, since the hook is never cloned and fails open (ADR-0015).
- Two adversarial-review passes ran before the v0.1.0 and v0.2.0 tags.
- This `/adda` is ENH-ADDA-001: ADDA documents itself, and that is the project's own credential.
- Keep this /adda current from here on: edit a module's code → update its entry here.
