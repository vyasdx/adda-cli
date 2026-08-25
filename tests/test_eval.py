# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda eval — rehydration fidelity. Load-bearing facts must be lossless."""

from pathlib import Path

from adda.evaluate import evaluate
from adda.okf import OKF, Architecture, Decision, Module, compile_okf

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "adda" / "templates" / "adda"


def test_scaffold_baseline():
    r = evaluate(compile_okf(TEMPLATES))
    assert r["load_bearing_fidelity_pct"] == 100.0   # rehydrate keeps every critical fact
    assert 0 < r["overall_fidelity_pct"] < 100        # prose/inactive intentionally dropped
    assert r["payload_reduction_pct"] > 0
    assert "module:worker" in r["dropped"]            # the planned module is dropped
    assert "domain_model" in r["dropped"]
    assert r["facts_preserved"] < r["facts_total"]


def test_full_fidelity_when_only_load_bearing():
    okf = OKF(
        project="P",
        version="1",
        constraints=["c"],
        architecture=Architecture(modules=[Module(name="a", status="active")]),
        decisions=[Decision(id="ADR-1", status="accepted")],
    )
    r = evaluate(okf)
    assert r["overall_fidelity_pct"] == 100.0
    assert r["load_bearing_fidelity_pct"] == 100.0
    assert r["dropped"] == []
