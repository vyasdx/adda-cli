# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""headroom wrapper must degrade gracefully (no hard dependency)."""

from adda.compress import available, compress_text


def test_compress_graceful_fallback():
    text = '{"okf_version": "0.1", "project": "x"}'
    out, info = compress_text(text)
    assert isinstance(out, str)  # never crashes, always returns text
    if not available():
        # headroom-ai absent -> exact pass-through
        assert out == text
        assert info["applied"] is False
        assert "not installed" in info["reason"]
