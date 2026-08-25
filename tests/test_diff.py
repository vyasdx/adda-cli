# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda diff must catch planted drift: vanished documented modules and undocumented code."""

from typer.testing import CliRunner

from adda.cli import app
from adda.diff import diff_report

runner = CliRunner()


def _project(root, modules_block, src_dirs):
    adda = root / "adda"
    (adda / "STATE").mkdir(parents=True)
    (adda / "VERSION.md").write_text("project: P\nversion: 1.0\n", encoding="utf-8")
    (adda / "ARCHITECTURE.md").write_text(
        "# Architecture\n\n## Modules\n" + modules_block, encoding="utf-8"
    )
    for d in src_dirs:
        (root / d).mkdir(parents=True)
        (root / d / "code.py").write_text("x = 1\n", encoding="utf-8")


def test_diff_catches_missing_and_undocumented(tmp_path):
    # core[src/core] exists; ghost[src/ghost] is planted drift (missing);
    # src/extra exists but is undocumented.
    _project(
        tmp_path,
        "- core: (active) [src/core]\n- ghost: (active) [src/ghost]\n",
        ["src/core", "src/extra"],
    )
    gaps = diff_report(tmp_path, tmp_path / "adda")
    flagged = {(g["module"], g["severity"]) for g in gaps}
    assert ("ghost", "high") in flagged     # documented but vanished
    assert ("extra", "medium") in flagged   # present but undocumented
    assert not any(g["module"] == "core" for g in gaps)  # core matches -> no gap


def test_diff_clean_exits_zero(tmp_path):
    _project(tmp_path, "- core: (active) [src/core]\n", ["src/core"])
    res = runner.invoke(app, ["diff", str(tmp_path)])
    assert res.exit_code == 0
    assert "No drift" in res.stdout


def test_diff_drift_exits_one(tmp_path):
    _project(tmp_path, "- ghost: (active) [src/ghost]\n", ["src/core"])
    res = runner.invoke(app, ["diff", str(tmp_path)])
    assert res.exit_code == 1
    assert "Drift detected" in res.stdout


def test_diff_name_documented_without_path_is_not_drift(tmp_path):
    # A module documented by name only (no [path]) whose dir exists must NOT be
    # flagged as undocumented drift.
    _project(tmp_path, "- core: Core logic (active)\n", ["src/core"])
    assert diff_report(tmp_path, tmp_path / "adda") == []


def test_diff_file_level_module_keeps_parent_clean(tmp_path):
    # ENH-ADDA-002: a documented file-level module covers its parent dir, so the
    # dir is not flagged undocumented.
    _project(tmp_path, "- cli: entrypoint (active) [src/pkg/cli.py]\n", [])
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "cli.py").write_text("x = 1\n", encoding="utf-8")
    assert diff_report(tmp_path, tmp_path / "adda") == []
