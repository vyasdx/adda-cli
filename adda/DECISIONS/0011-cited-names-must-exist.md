<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0011 — A deterministic slice of the "updated wrongly" gap is checkable

Date: 2026-09-24
Status: accepted
Issue: ENH-ADDA-027
Amends: ADR-0010

## Context

ADR-0010 published the boundary of ancestry-based staleness: `audit` sees a doc
nobody touched, never a doc touched alongside its code but touched wrongly. It
called that gap "not patchable", because judging whether a doc is *wrong* means
understanding what it claims — a model call, which ADR-0003 rules out.

That holds for the gap as a whole, but not for all of it. The incident ADR-0010
cites, RF-ADDA-005, was two docs, and they failed differently. One invariant
named `_source_files` after it had been deleted — and an earlier doc (ENH-ADDA-007)
had done the same with the removed `is_strictly_later`. Those needed no
understanding to catch, only noticing that a name the doc cites exists nowhere in
the code. The other RF-ADDA-005 doc *omitted* a function from its public surface.
A check on the names a doc cites cannot see a name it never cited, so that half
stays with the reviewer.

A prototype run against ADDA's own module docs checked 47 cited names and
flagged 3 — all of them false positives. Two sat in Change Log sections, which
exist to name code that is gone. The third was a builtin. Those two Change Log
lines were, in fact, the written records of the two incidents above.

## Decision

Add `refs`: every code name a mapped doc cites must still appear somewhere in
the source. Deterministic, offline, no model call.

- **It narrows ADR-0010's boundary; it does not remove it.** It catches a doc
  that names code which no longer exists. It cannot catch a doc that leaves a
  name out, nor one whose names all exist but whose claims about them are false.
  The README keeps stating the remaining gap.
- **Opt-in, as `audit --refs`.** ADR-0010 asks that a check aimed at wrong docs
  be a clearly separate opt-in surface rather than a change to `audit`. Plain
  `audit` keeps its five rules and exit contract, so no pipeline already running
  it changes. A new rule has a new false-positive profile, and it earns default
  status by running clean first.
- **False positives are designed out, not tolerated.** A checker that cries
  wolf teaches users to stop reading it, which costs more than the misses it
  prevents. Each exclusion came from the prototype: history sections, builtins,
  names defined in other modules or tests, fenced examples, and spans that are
  not code names. Undecidable input — no source at all, an undecodable doc — is
  reported under `[skipped]`, never counted as a pass.
- **It always states how much it checked**, so an empty result can never be
  mistaken for a clean one.

## Consequences

- ADDA's own docs pass: 36 cited names across 11 docs, 0 findings.
- The README's "What staleness detection cannot see" narrows: a carelessly
  touched doc is now caught when it names code that no longer exists. A doc that
  omits a name, or makes false claims about names that do exist, still needs a
  reader.
- Existence is a whole-word match anywhere in the code, including comments and
  strings. A deleted function whose name survives in a comment reads as present.
  That is the chosen trade: a miss here is cheaper than a false alarm.
- Paths, flags and dotted names are out of scope for this version. Checking them
  in instruction files is the natural next step, and a separate decision.
