# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda audit --refs: a code name a doc cites must still exist somewhere in the code.

Ancestry sees a doc nobody touched. It cannot see a doc touched alongside its code
but touched wrongly (ADR-0010). These tests pin the deterministic slice of that gap
the refs rule catches, and - just as important - the cases it must NOT flag. A
checker that cries wolf teaches its users to stop reading it.
"""

import json
import subprocess

from typer.testing import CliRunner

from adda.cli import app
from adda.modulemap import MAP_FILENAME
from adda.refs import extract_paths, extract_refs, instructions_report, refs_report

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


def test_line_saying_a_name_is_gone_is_not_a_claim_that_it_exists(tmp_path):
    # Same principle as a Change Log, one line wide: naming code to say it was
    # removed is accurate, not drift.
    _project(tmp_path, "# core\n\n`old_helper` was removed; use `compare_commits`.\n")
    findings, _, stats = refs_report(tmp_path, tmp_path / "adda")
    assert findings == [] and stats["refs"] == 0


# --- ENH-ADDA-024: instruction files cite paths and names for the whole repo ---
#
# Each test below is one of the 30 naive hits from prototyping this against
# ADDA's own AGENTS.md, CLAUDE.md and README.md - every one a false positive.


def _repo(root, files, instructions):
    for rel, text in files.items():
        _write(root, rel, text)
    for rel, text in instructions.items():
        _write(root, rel, text)


def _path_issues(findings):
    return sorted(f["ref"] for f in findings if f["issue"] == "path missing")


def test_instruction_file_citing_an_existing_path_is_clean(tmp_path):
    _repo(tmp_path, {"src/app.py": "x = 1\n"}, {"AGENTS.md": "Code lives in `src/app.py`.\n"})
    findings, skipped, stats = instructions_report(tmp_path)
    assert findings == [] and skipped == []
    assert stats == {"files": 1, "refs": 0, "paths": 1, "unresolved": 0}


def test_missing_path_inside_the_repo_is_flagged_with_its_line(tmp_path):
    _repo(tmp_path, {"src/app.py": "x = 1\n"}, {"CLAUDE.md": "# rules\n\nRun `src/gone.py` first.\n"})
    findings, _, _ = instructions_report(tmp_path)
    assert _path_issues(findings) == ["src/gone.py"]
    assert findings[0]["item"] == "CLAUDE.md:3" and findings[0]["severity"] == "medium"


def test_path_into_another_repository_is_unresolved_not_missing(tmp_path):
    _repo(tmp_path, {"src/app.py": "x = 1\n"}, {"AGENTS.md": "Synced from `OtherRepo/specs/RULES.md`.\n"})
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["unresolved"] == 1 and stats["paths"] == 0


def test_brace_list_is_expanded_and_each_member_checked(tmp_path):
    _repo(
        tmp_path,
        {"src/pkg/cli.py": "", "src/pkg/okf.py": ""},
        {"CLAUDE.md": "Modules: `src/pkg/{cli,okf,hook}.py`.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert _path_issues(findings) == ["src/pkg/hook.py"]
    assert stats["paths"] == 3


def test_leading_slash_means_repo_root_not_filesystem_root(tmp_path):
    _repo(tmp_path, {"adda/ARCHITECTURE.md": "# a\n"}, {"CLAUDE.md": "Read `/adda/ARCHITECTURE.md` first.\n"})
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["paths"] == 1


def test_globs_and_placeholders_are_not_paths(tmp_path):
    _repo(
        tmp_path,
        {"docs/modules/a.md": "", "src/app.py": ""},
        {"AGENTS.md": "Update `docs/modules/*.md` and `log/<today>.md`.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["paths"] == 0 and stats["unresolved"] == 0


def test_slash_commands_and_slashed_words_do_not_resolve_so_are_not_flagged(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {"README.md": "Use `/compact` or `/clear`; score `n/a`.\n"})
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["unresolved"] == 3


def test_path_named_to_say_it_is_retired_is_not_flagged(tmp_path):
    _repo(
        tmp_path,
        {"notes/live.md": ""},
        {"AGENTS.md": "The old `notes/feed.md` is **RETIRED** - ignore it.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["paths"] == 0


def test_generated_gitignored_file_is_not_missing(tmp_path):
    # It exists on a working machine and not on a clean CI checkout; the answer
    # must be the same in both places.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _repo(
        tmp_path,
        {".gitignore": "out.json\n", "src/app.py": ""},
        {"CLAUDE.md": "`src/out.json` is generated; regenerate it with the build.\n"},
    )
    _write(tmp_path, ".gitignore", "src/out.json\n")
    findings, _, _ = instructions_report(tmp_path)
    assert findings == []


def test_case_mismatch_is_flagged_on_every_platform(tmp_path):
    # Passes on a case-insensitive disk, fails on Linux CI. Exact-case matching
    # makes both give the same answer.
    _repo(tmp_path, {"Docs/guide.md": "# g\n"}, {"README.md": "See `Docs/Guide.md`.\n"})
    findings, _, _ = instructions_report(tmp_path)
    assert _path_issues(findings) == ["Docs/Guide.md"]


def test_code_names_in_instruction_files_are_checked_too(tmp_path):
    _repo(
        tmp_path,
        {"src/app.py": "def build_index():\n    pass\n"},
        {"AGENTS.md": "Call `build_index()`, never `rebuild_all()`.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert sorted(f["ref"] for f in findings if f["issue"] == "ref missing") == ["rebuild_all"]
    assert stats["refs"] == 2


def test_only_conventional_instruction_files_are_read(tmp_path):
    _repo(
        tmp_path,
        {"src/app.py": "", "NOTES.md": "`src/gone.py`\n"},
        {".github/copilot-instructions.md": "`src/also_gone.py`\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert _path_issues(findings) == ["src/also_gone.py"]
    assert stats["files"] == 1


def test_repo_with_no_instruction_files_checks_nothing_and_says_so(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {})
    findings, skipped, stats = instructions_report(tmp_path)
    assert findings == [] and skipped == []
    assert stats == {"files": 0, "refs": 0, "paths": 0, "unresolved": 0}


def test_paths_in_fenced_examples_are_not_checked(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {"README.md": "```bash\nrun `src/gone.py`\n```\n"})
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["paths"] == 0


def test_extract_paths_expands_braces_and_normalises_root_slash():
    text = "`/src/{a,b}.py` and `docs/*.md` and `x/<n>.md`\n## Change Log\n`src/old.py`\n"
    assert extract_paths(text) == [(1, "src/a.py"), (1, "src/b.py")]


def test_audit_refs_reports_instruction_files_separately(tmp_path):
    _project(tmp_path, "`compare_commits`\n")
    _write(tmp_path, "AGENTS.md", "# agents\n\nSee `src/pkg/core.py` and `src/pkg/gone.py`.\n")
    res = runner.invoke(app, ["audit", str(tmp_path), "--refs"])
    assert res.exit_code == 1
    assert "path missing" in res.stdout and "AGENTS.md:3" in res.stdout
    assert "2 path(s) in 1 instruction file(s)" in res.stdout


def test_audit_refs_json_carries_instruction_stats_and_plain_audit_does_not(tmp_path):
    _project(tmp_path, "`compare_commits`\n")
    _write(tmp_path, "AGENTS.md", "`src/pkg/core.py`\n")
    with_refs = json.loads(runner.invoke(app, ["audit", str(tmp_path), "--refs", "--json"]).stdout)
    assert with_refs["instructions"] == {"files": 1, "refs": 0, "paths": 1, "unresolved": 0}
    plain = json.loads(runner.invoke(app, ["audit", str(tmp_path), "--json"]).stdout)
    assert "instructions" not in plain


def test_listing_the_conventional_instruction_filenames_is_not_a_claim_they_exist(tmp_path):
    # Found by dogfooding: ADDA's own README lists the files the check reads,
    # and `.github/` exists (for workflows) while the Copilot file does not.
    _repo(
        tmp_path,
        {".github/workflows/ci.yml": "on: push\n", "src/app.py": ""},
        {"README.md": "Reads `AGENTS.md`, `GEMINI.md` and `.github/copilot-instructions.md` when present.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert findings == []
    assert stats["unresolved"] == 3 and stats["paths"] == 0


# --- BUG-ADDA-026: names the doc's own example defines ----------------------


def test_name_defined_in_the_docs_own_example_is_described_not_claimed(tmp_path):
    # fastapi's README: a fenced model defines `is_offer`, prose then explains it.
    readme = (
        "```Python\nclass Item(BaseModel):\n    is_offer: bool | None = None\n```\n\n"
        "* Check that it has an optional attribute `is_offer`.\n"
    )
    _repo(tmp_path, {"src/app.py": "x = 1\n"}, {"README.md": readme})
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["refs"] == 1


def test_name_the_example_only_uses_is_still_checked(tmp_path):
    # A stale example calling deleted code must not excuse the prose citing it.
    readme = "```python\nresult = old_helper()\n```\n\nCall `old_helper()` first.\n"
    _repo(tmp_path, {"src/app.py": "x = 1\n"}, {"README.md": readme})
    assert _missing(instructions_report(tmp_path)[0]) == ["old_helper"]


def test_module_doc_example_definitions_count_too(tmp_path):
    doc = "```python\ndef make_widget():\n    ...\n```\n\n`make_widget()` returns a widget.\n"
    _project(tmp_path, doc)
    findings, _, _ = refs_report(tmp_path, tmp_path / "adda")
    assert findings == []


# --- ENH-ADDA-028: files a project names itself ----------------------------


def test_configured_instruction_file_is_checked_like_the_conventional_ones(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {"intent.md": "# intent\n\nBuild `src/gone.py`.\n"})
    assert instructions_report(tmp_path)[0] == []  # not conventional: unread by default
    findings, _, stats = instructions_report(tmp_path, ["intent.md"])
    assert [(f["item"], f["ref"]) for f in findings] == [("intent.md:3", "src/gone.py")]
    assert stats["files"] == 1


def test_configured_file_that_does_not_exist_is_reported_not_passed(tmp_path):
    # A typo in the config must not read as "checked, all clean".
    _repo(tmp_path, {"src/app.py": ""}, {})
    findings, skipped, stats = instructions_report(tmp_path, ["docs/intent.md"])
    assert findings == [] and stats["files"] == 0
    assert any("docs/intent.md" in s for s in skipped)


def test_file_both_conventional_and_configured_is_read_once(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {"AGENTS.md": "`src/gone.py`\n"})
    findings, _, stats = instructions_report(tmp_path, ["AGENTS.md"])
    assert stats["files"] == 1 and _path_issues(findings) == ["src/gone.py"]


def test_other_agents_rule_files_are_read(tmp_path):
    # Each convention verified against the tool's official docs on 2026-09-24
    # (Cursor, Windsurf, Copilot path-specific, Cline, Junie) - see ADR-0014.
    rules = {
        ".cursor/rules/api.mdc": "---\nalwaysApply: true\n---\nSee `src/gone_a.py`.\n",
        ".windsurfrules": "`src/gone_b.py`\n",
        ".github/instructions/py.instructions.md": "`src/gone_c.py`\n",
        ".clinerules/style.md": "`src/gone_d.py`\n",
        ".junie/guidelines.md": "`src/gone_e.py`\n",
    }
    _repo(tmp_path, {"src/app.py": ""}, rules)
    findings, _, stats = instructions_report(tmp_path)
    assert _path_issues(findings) == [f"src/gone_{c}.py" for c in "abcde"]
    assert stats["files"] == 5


def test_nested_agents_file_resolves_paths_from_root_or_its_own_directory(tmp_path):
    _repo(
        tmp_path,
        {"src/app.py": "", "pkg/core.py": "", "pkg/lib/util.py": ""},
        {"pkg/AGENTS.md": "`core.py` `lib/util.py` `src/app.py` `lib/gone.py`\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert [(f["item"], f["ref"]) for f in findings] == [("pkg/AGENTS.md:1", "lib/gone.py")]
    assert stats["files"] == 1 and stats["paths"] == 4


def test_only_files_tools_read_nested_are_read_nested(tmp_path):
    # Copilot reads .github/copilot-instructions.md at the root only, and a
    # nested README is documentation, not an instruction file.
    _repo(
        tmp_path,
        {"src/app.py": ""},
        {"pkg/README.md": "`src/gone.py`\n", "pkg/.github/copilot-instructions.md": "`src/gone.py`\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["files"] == 0


def test_dependency_and_tooling_dirs_are_not_searched(tmp_path):
    _repo(
        tmp_path,
        {"src/app.py": ""},
        {"node_modules/lib/AGENTS.md": "`src/gone.py`\n", ".venv/pkg/CLAUDE.md": "`src/gone.py`\n"},
    )
    assert instructions_report(tmp_path)[2]["files"] == 0


def test_gitignored_instruction_file_is_not_checked(tmp_path):
    # A personal, ignored file exists on one machine only; checking it would
    # make the same commit pass on CI and fail locally.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _repo(tmp_path, {"src/app.py": "", ".gitignore": "local/\n"}, {"local/CLAUDE.md": "`src/gone.py`\n"})
    assert instructions_report(tmp_path)[2]["files"] == 0


def test_filename_case_must_match_the_convention(tmp_path):
    _repo(tmp_path, {"src/app.py": ""}, {"agents.md": "`src/gone.py`\n"})
    assert instructions_report(tmp_path)[2]["files"] == 0


def test_citing_a_rule_file_convention_is_not_a_claim_it_exists(tmp_path):
    _repo(
        tmp_path,
        {".github/workflows/ci.yml": "on: push\n", "src/app.py": ""},
        {"README.md": "Copilot also reads `.github/instructions/py.instructions.md`.\n"},
    )
    findings, _, stats = instructions_report(tmp_path)
    assert findings == [] and stats["unresolved"] == 1


def test_audit_refs_reads_instruction_files_named_in_the_map(tmp_path):
    _project(tmp_path, "`compare_commits`\n", extra={"intent.md": "`src/pkg/gone.py`\n"})
    target = tmp_path / "adda" / MAP_FILENAME
    data = json.loads(target.read_text(encoding="utf-8"))
    target.write_text(json.dumps({**data, "instructions": ["intent.md"]}), encoding="utf-8")
    res = runner.invoke(app, ["audit", str(tmp_path), "--refs"])
    assert res.exit_code == 1 and "intent.md:1" in res.stdout
