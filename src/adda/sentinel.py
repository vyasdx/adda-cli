# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Context Sentinel — token-usage gauge that says WHEN to checkpoint (spec §6/§7).

Token counting uses the Anthropic SDK's `messages.count_tokens` for Claude-model
accuracy and falls back to a chars/4 heuristic when the SDK, an API key, or a
Claude model isn't available (spec §4). The gauge itself is provider-agnostic.
"""
from __future__ import annotations

# Thresholds from spec §6 (percent of the model's context window).
CHECKPOINT = 60
ALERT = 85
FORCE = 90

# Known context windows. Anything unlisted falls back to DEFAULT_LIMIT; callers
# can always override with an explicit --limit.
# ponytail: small static map, not a live Models-API lookup — upgrade path is to
# query the Anthropic Models API if these drift.
DEFAULT_LIMIT = 200_000
MODEL_LIMITS = {
    "claude-opus-4-8": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-haiku-4-5": 200_000,
}


class ContextSentinel:
    """Maps a token count to OK / CHECKPOINT / ALERT / FORCE (spec §7 pseudocode)."""

    def __init__(self, limit: int = DEFAULT_LIMIT):
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.limit = limit

    def percent(self, tokens: int) -> float:
        return (tokens / self.limit) * 100

    def check(self, tokens: int) -> str:
        usage = self.percent(tokens)
        if usage >= FORCE:
            return "FORCE"
        if usage >= ALERT:
            return "ALERT"
        if usage >= CHECKPOINT:
            return "CHECKPOINT"
        return "OK"


def limit_for(model: str | None) -> int:
    """Context window for a model, or the default when unknown."""
    return MODEL_LIMITS.get(model or "", DEFAULT_LIMIT)


def count_tokens(text: str, model: str | None = None) -> tuple[int, str]:
    """Count tokens in `text`. Returns (count, method).

    Uses the Anthropic SDK for Claude models when an API key is available;
    otherwise falls back to a chars/4 heuristic. Never raises — counting is a
    best-effort gauge input, so any SDK/network/auth failure degrades gracefully.
    """
    if not text.strip():
        return 0, "heuristic"
    if model and model.startswith("claude"):
        try:
            from anthropic import Anthropic

            client = Anthropic()  # resolves ANTHROPIC_API_KEY from the environment
            resp = client.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": text}],
            )
            return resp.input_tokens, "anthropic"
        except Exception:
            pass  # no key / offline / non-counting model -> heuristic
    return len(text) // 4, "heuristic"
