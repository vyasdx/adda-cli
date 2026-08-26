# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda eval — rehydration fidelity. Load-bearing facts must be lossless."""

import json
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


def test_eval_refuses_to_score_an_unauthored_scaffold(tmp_path):
    """BUG-ADDA-021: `adda eval` on a fresh `init` reported a confident number.

    "58.3% overall, 100.0% load-bearing" computed entirely from template
    placeholder text — and that figure is where the README's long-standing
    stale 58% came from. A fidelity score over memory nobody wrote is not a low
    score, it is not a score at all.
    """
    from typer.testing import CliRunner

    from adda.cli import app

    r = CliRunner()
    assert r.invoke(app, ["init", str(tmp_path)]).exit_code == 0

    res = r.invoke(app, ["eval", str(tmp_path), "--json"])
    assert res.exit_code == 0
    report = json.loads(res.stdout)
    assert report["overall_fidelity_pct"] is None
    assert report["load_bearing_fidelity_pct"] is None
    assert "VERSION.md" in report["unauthored_template_files"]

    human = r.invoke(app, ["eval", str(tmp_path)])
    assert "n/a" in human.stdout


def test_eval_scores_partly_authored_memory_but_says_what_is_missing(tmp_path):
    """One authored file is enough to score — and the rest must still be named.

    Silently counting placeholder text as memory is what produced the stale
    number; the score is only honest next to the list of files still unwritten.
    """
    from typer.testing import CliRunner

    from adda.cli import app

    r = CliRunner()
    r.invoke(app, ["init", str(tmp_path)])
    (tmp_path / "adda" / "ARCHITECTURE.md").write_text(
        "# Architecture\n\n## Constraints\n- Must stay offline\n\n"
        "## Modules\n- core (active) [src/core]\n",
        encoding="utf-8",
    )
    report = json.loads(r.invoke(app, ["eval", str(tmp_path), "--json"]).stdout)
    assert report["overall_fidelity_pct"] is not None
    assert "ARCHITECTURE.md" not in report["unauthored_template_files"]
    assert "VERSION.md" in report["unauthored_template_files"]
    assert "[partial]" in r.invoke(app, ["eval", str(tmp_path)]).stdout
