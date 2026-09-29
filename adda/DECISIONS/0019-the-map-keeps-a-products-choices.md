<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# 0019 — The map keeps a product's choices

Date: 2026-09-29
Status: accepted
Issue: ENH-ADDA-034
Amends: ADR-0013

## Context

ADR-0013 made `sync --map` carry over every key it does not generate, and noted
that hand-edits to `map` and `exempt` were still overwritten - loudly, so
accepted at the time.

A trial on a real product repository changed that. It keeps 60 module docs,
named by hand (`docs/modules/agent-runner.md`). `sync --map` generated 119
mirrored paths and none of them matched. The only way to adopt ADDA there is to
point each entry at the doc that already exists - and the next routine
regenerate threw every one of those choices away. With the fleet rollout
decided, that is not an edge case; it is most of the fleet.

## Decision

- **An existing map entry is kept while its code exists.** Only code the map
  has never seen gets a generated, mirrored path. Entries for deleted code are
  dropped, which is what a regenerate is for.
- **A hand-written exempt pattern is kept, and wins over an older map entry.**
  The exempt list is a product's written-down debt register during a rollout;
  adding a pattern must take those files out of the map, not be silently
  outranked by entries a first regenerate wrote. An exact exempt path whose file
  is gone is dropped; a pattern is kept even when it matches nothing yet.
- **To start over, delete the file.** No flag - the escape hatch is plain.

## Consequences

- ADR-0013's note that `map`/`exempt` hand-edits are overwritten no longer
  holds. On a repository whose docs mirror the source, like this one, nothing
  changes: the regenerate still produces the same map.
- On the trial repository, a hand-pointed entry and two exempt patterns
  survived a regenerate, and the exempted pages left the map (119 to 97).
- A wrong hand-chosen target now persists. It is not hidden: `audit` reports
  the doc as missing or stale like any other.
