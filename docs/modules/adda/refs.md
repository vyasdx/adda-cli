<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `refs` - `src/adda/refs.py`

Last verified: 2026-09-24

**Purpose** - The deterministic slice of the gap ancestry cannot see (ADR-0010, ADR-0011). `audit` decides staleness by commit ancestry, so a doc committed alongside its code reads as current even when it names a function deleted in that same commit. `refs` checks that every code name a mapped doc cites still appears somewhere in the source. Opt-in, via `adda audit --refs`.

It also covers the instruction files an agent reads before any code (ADR-0012): `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `README.md`. There, every cited code name *and* every repository path must exist.

## Public surface

`refs_report(repo, adda_dir) -> (findings, skipped, stats)` · `instructions_report(repo) -> (findings, skipped, stats)` · `extract_refs(text) -> [(line, name)]` · `extract_paths(text) -> [(line, path)]` · `INSTRUCTION_FILES`

Findings are `{"item": "file:line", "issue": "ref missing" | "path missing", "severity": "medium", "ref": name_or_path}`. `refs_report` stats are `{"docs", "refs"}`; `instructions_report` stats are `{"files", "refs", "paths", "unresolved"}` - so every count of what was checked, and of what could not be, is visible.

## Invariants

- **Deterministic and offline - no model calls (ADR-0003).** It checks that a cited name *exists*. It never judges whether the prose around it is true; that would take a model, and ADR-0010 keeps that out of `audit`.
- **Opt-in.** Plain `adda audit` keeps exactly its five rules and exit code, so no CI already running it changes behaviour. A new rule has a new false-positive profile and earns default status by running clean first.
- **Existence is searched across all code, not the doc's own module.** A doc may cite a neighbour module, a test helper or a script. The corpus is `sync.SOURCE_SUFFIXES` files anywhere outside `IGNORE_DIRS` - but with tests, scripts and examples put back in, because the question is "does this name exist?", not "what needs a doc?". Searching more code can only turn a flag into a pass, the safe direction for this rule.
- **History sections are not checked.** A heading matching change log or history starts one, and it runs until the next heading at the same or shallower level. A Change Log exists to name code that is gone.
- **Only code-shaped spans count.** A backticked span is a reference only if it is a bare identifier - optionally written as a call - that is snake_case, CamelCase or called. Builtins and keywords are excluded. Paths, flags, dotted names, filenames and plain words are ignored, and so are fenced code blocks.
- **Cannot tell is skipped, never passed.** No source files at all, or a doc that cannot be decoded, is reported in `skipped`. With nothing to compare against, every cited name would read as missing - a false alarm, not a finding.
- **Always states how much it checked.** The CLI prints `checked N code name(s) cited in M doc(s)`, so a rule that looked at nothing can never read as a clean pass.
- **A missing doc is not re-reported.** That is `audit` rule 1's finding; `refs` skips a mapped doc that does not exist.
- **A line that names something to say it is gone is skipped** - "retired", "removed", "renamed" and the like - for names and paths, in module docs and instruction files. It is the one-line form of a Change Log.
- **Instruction files are checked, never mapped (ADR-0012).** They describe the whole repo, so ancestry against all the code would read them stale forever. The file list is fixed with no configuration, because a key in `MODULE_MAP.json` would be dropped the next time `sync --map` regenerates it.
- **A path is checked only when its first segment exists in this repo.** Anything else - another repository, a bare filename relative to elsewhere, a slash command - is counted as `unresolved` and printed, never flagged.
- **Paths:** brace lists expand and each member is checked; a leading `/` means the repo root; the path character set excludes globs and `<placeholders>`; gitignored paths are excused, since a generated file exists on one machine and not on a clean checkout; existence is matched with **exact case**, so a case-insensitive disk and a case-sensitive CI runner give the same answer.
- **A cited conventional instruction filename that is absent is `unresolved`, not missing.** Docs about AI tooling list those names generically. Found by dogfooding - ADDA's own README tripped the rule on its first run, because `.github/` exists for workflows while the Copilot file does not.
- **It verifies what a file cites, never what it omits.** When `refs.py` was added, `CLAUDE.md`'s module list became incomplete and this check passed. That is the boundary, not a bug.

## Change Log (newest first)

- [2026-09-24] ENH-ADDA-024 - `instructions_report` and `extract_paths` added; lines naming something to say it is gone now skipped everywhere · instruction files are what agents read first, and a dead reference in one is a broken instruction. Prototyped on ADDA's own AGENTS.md, CLAUDE.md and README.md first: 30 naive hits, all false positives in seven shapes, each now an exclusion with a test. Six mutations were run against the exclusions; one caught nothing, which exposed a glob check the path character set already covered, so it was deleted as dead code. The first dogfood run then flagged ADDA's own README for listing `.github/copilot-instructions.md` - a new false-positive shape, fixed test-first (red before, green after). Final dogfood: 51 paths and 2 names checked, 24 spans unresolved, 0 findings; the public repo's layout also passes.

- [2026-09-24] ENH-ADDA-027 - module created · catches the doc updated alongside its code but naming code that no longer exists, which ancestry reads as current (RF-ADDA-005). Prototyped against ADDA's own docs first: 47 names, 3 flagged, all 3 false positives - two Change Log entries and a builtin - each now an exclusion with a test. Shipped version checks 36 names in 11 docs with 0 findings. Three deliberate mutations of the implementation were each caught by the tests written for them.
