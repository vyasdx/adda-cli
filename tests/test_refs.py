# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda audit --refs: a code name a doc cites must still exist somewhere in the code.

Ancestry sees a doc nobody touched. It cannot see a doc touched alongside its code
but touched wrongly (ADR-0010). These tests pin the deterministic slice of that gap
the refs rule catches, and - just as important - the cases it must NOT flag. A
checker that cries wolf teaches its users to stop reading it.
"""

import json

from typer.testing import CliRunner

from adda.cli import app
from adda.modulemap import MAP_FILENAME
from adda.refs import extract_refs, refs_report

runner = CliRunner()


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _project(root, doc_text, code_text="def compare_commits():\n    pass\n", extra=None):
    """One mapped module: src/pkg/core.py documented by docs/modules/core.md."""
    (root / "adda").mkdir(parents=True, exist_ok=True)
    (root / "adda" / MAP_FILENAME).write_text(
        json.dumps({"map": {"src/pkg/core.py": "docs/modules/core.md"}, "exempt": []}),
        encoding="utf-8",
    )
    _write(root, "src/pkg/__init__.py", "")
    _write(root, "src/pkg/core.py", code_text)
    _write(root, "docs/modules/core.md", doc_text)
    for rel, text in (extra or {}).items():
        _write(root, rel, text)


def _missing(findings):
    return sorted(f["ref"] for f in findings if f["issue"] == "ref missing")


# --- the rule itself -------------------------------------------------------


def test_cited_name_that_exists_is_not_flagged(tmp_path):
    _project(tmp_path, "# core\n\nStaleness is `compare_commits`.\n")
    findings, skipped, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == [] and skipped == []
    assert stats == {"docs": 1, "refs": 1}


def test_cited_name_deleted_from_code_is_flagged_with_its_line(tmp_path):
    _project(tmp_path, "# core\n\nStaleness is `is_strictly_later`.\n")
    findings, _, _ = refs_report(tmp_path, tmp_path / "adda")
    assert _missing(findings) == ["is_strictly_later"]
    (f,) = findings
    assert f["severity"] == "medium"
    assert f["item"] == "docs/modules/core.md:3"


def test_call_form_is_normalised(tmp_path):
    _project(tmp_path, "Call `compare_commits()`, not `gone_function()`.\n")
    findings, _, stats = refs_report(tmp_path, tmp_path / "adda")
    assert _missing(findings) == ["gone_function"]
    assert stats["refs"] == 2


def test_regression_rf_adda_005_invariant_naming_a_deleted_function(tmp_path):
    """The real incident, verbatim in shape: an invariant still naming
    `_source_files` after it was deleted the same day. Both files were committed
    together, so ancestry called the doc current and a human had to find it."""
    doc = (
        "# `audit`\n\n## Invariants\n\n"
        "- Source discovery goes through `_source_files`, which globs the tree.\n\n"
        "## Change Log (newest first)\n\n"
        "- BUG-ADDA-013 - `_source_files` deleted; discovery now imported from `sync`.\n"
    )
    _project(tmp_path, doc, code_text="from adda.sync import source_roots\n")
    findings, _, _ = refs_report(tmp_path, tmp_path / "adda")
    # Flagged once - in the live Invariants section, not in the Change Log.
    assert _missing(findings) == ["_source_files"]
    assert findings[0]["item"] == "docs/modules/core.md:5"


# --- what it must NOT flag (each one a false positive found while prototyping) ---


def test_change_log_may_name_code_that_no_longer_exists(tmp_path):
    doc = (
        "# core\n\n`compare_commits` decides staleness.\n\n"
        "## Change Log (newest first)\n\n"
        "- replaced the removed `is_strictly_later`\n\n"
        "### nested note\n\n- also dropped `old_helper`\n"
    )
    _project(tmp_path, doc)
    findings, _, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == []
    assert stats["refs"] == 1  # history is not counted as checked, either


def test_a_later_section_after_the_change_log_is_checked_again(tmp_path):
    doc = "## Changelog\n\n- `old_helper`\n\n## Notes\n\n- uses `gone_function`\n"
    _project(tmp_path, doc)
    findings, _, _ = refs_report(tmp_path, tmp_path / "adda")
    assert _missing(findings) == ["gone_function"]


def test_builtins_and_keywords_are_not_flagged(tmp_path):
    _project(tmp_path, "Raises `KeyError`; returns `None`; see `NotImplementedError`.\n")
    findings, _, _ = refs_report(tmp_path, tmp_path / "adda")
    assert findings == []


def test_name_defined_in_another_module_counts(tmp_path):
    _project(
        tmp_path,
        "Imported from `source_roots` in sync.\n",
        extra={"src/pkg/sync.py": "def source_roots():\n    return []\n"},
    )
    assert refs_report(tmp_path, tmp_path / "adda")[0] == []


def test_name_that_only_exists_in_tests_counts(tmp_path):
    _project(
        tmp_path,
        "Exercised through `CliRunner` in the suite.\n",
        extra={"tests/test_core.py": "from typer.testing import CliRunner\n"},
    )
    assert refs_report(tmp_path, tmp_path / "adda")[0] == []


def test_fenced_code_blocks_are_examples_not_claims(tmp_path):
    doc = "# core\n\n```python\n`not_a_real_name` = maybe_later()\n```\n\n`compare_commits`\n"
    _project(tmp_path, doc)
    findings, _, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == [] and stats["refs"] == 1


def test_spans_that_are_not_code_names_are_ignored(tmp_path):
    doc = (
        "Returns `stale` or `current`; run with `--json`; writes `okf.json`; "
        "reads `MODULE_MAP.json`; path `src/pkg/core.py`; two words `a b`.\n"
    )
    _project(tmp_path, doc)
    findings, _, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == [] and stats["refs"] == 0


def test_extract_refs_reports_line_numbers_and_skips_history():
    text = "# t\n`alpha_one`\n## Change Log\n`beta_two`\n## After\n`gamma_three()`\n"
    assert extract_refs(text) == [(2, "alpha_one"), (6, "gamma_three")]


# --- cannot tell is reported, never passed (ADR-0007) ----------------------


def test_doc_that_cannot_be_decoded_is_skipped_not_passed(tmp_path):
    _project(tmp_path, "placeholder\n")
    (tmp_path / "docs/modules/core.md").write_bytes(b"\xff\xfe`gone_function`\n")
    findings, skipped, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == []
    assert any("could not be read" in s for s in skipped)
    assert stats["docs"] == 0


def test_no_code_at_all_is_skipped_rather_than_flagging_every_ref(tmp_path):
    _project(tmp_path, "`compare_commits` and `gone_function`\n")
    (tmp_path / "src/pkg/core.py").unlink()
    (tmp_path / "src/pkg/__init__.py").unlink()
    findings, skipped, _ = refs_report(tmp_path, tmp_path / "adda")
    assert findings == []
    assert any("no source" in s for s in skipped)


def test_missing_doc_is_left_to_audit_rule_one(tmp_path):
    _project(tmp_path, "`gone_function`\n")
    (tmp_path / "docs/modules/core.md").unlink()
    findings, skipped, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == [] and skipped == [] and stats["docs"] == 0


# --- CLI: opt-in, and plain `audit` is unchanged ---------------------------


def test_plain_audit_ignores_refs_so_existing_ci_is_unaffected(tmp_path):
    _project(tmp_path, "`gone_function`\n")
    res = runner.invoke(app, ["audit", str(tmp_path), "--json"])
    report = json.loads(res.stdout)
    assert not any(f["issue"] == "ref missing" for f in report["findings"])
    assert "refs" not in report


def test_audit_refs_reports_missing_name_and_exits_one(tmp_path):
    _project(tmp_path, "# core\n\nuses `gone_function`\n")
    res = runner.invoke(app, ["audit", str(tmp_path), "--refs"])
    assert res.exit_code == 1
    assert "ref missing" in res.stdout
    assert "gone_function" in res.stdout
    assert "docs/modules/core.md:3" in res.stdout


def test_audit_refs_states_how_much_it_checked(tmp_path):
    """An empty result must look empty: say how many names were checked, so a
    rule that checked nothing can never read as a clean pass."""
    _project(tmp_path, "`compare_commits`\n")
    res = runner.invoke(app, ["audit", str(tmp_path), "--refs"])
    assert "1 code name(s) cited in 1 doc(s)" in res.stdout


def test_audit_refs_json_carries_findings_and_counts(tmp_path):
    _project(tmp_path, "`gone_function`\n")
    res = runner.invoke(app, ["audit", str(tmp_path), "--refs", "--json"])
    report = json.loads(res.stdout)
    assert res.exit_code == 1
    assert report["refs"] == {"docs": 1, "refs": 1}
    (f,) = [f for f in report["findings"] if f["issue"] == "ref missing"]
    assert f["ref"] == "gone_function"
