# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Optional headroom-ai wrapper (spec §14).

headroom-ai is NOT a hard dependency. If it is importable, `compress_text` runs
its `compress(messages, model=...)` and returns the optimized text; otherwise it
returns the input unchanged. Either way ADDA keeps working.

ponytail: headroom compression is LOSSY (its SmartCrusher drops low-signal JSON
items), so this is wired behind an opt-in `--compress` flag only — never the
default. Default `export`/`rehydrate` always emit faithful, valid OKF. The upgrade
path, if a guaranteed-reversible payload is ever needed, is headroom's CCR mode.
"""

from typing import Optional


def available() -> bool:
    """True if headroom-ai can be imported."""
    try:
        import headroom  # noqa: F401

        return True
    except Exception:
        return False


def compress_text(text: str, model: Optional[str] = None) -> tuple[str, dict]:
    """Best-effort compress `text`. Returns (text_out, info).

    info["applied"] is False (and text_out == text) whenever headroom is absent
    or anything goes wrong — compression never breaks the caller.
    """
    try:
        from headroom import compress as _compress
    except Exception:
        return text, {"applied": False, "reason": "headroom-ai not installed"}

    try:
        messages = [{"role": "user", "content": text}]
        # model only steers headroom's internal tokenizer; ADDA stays provider-agnostic.
        result = _compress(messages, model=model or "gpt-4o")
        out = result.messages[-1].get("content") if result.messages else None
        if not isinstance(out, str) or not out:
            return text, {"applied": False, "reason": "unexpected headroom output shape"}
        return out, {
            "applied": True,
            "tokens_saved": getattr(result, "tokens_saved", None),
            "compression_ratio": getattr(result, "compression_ratio", None),
        }
    except Exception as exc:  # any headroom failure -> safe pass-through
        return text, {"applied": False, "reason": f"headroom error: {exc}"}
