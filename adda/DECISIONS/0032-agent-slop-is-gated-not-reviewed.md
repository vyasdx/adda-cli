<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0032 — Complexity and blind excepts are gated in lint, not caught in review

Date: 2026-11-15
Status: accepted
Issue: ENH-ADDA-063 (with ENH-ADDA-062, RF-ADDA-016)

## Context

All of ADDA's code is written by agents from Vyas's intent. On 2026-11-15 he
asked how he would know if any of it is slop. A first measurement of
`src/adda` (3,353 lines) found no dead code (vulture), one lint suppression,
ruff clean and 284 tests, but two functions at radon grade F
(`instructions_report` 47, `restated_report` 45) and six at D. Those grew the
way agent code grows: each fix adds a branch to the function that already
works, and nothing pushes back. `refs.py` has 20 commits.

The same review found `refs._ignored` starting one `git check-ignore` per
candidate path (62 processes for a one-line doc) while `sync.git_ignored`
already answers a batch in one call.

Lint excluded BLE001 and S110 because every existing blind except was
deliberate. That also let a new one in without a word.

## Decision

- **ruff C901 with max-complexity 15** joins CI's lint. The three functions
  over it today (`memory_report`, `instructions_report`, `restated_report`)
  carry `noqa: C901 - RF-ADDA-016`; RF-ADDA-016 splits them and removes the
  marker. Nothing new may cross the line without a visible, named exception.
- **ruff BLE and S110** join too. The deliberate blind excepts (headroom and
  the Anthropic SDK are optional and must degrade, never break the caller) say
  why on their own line. `sync.discover_deps` now names what it catches, so a
  bug in it surfaces instead of reading as "no dependencies".
- **Mutation testing (ENH-ADDA-062)** measures whether the tests notice a
  broken line. It is run on purpose, not in CI: one mutant costs a full test
  run, and on Windows that is 15-20 s.

## Consequences

- A rule, not a reviewer, stops the "one more branch" pattern. 15 is above
  ruff's default 10 because five more functions sit between 11 and 15 today;
  lowering it is a later, measured step.
- A `noqa` is an escape hatch. Each one names its reason or its issue, and a
  search for `noqa: C901` lists what is left to split.
