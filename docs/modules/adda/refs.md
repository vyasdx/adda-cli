<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `refs` - `src/adda/refs.py`

Last verified: 2026-09-24

**Purpose** - The deterministic slice of the gap ancestry cannot see (ADR-0010, ADR-0011). `audit` decides staleness by commit ancestry, so a doc committed alongside its code reads as current even when it names a function deleted in that same commit. `refs` checks that every code name a mapped doc cites still appears somewhere in the source. Opt-in, via `adda audit --refs`.

## Public surface

`refs_report(repo, adda_dir) -> (findings, skipped, stats)` · `extract_refs(text) -> [(line, name)]`

Findings are `{"item": "doc:line", "issue": "ref missing", "severity": "medium", "ref": name}`. `stats` is `{"docs": n, "refs": m}` - how many docs were read and how many names were checked.

## Invariants

- **Deterministic and offline - no model calls (ADR-0003).** It checks that a cited name *exists*. It never judges whether the prose around it is true; that would take a model, and ADR-0010 keeps that out of `audit`.
- **Opt-in.** Plain `adda audit` keeps exactly its five rules and exit code, so no CI already running it changes behaviour. A new rule has a new false-positive profile and earns default status by running clean first.
- **Existence is searched across all code, not the doc's own module.** A doc may cite a neighbour module, a test helper or a script. The corpus is `sync.SOURCE_SUFFIXES` files anywhere outside `IGNORE_DIRS` - but with tests, scripts and examples put back in, because the question is "does this name exist?", not "what needs a doc?". Searching more code can only turn a flag into a pass, the safe direction for this rule.
- **History sections are not checked.** A heading matching change log or history starts one, and it runs until the next heading at the same or shallower level. A Change Log exists to name code that is gone.
- **Only code-shaped spans count.** A backticked span is a reference only if it is a bare identifier - optionally written as a call - that is snake_case, CamelCase or called. Builtins and keywords are excluded. Paths, flags, dotted names, filenames and plain words are ignored, and so are fenced code blocks.
- **Cannot tell is skipped, never passed.** No source files at all, or a doc that cannot be decoded, is reported in `skipped`. With nothing to compare against, every cited name would read as missing - a false alarm, not a finding.
- **Always states how much it checked.** The CLI prints `checked N code name(s) cited in M doc(s)`, so a rule that looked at nothing can never read as a clean pass.
- **A missing doc is not re-reported.** That is `audit` rule 1's finding; `refs` skips a mapped doc that does not exist.

## Change Log (newest first)

- [2026-09-24] ENH-ADDA-027 - module created · catches the doc updated alongside its code but naming code that no longer exists, which ancestry reads as current (RF-ADDA-005). Prototyped against ADDA's own docs first: 47 names, 3 flagged, all 3 false positives - two Change Log entries and a builtin - each now an exclusion with a test. Shipped version checks 36 names in 11 docs with 0 findings. Three deliberate mutations of the implementation were each caught by the tests written for them.
