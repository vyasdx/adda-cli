# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Compile the shipped scaffold and assert the OKF comes out as expected."""

from pathlib import Path

from adda.okf import OKF, OKF_VERSION, active_decisions, active_modules, compile_okf

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "adda" / "templates" / "adda"


def test_compile_scaffold():
    okf = compile_okf(TEMPLATES)
    assert isinstance(okf, OKF)
    assert okf.okf_version == "0.2"
    assert okf.project == "My Project"
    assert okf.version == "0.1.0"

    # modules parse in order, with status
    names = [m.name for m in okf.architecture.modules]
    assert names == ["core", "api", "worker"]
    statuses = {m.name: m.status for m in okf.architecture.modules}
    assert statuses["worker"] == "planned"

    # rehydrate-relevant filters
    assert [m.name for m in active_modules(okf)] == ["core", "api"]

    # constraints + decisions + free-text + state
    assert len(okf.constraints) == 2
    assert okf.decisions[0].id == "ADR-0001"
    assert okf.decisions[0].status == "accepted"
    assert active_decisions(okf) == okf.decisions
    assert "User" in okf.architecture.domain_model
    assert "/health" in okf.architecture.api_contracts
    assert okf.state.updated == "2026-06-25"
    assert "scaffold" in okf.state.summary.lower()


def test_empty_overview_does_not_swallow_constraints(tmp_path):
    # Blank overview paragraph (H1 immediately followed by `## Constraints`) must
    # NOT capture the Constraints section into architecture.overview.
    adda = tmp_path / "adda"
    adda.mkdir()
    (adda / "VERSION.md").write_text("project: P\nversion: 1.0\n", encoding="utf-8")
    (adda / "ARCHITECTURE.md").write_text(
        "# Architecture\n\n## Constraints\n- c1\n\n## Modules\n- core: logic (active)\n",
        encoding="utf-8",
    )
    okf = compile_okf(adda)
    assert okf.architecture.overview == ""
    assert okf.constraints == ["c1"]
    assert [m.name for m in okf.architecture.modules] == ["core"]


def test_module_path_parsed():
    from adda.okf import _parse_module

    mod = _parse_module("core: Core logic (active) [src/core]")
    assert (mod.name, mod.status, mod.path) == ("core", "active", "src/core")
    bare = _parse_module("worker (planned)")
    assert (bare.name, bare.status, bare.path) == ("worker", "planned", "")


def test_okf_schema_doc_in_sync():
    """OKF_SCHEMA.md must document the current version, fields, and models (anti-drift)."""
    doc = (Path(__file__).resolve().parents[1] / "OKF_SCHEMA.md").read_text(encoding="utf-8")
    schema = OKF.model_json_schema()
    assert OKF_VERSION in doc
    for field in schema["properties"]:
        assert field in doc, f"top-level field '{field}' missing from OKF_SCHEMA.md"
    for model in schema["$defs"]:
        assert model in doc, f"model '{model}' missing from OKF_SCHEMA.md"
    assert "path" in doc  # the v0.2 addition
