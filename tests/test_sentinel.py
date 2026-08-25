# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Context Sentinel threshold + token-counting fallback tests (spec §6)."""

from adda.sentinel import ContextSentinel, count_tokens


def test_thresholds():
    s = ContextSentinel(100)  # limit 100 -> tokens equal the percentage
    assert s.check(0) == "OK"
    assert s.check(59) == "OK"
    assert s.check(60) == "CHECKPOINT"   # spec §6 boundary
    assert s.check(84) == "CHECKPOINT"
    assert s.check(85) == "ALERT"        # spec §6 boundary
    assert s.check(89) == "ALERT"
    assert s.check(90) == "FORCE"        # spec §6 boundary
    assert s.check(100) == "FORCE"


def test_percent():
    assert ContextSentinel(200_000).percent(100_000) == 50.0


def test_count_tokens_heuristic_fallback():
    # No model -> deterministic chars/4 heuristic; never touches the network.
    assert count_tokens("x" * 400) == (100, "heuristic")
    # A non-Claude model also uses the heuristic.
    assert count_tokens("x" * 40, model="gpt-4") == (10, "heuristic")
    # Blank input -> 0 tokens.
    assert count_tokens("   ") == (0, "heuristic")


def test_module_annotations_are_importable_on_the_declared_floor():
    """`str | None` at runtime needs 3.10+. Either the floor says 3.10, or the
    module defers annotations. Anything else is broken on a supported Python."""
    import pathlib
    import re

    import adda.sentinel

    # Plain-text read on purpose: tomllib is 3.11+, and this test must run on
    # the 3.10 floor it is guarding.
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    floor = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8")).group(1)
    src = pathlib.Path(adda.sentinel.__file__).read_text(encoding="utf-8")
    uses_pep604 = "str | None" in src
    defers = "from __future__ import annotations" in src
    # Both halves of BUG-ADDA-005 are intended together, so assert them
    # SEPARATELY. A single `or`-chained assertion is satisfied by the floor
    # alone and silently stops guarding the future-import.
    if uses_pep604:
        assert defers, (
            "sentinel.py uses PEP 604 unions (`str | None`) in annotations, so it "
            "must carry `from __future__ import annotations` — without it the module "
            "raises TypeError at import on Python 3.9."
        )
    assert floor.startswith(">=3.10"), (
        f"requires-python must be '>=3.10' (got {floor!r}) — that is the lowest "
        "version this package has actually been tested against."
    )
