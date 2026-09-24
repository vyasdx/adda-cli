<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `restated` - `src/adda/restated.py`

Last verified: 2026-09-24

**Purpose** - After a commit corrects a fact, list the other files that still state the old version word for word (ADR-0017). Advisory and run on purpose: `adda restated [path] --rev <commit>`.

## Public surface

`restated_report(repo, rev="HEAD", also=()) -> (current, records, skipped)`. Hits are `{"file", "line", "source", "words", "text"}`; `source` is the `file:line` of the removed text. `K = 6`.

CLI: `adda restated [path] [--rev REV] [--also DIR]... [--json]` - exit 1 only when a current file still states it.

## Invariants

- **Copies, never paraphrases.** A hit is a run of 6+ consecutive words. "Not covered by the ops dashboard" and "outside the ops dashboard's coverage" share nothing it can see - the case that motivated it - and the output says so on every run. Understanding a rewording would take a model (ADR-0003).
- **Only what the correction removed.** A phrase counts if it touches a removed line and is gone from the file afterwards; the unchanged part of a corrected sentence is still true and is not searched.
- **A move is not a retraction.** A phrase the same commit wrote somewhere it was not before is dropped.
- **Prose only.** `.md`, `.txt`, `.rst`, outside fenced code. Code idioms were nearly all of the prototype's false alarms.
- **Records restate old facts by design.** Folders named `log`, `logs` or `checkpoints`, `CHANGELOG*` files and change-log/history sections are not searched. Dated lines (`[YYYY-MM-DD]`), rows marked `closed YYYY-MM-DD` and files marked superseded are reported apart, as `records`, and do not fail the run.
- **K = 6** was measured, not chosen: 5 matched code idioms, 8 missed real restatements.
- **Searched as the repo is now (HEAD), not as it was at the commit.** "Still stated" means today: a copy fixed after the correction is not reported, so an old correction can be re-checked usefully. Right after a correction the two are the same.
- **`--also` searches untracked directories** such as agent memory - where the real incident's fourth copy lived.
- **A root commit removed nothing**, and that is said in `skipped`.
- **Read-only.** Git plumbing (`diff`, `ls-tree`, `cat-file --batch`); it never checks anything out.
- Every rule shown to matter: removing each of ten turns a test red (two first survived and exposed weak tests, then tightened).

## Change Log (newest first)

- [2026-09-24] ENH-ADDA-031 - the search runs over HEAD, not the tree at `--rev` · dogfooding on an older commit kept reporting a paragraph already fixed after it; "still stated" has to mean now. Test-first.
- [2026-09-24] ENH-ADDA-031 - module created from a scoped prototype · on this repo's last 40 commits: 23 hits, about half needing an edit and nearly all worth reading; the built version reproduces the prototype's count exactly. It finds the stale MSG-015 reply at 4f0c158 and, with `--also` on agent memory, the ops-dashboard copy at a7dfc94.
