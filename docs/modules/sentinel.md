<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# `sentinel` - `src/adda/sentinel.py`

Last verified: 2026-08-25

**Purpose** - Context Sentinel - the token-usage gauge that answers *when* to checkpoint.

## Public surface

`ContextSentinel(limit)` with `.percent(tokens)` / `.check(tokens)` · `limit_for(model)` · `count_tokens(text, model)` returning `(tokens, method)`

## Thresholds (spec section 6, percent of the context window)

`OK` under 60 · `CHECKPOINT` at 60 · `ALERT` at 85 · `FORCE` at 90

## Invariants

- **This is ADDA's only outbound API call, and it is optional.** `count_tokens` uses the Anthropic SDK's `messages.count_tokens` for Claude-model accuracy and falls back to a chars/4 heuristic when the SDK, an API key, or a Claude model is absent. ADDA must stay fully usable offline. (Re-confirmed 2026-08-07: no generative call, ~$0 spend, no vendor lock-in.)
- It counts tokens; it never runs inference. No generative call belongs here.
- `ContextSentinel` rejects a non-positive `limit`.
- **`MODEL_LIMITS` is a small static map and will drift** as models ship. `--limit` is the escape hatch; the upgrade path is the Anthropic Models API (already flagged with a `ponytail:` comment in-file).
- Anthropic SDK work here goes through the `claude-api` skill - do not hand-write SDK calls.

## Change Log (newest first)

- [2026-08-25] BUG-ADDA-008 — dropped an internal message-ID reference from the outbound-call invariant · this file ships in the public export, and the reference leaked the company's internal operating name past a marker scan that could not see it.
- [2026-08-18] BUG-ADDA-005 — deferred annotations + `requires-python` raised to 3.10 · `str | None` raised TypeError at import on the declared 3.9 floor.
- [2026-08-18] ENH-ADDA-006 - module doc created (backfill; code unchanged) · the anti-drift rule requires a doc per code path and `docs/modules/` was empty.
