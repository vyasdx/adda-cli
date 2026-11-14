<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Stale agent instructions in public repositories (November 2026)

Agent instruction files (`AGENTS.md`, `CLAUDE.md`, `.clinerules`, Copilot instructions) tell
coding agents which files to open and which functions to call. When the code moves and the file
does not, the agent follows the file. We ran ADDA's `audit --refs` on 83 public repositories in
four rounds between 2 and 4 November 2026 to see how often that happens, and how often ADDA
itself is wrong.

**The short version:**

- Real drift is common where agent files are written fastest: large monorepos and enterprise
  repositories. Small, tightly kept files (most AI labs' own) had none.
- ADDA is not yet precise on prose it was not written for. In the last round, 47 of its 200
  findings were real (24%). The false alarms are listed below by cause, with what we changed.
- Five fixes went upstream as pull requests. None has been reviewed yet.

The fixes made during this study shipped in ADDA 0.5.7 (`pip install "adda>=0.5.7"`).
ADDA 0.5.6 and earlier behave like round 1 below.

## Method

- Shallow clones of each repository's default branch, taken 2 and 3 November 2026; the
  commits of the repositories named here are listed at the end.
- `adda audit --refs` checks that every file path and code name an instruction file cites exists
  in the repository.
- Every finding was checked against the code before it was counted as real. In rounds 1 and 2,
  each one by us. In rounds 3 and 4, each one by one of four independent reviewer agents with a
  fixed list of verdicts; we then re-checked a sample of their "real" verdicts (10 in round 3,
  9 in round 4), and all held.
- "Real" means the cited path or name does not exist in the code, and the file is wrong today.

## Results

| Round | Repositories | ADDA | Findings | Real | Precision |
|---|---|---|---|---|---|
| 1 (2 Nov) | 11 large open-source projects | 0.5.6 (PyPI) | 21 | 6 | 29% |
| 2 (2 Nov) | the same 11, same commits | `main` after three fixes | 6 | 6 | 100% |
| 3 (2 Nov) | 28: AI labs, AI tool companies, practitioners, enterprise and services, Indian product companies | `main` after two more fixes | 178 | 84 | 47% |
| 4 (3 Nov) | 44: members and watched projects of the Agentic AI Foundation | `main` after two more fixes | 200 | 47 | 24% |

Before each round's fixes, rounds 3 and 4 gave 274 findings (85 real, 31%) and 257 findings
(47 real, 18%). The fixes removed false alarms only: no real finding was lost, except one in
round 3 that a lint rule's message text now vouches for.

In round 4, 16 of the 44 repositories had no findings at all. In round 3, the four AI-lab
repositories had 3 findings between them, all false.

## Where ADDA was wrong

Precision depends on how a team writes its instruction files, so it moved from round to round.
The causes of false alarms, and what we did about each:

- **Names from outside the repository**: config keys of the agent tool itself, third-party tools
  and services, a GitHub Action, an environment variable, a path in another repository or inside
  an installed package. Partly fixed: a GitHub Action, and a name in a sentence that says it is
  upstream, in an installed package or an environment variable, are no longer checked. The rest
  is the biggest remaining class.
- **Counter-examples**: "`TRANSIENT_ERRORS`, not `RETRYABLE_EXCEPTION_TUPLE`". Fixed after "not",
  "instead of" and "rather than"; "avoid" and "never" still slip through.
- **Placeholders**: naming patterns (`BaseX`, an `async_` prefix) and API templates built on
  `Foo`/`Bar` (`CreateFooRequest`). Fixed for a name ending in a lone capital, a name right after
  "a" or "an", and Foo/Bar/Baz/Qux; others such as `xHandlers` remain.
- **HTTP routes read as paths**: a table of routes (`/api/v1/series`) in a nested `AGENTS.md` was
  checked against that folder. Fixed: a leading `/` means the repository root.
- **Paths the reader is told to create**, or hedged ("if exists"). Fixed.
- **Names that exist in forms ADDA does not read yet**: `module.func`, Go's `pkg.Symbol`. Open.

Two defects outside precision were found and fixed too: on Windows, clones with an empty git index
made ADDA report present files as missing; and the check took 18 minutes on a 68,000-file
repository (now under 4).

## What real drift looks like

The real findings fell into a few repeating shapes. The examples named here are the ones we sent
fixes for; the others are counted, not named.

- **A refactor deletes or renames code, and the instruction file stays behind.** React's
  `compiler/CLAUDE.md` described a `tryRecord()` wrapper that was removed eight months earlier.
  SAP open-ux-tools' agent file linked ESLint configs renamed from `.js` to `.mjs` in an ESM
  migration; an agent that creates the "missing" `eslint.config.js` overrides the real config,
  because ESLint looks for `.js` first.
- **A migration leaves the whole agent guide describing the old code.** Cline's `.clinerules`
  walk agents through names and paths from before its SDK migration, and use a feature that was
  removed as the worked example for adding an RPC.
- **Two PRs in flight.** DataDog's health-platform `AGENTS.md` merged the day after a rename and the
  day before a refactor, so its test pattern asserts a deprecated state and names a helper that had
  just been renamed.
- **A plan documented as done.** UiPath's troubleshoot guide says a CI gate blocks a regression;
  the gate was in a PR that was closed unmerged. The closed PR also carried the real fix, so the
  scenario generator still writes the regression the guide says is blocked.
- **Wrong from the first commit**: links to skills under a folder they never shipped in, a test
  file and classes that never existed, a rule file that was never committed.
- **Written ahead of an open PR**: a name that exists on a maintainer's branch, not on `main`.
  That is not drift yet, so it gets no fix.

Two lessons for anyone checking these files, by tool or by hand:

- **A link that resolves can still be wrong.** Two of the SAP links pointed at an old config that
  still exists but that nothing uses any more. No existence check can see that.
- **A correct fix can be made wrong by a PR in flight.** One fix we drafted would have pointed at a
  test file that an approved, open PR deletes. Check open PRs for moves and deletes of the target,
  not only for edits to the line.

## The fixes we sent

Each was checked against the code by an agent that had not seen our reasoning, revised, and checked
again, before it was sent. One pull request per repository, covering only lines we could prove from
the code. State as of 9 November 2026: all open, none reviewed yet.

| Pull request | What it fixes |
|---|---|
| [facebook/react#38096](https://github.com/facebook/react/pull/38096) | `compiler/CLAUDE.md` and the passes README: the removed `tryRecord()` wrapper, and when non-compiler exceptions are re-thrown |
| [SAP/open-ux-tools#5366](https://github.com/SAP/open-ux-tools/pull/5366) | `AGENTS.md`: config paths renamed in the ESM migration, including two links that still resolve to a superseded file |
| [DataDog/datadog-agent#59485](https://github.com/DataDog/datadog-agent/pull/59485) | `comp/healthplatform/AGENTS.md`: the deprecated issue state in its test pattern, and a renamed helper |
| [cline/cline#15526](https://github.com/cline/cline/pull/15526) | `.clinerules`: names and paths that no longer exist, with the outdated sections listed for the maintainers |
| [UiPath/skills#4386](https://github.com/UiPath/skills/pull/4386) | The scenario generator's judge settings, and three stale lines in the troubleshoot guide |

**What we did not send, and why.** Most real findings did not become pull requests:

- A single renamed path in a large repository, which a reader corrects in seconds, is not worth a
  maintainer's review.
- A repository that does not merge outside pull requests, or has had no push in months.
- A fix an open PR would make wrong, or a line that a maintainer's own open PR already rewrites.
- A repository with its own bot that audits these files.

## Reproduce

Clone a repository at the commit below, install ADDA 0.5.7 or later, and run `adda audit --refs`
in the clone. Results on a later commit will differ: that is the point of the check.

| Repository | Commit scanned |
|---|---|
| facebook/react | `76baa3b` |
| SAP/open-ux-tools | `a3884e3` |
| DataDog/datadog-agent | `1d04cf7d` |
| cline/cline | `59cce11` |
| UiPath/skills | `5796367` |
