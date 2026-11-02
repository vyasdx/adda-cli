<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0028 — A cited span counts only when its own sentence claims it exists here

Date: 2026-11-02
Status: accepted
Issue: BUG-ADDA-039
Relates to: ADR-0011, ADR-0012

## Context

`--refs` treated every code-shaped backticked span on a live line as a claim that the name or
path exists in the repository. ADDA's own and the fleet's files were written to be checked, so
that held. The first run on 11 public repositories (ENH-ADDA-056, `docs/case-study-2026-11.md`)
showed outsiders' prose does not: 15 of 21 findings were spans the text never claimed exist -
another project's names, counter-examples, naming patterns, and paths hedged or still to be
created. A checker whose false positives outnumber its findings disproves itself.

## Decision

A span is checked only when its sentence claims it. Skipped:

- **The text of a link to a URL** - `[`rome_formatter`](https://...)` names another project's thing.
- **A sentence that puts it elsewhere or hedges it** - "installed package", "source repository",
  "upstream", "frontmatter", "env var", "if exists", "if present", "can be added/created".
- **A span right after "a"/"an", "not", "instead of", "rather than", or a capitalised
  possessive** - a hypothetical (`a make_error() helper`), a counter-example (`X, not Y`), or
  someone else's (`Corridor's analyzePlan`).
- **A name ending in a lone capital** (`BaseX`) - a pattern, not a name.
- **`actions/<name>`** - a GitHub Action, not a path.

Scope is the sentence, not the line, so one hedge does not excuse a whole paragraph line.

## Consequences

- Every rule has a test built from the real line it came from, and the two real findings of the
  study (React's `tryRecord`, Deno's `find_descendant_pids`) have a test that they still flag.
- It misses more: a real name after "a" or in a sentence mentioning "upstream" is no longer
  checked. That is the trade the rule has made since ADR-0011 - a false alarm costs more than a miss.
- "optional" was tried as a hedge and dropped: "an optional attribute `is_offer`" is a real claim
  (an existing BUG-ADDA-026 test caught it).
