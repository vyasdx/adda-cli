# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda audit must catch the doc-layer drift that `adda diff` structurally cannot."""

import json
import subprocess

from typer.testing import CliRunner

from adda.audit import audit_report
from adda.cli import app
from adda.modulemap import MAP_FILENAME

runner = CliRunner()


def _project(root, mapping, exempt=(), docs=(), code=()):
    adda = root / "adda"
    adda.mkdir(parents=True, exist_ok=True)
    (adda / MAP_FILENAME).write_text(
        json.dumps({"map": mapping, "exempt": list(exempt)}), encoding="utf-8"
    )
    for rel in code:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x = 1\n", encoding="utf-8")
    for rel in docs:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# doc\n", encoding="utf-8")


def _issues(findings):
    return {(f["item"], f["issue"], f["severity"]) for f in findings}


def test_rule1_missing_doc_is_high(tmp_path):
    # This is the exact failure of 2026-08-18: code documented in the map,
    # doc never written, and `adda diff` reported clean throughout.
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=[],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert ("docs/modules/cli.md", "doc missing", "high") in _issues(findings)


def test_rule3_unmapped_source_file_is_medium(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py", "src/pkg/sneaky.py"],
        docs=["docs/modules/cli.md"],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert ("src/pkg/sneaky.py", "code unmapped", "medium") in _issues(findings)


def test_rule3_exempt_file_is_not_flagged(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        exempt=["src/pkg/__init__.py"],
        code=["src/pkg/cli.py", "src/pkg/__init__.py"],
        docs=["docs/modules/cli.md"],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert not any(f["item"] == "src/pkg/__init__.py" for f in findings)


def test_rule4_orphaned_doc_is_low(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/gone.py": "docs/modules/gone.md"},
        code=[],
        docs=["docs/modules/gone.md"],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert ("src/pkg/gone.py", "doc orphaned", "low") in _issues(findings)


def test_clean_project_reports_nothing(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert [f for f in findings if f["issue"] != "doc stale"] == []


def test_templates_py_is_not_flagged_as_unmapped(tmp_path):
    # audit must apply the SAME source rule as module_map_json, which excludes
    # templates/. Otherwise audit reports drift on a file the generator
    # deliberately refuses to map — a false positive that erodes trust.
    _project(
        tmp_path,
        {"src/pkg/core.py": "docs/modules/core.md"},
        code=["src/pkg/core.py", "src/pkg/templates/seed.py"],
        docs=["docs/modules/core.md"],
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert not any(f["item"] == "src/pkg/templates/seed.py" for f in findings)


def test_map_entry_with_neither_code_nor_doc_is_reported(tmp_path):
    # A stale map entry must never pass silently.
    _project(tmp_path, {"src/pkg/gone.py": "docs/modules/gone.md"}, code=[], docs=[])
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    assert ("src/pkg/gone.py", "map entry stale", "low") in _issues(findings)


def _git(repo, *args):
    subprocess.run(
        ["git", *args], cwd=repo, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _git_repo(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    return tmp_path


def test_rule2_doc_older_than_code_is_stale(tmp_path):
    repo = _git_repo(tmp_path)
    _project(
        repo,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")

    # Touch only the code, in a later commit -> the doc is now stale.
    (repo / "src" / "pkg" / "cli.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "change code only")

    findings, skipped = audit_report(repo, repo / "adda")
    assert skipped == []
    assert ("docs/modules/cli.md", "doc stale", "medium") in _issues(findings)


def test_same_second_separate_commits_are_still_detected_as_stale(tmp_path):
    # Two commits inside the same second tie under `%ct`, which silently
    # reported a stale doc as clean. Ancestry is exact, so this must be
    # caught with no sleep anywhere.
    repo = _git_repo(tmp_path)
    _project(
        repo,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    (repo / "src" / "pkg" / "cli.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "code only, same second")

    findings, skipped = audit_report(repo, repo / "adda")
    assert skipped == []
    assert ("docs/modules/cli.md", "doc stale", "medium") in _issues(findings)


def test_rule2_doc_updated_with_code_is_not_stale(tmp_path):
    repo = _git_repo(tmp_path)
    _project(
        repo,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")

    (repo / "src" / "pkg" / "cli.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "docs" / "modules" / "cli.md").write_text("# doc v2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "change both together")

    findings, _ = audit_report(repo, repo / "adda")
    assert not any(f["issue"] == "doc stale" for f in findings)


def test_rule2_outside_git_is_reported_as_skipped_not_passed(tmp_path):
    # A check that cannot run must SAY SO. Silent pass is the failure mode
    # this whole release exists to kill.
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    findings, skipped = audit_report(tmp_path, tmp_path / "adda")
    assert skipped, "staleness must be reported as skipped outside a git repo"
    assert "stale" in skipped[0].lower()
    assert not any(f["issue"] == "doc stale" for f in findings)


def test_divergent_history_is_skipped_not_reported_clean(tmp_path):
    # Doc touched only on a branch, code touched only on main. Neither commit
    # is an ancestor of the other, so staleness is genuinely undecidable —
    # it must be REPORTED as skipped, never silently pass as current.
    repo = _git_repo(tmp_path)
    _project(
        repo,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    default_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git(repo, "checkout", "-b", "feature")
    (repo / "docs" / "modules" / "cli.md").write_text("# doc v2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "doc on branch")
    _git(repo, "checkout", default_branch)
    (repo / "src" / "pkg" / "cli.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "code on default branch")
    _git(repo, "merge", "feature", "--no-edit")

    findings, skipped = audit_report(repo, repo / "adda")
    assert skipped, "undecidable ancestry must be reported, not silently passed"
    assert not any(f["issue"] == "doc stale" for f in findings)


def test_compare_commits_returns_unknown_for_bogus_shas(tmp_path):
    from adda.audit import compare_commits

    repo = _git_repo(tmp_path)
    (repo / "f.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    # Objects that do not exist: git cannot decide -> must be 'unknown',
    # never 'current'.
    assert compare_commits(repo, "0" * 40, "1" * 40) == "unknown"


def test_audit_clean_exits_zero(tmp_path):
    repo = _git_repo(tmp_path)
    _project(
        repo,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    res = runner.invoke(app, ["audit", str(repo)])
    assert res.exit_code == 0
    assert "No doc drift" in res.stdout


def test_audit_finding_exits_one(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=[],
    )
    res = runner.invoke(app, ["audit", str(tmp_path)])
    assert res.exit_code == 1
    assert "doc missing" in res.stdout


def test_audit_prints_skipped_rules(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=["docs/modules/cli.md"],
    )
    res = runner.invoke(app, ["audit", str(tmp_path)])
    assert "skipped" in res.stdout.lower()


def test_audit_without_module_map_explains_how_to_fix(tmp_path):
    (tmp_path / "adda").mkdir()
    (tmp_path / "adda" / "VERSION.md").write_text("project: P\n", encoding="utf-8")
    res = runner.invoke(app, ["audit", str(tmp_path)])
    assert res.exit_code == 1
    assert "sync --map" in res.stdout


def test_audit_json_flag_emits_parsable_report(tmp_path):
    _project(
        tmp_path,
        {"src/pkg/cli.py": "docs/modules/cli.md"},
        code=["src/pkg/cli.py"],
        docs=[],
    )
    res = runner.invoke(app, ["audit", str(tmp_path), "--json"])
    payload = json.loads(res.stdout)
    assert payload["findings"][0]["issue"] == "doc missing"
    assert "skipped" in payload


def test_audit_json_stays_parsable_when_module_map_is_missing(tmp_path):
    # A CI script doing `adda audit --json | jq` must not break on the very
    # setup error it most needs to read.
    (tmp_path / "adda").mkdir()
    (tmp_path / "adda" / "VERSION.md").write_text("project: P\n", encoding="utf-8")
    res = runner.invoke(app, ["audit", str(tmp_path), "--json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert "sync --map" in payload["error"]
    assert payload["findings"] == []


def test_audit_would_have_caught_the_2026_08_07_doc_hole(tmp_path):
    """Regression against real history, not a synthetic fixture.

    At commit 23ee895 (2026-08-07) every src/adda/*.py existed and
    docs/modules/ did not. `adda diff` reported "No drift" throughout, because
    it only checks module PATHS and ignores docs/. audit must not.
    """
    modules = ["cli", "okf", "sentinel", "rehydrate", "compress", "sync", "diff", "evaluate"]
    _project(
        tmp_path,
        {f"src/adda/{m}.py": f"docs/modules/{m}.md" for m in modules},
        exempt=["src/adda/__init__.py", "src/adda/templates/**"],
        code=[f"src/adda/{m}.py" for m in modules] + ["src/adda/__init__.py"],
        docs=[],  # the hole
    )
    findings, _ = audit_report(tmp_path, tmp_path / "adda")
    missing = {f["item"] for f in findings if f["issue"] == "doc missing"}
    assert missing == {f"docs/modules/{m}.md" for m in modules}
    assert all(f["severity"] == "high" for f in findings if f["issue"] == "doc missing")

def test_new_typescript_file_added_after_sync_is_caught_as_unmapped(tmp_path):
    """BUG-ADDA-013, end to end: generate the map, THEN add a .ts file.

    The map generator covered ts/tsx/js while audit still globbed *.py, so a
    file added after the map was written was absent from the map AND invisible
    to the unmapped-code rule. It escaped enforcement entirely. This asserts
    ongoing enforcement, not just map generation.
    """
    from adda.sync import module_map_json

    app = tmp_path / "src" / "app"
    app.mkdir(parents=True)
    (app / "index.ts").write_text("export const x = 1\n", encoding="utf-8")

    adda = tmp_path / "adda"
    adda.mkdir()
    (adda / MAP_FILENAME).write_text(module_map_json(tmp_path), encoding="utf-8")
    (tmp_path / "docs" / "modules" / "app").mkdir(parents=True)
    (tmp_path / "docs" / "modules" / "app" / "index.md").write_text("# d\n", encoding="utf-8")

    findings, _ = audit_report(tmp_path, adda)
    assert findings == [], "baseline should be clean"

    # a developer adds a file and does not regenerate the map
    (app / "payment.ts").write_text("export const y = 1\n", encoding="utf-8")

    findings, _ = audit_report(tmp_path, adda)
    assert ("src/app/payment.ts", "code unmapped", "medium") in _issues(findings)


def test_mixed_python_and_typescript_repo_keeps_both(tmp_path):
    """BUG-ADDA-014: `backend/` having __init__.py must not delete `frontend/`.

    The package test was applied to every root, so one Python package in a
    monorepo dropped the entire TypeScript side from the map and from audit.
    """
    from adda.sync import module_map_json

    be = tmp_path / "src" / "backend"
    be.mkdir(parents=True)
    (be / "__init__.py").write_text("", encoding="utf-8")
    (be / "api.py").write_text("x = 1\n", encoding="utf-8")

    fe = tmp_path / "src" / "frontend"
    fe.mkdir(parents=True)
    (fe / "app.ts").write_text("export const x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert "src/backend/api.py" in mapping
    assert "src/frontend/app.ts" in mapping


def test_audit_reports_the_root_it_chose_not_to_map(tmp_path):
    """DEC-ADDA-009: a wrong guess must cost a printed line, not a whole directory.

    `toolscripts/` disappears because `pkgmod/` has an `__init__.py`
    (BUG-ADDA-020). The heuristic is kept deliberately, so the guarantee is not
    that the files get mapped — it is that `audit` says so out loud instead of
    reporting a clean sweep over code nothing is enforcing.
    """
    (tmp_path / "pkgmod").mkdir()
    (tmp_path / "pkgmod" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkgmod" / "core.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "toolscripts").mkdir()
    (tmp_path / "toolscripts" / "build.py").write_text("y = 2\n", encoding="utf-8")

    adda = tmp_path / "adda"
    adda.mkdir()
    (adda / MAP_FILENAME).write_text(
        json.dumps({"map": {"pkgmod/core.py": "docs/modules/pkgmod/core.md"},
                    "exempt": ["pkgmod/__init__.py"]}),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "modules" / "pkgmod").mkdir(parents=True)
    (tmp_path / "docs" / "modules" / "pkgmod" / "core.md").write_text("d\n", encoding="utf-8")

    findings, skipped = audit_report(tmp_path, adda)
    assert not findings, findings
    assert any("toolscripts" in note for note in skipped), (
        "audit reported a clean sweep and never mentioned the root it dropped"
    )

    # ...and `include` in the map takes it back under enforcement.
    (adda / MAP_FILENAME).write_text(
        json.dumps({
            "map": {"pkgmod/core.py": "docs/modules/pkgmod/core.md"},
            "exempt": ["pkgmod/__init__.py"],
            "include": ["toolscripts"],
        }),
        encoding="utf-8",
    )
    findings, skipped = audit_report(tmp_path, adda)
    assert {"item": "toolscripts/build.py", "issue": "code unmapped",
            "severity": "medium"} in findings
    assert not any("toolscripts" in note for note in skipped)
