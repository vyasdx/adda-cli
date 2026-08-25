# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda sync should derive modules (with paths) and deps from a sample repo."""

import json

from typer.testing import CliRunner

from adda.cli import app
from adda.sync import discover_modules, module_map_json

runner = CliRunner()


def _make_sample(root):
    (root / "src" / "widget").mkdir(parents=True)
    (root / "src" / "widget" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "helper").mkdir(parents=True)
    (root / "src" / "helper" / "core.py").write_text("y = 2\n", encoding="utf-8")
    (root / "src" / "__pycache__").mkdir(parents=True)  # must be ignored
    (root / "src" / "__pycache__" / "junk.pyc").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "s"\ndependencies = ["requests>=2.0", "rich"]\n',
        encoding="utf-8",
    )


def test_discover_modules_skips_noise(tmp_path):
    _make_sample(tmp_path)
    mods = dict(discover_modules(tmp_path))
    assert mods == {"widget": "src/widget", "helper": "src/helper"}  # no __pycache__


def test_discover_modules_skips_dir_with_only_ignored_content(tmp_path):
    (tmp_path / "src" / "real").mkdir(parents=True)
    (tmp_path / "src" / "real" / "m.py").write_text("x = 1\n", encoding="utf-8")
    # phantom/: its only file lives in an ignored subdir -> must not count as a module
    (tmp_path / "src" / "phantom" / "__pycache__").mkdir(parents=True)
    (tmp_path / "src" / "phantom" / "__pycache__" / "x.pyc").write_text("", encoding="utf-8")
    mods = dict(discover_modules(tmp_path))
    assert "real" in mods
    assert "phantom" not in mods


def test_sync_cli_outputs_skeleton(tmp_path):
    _make_sample(tmp_path)
    res = runner.invoke(app, ["sync", str(tmp_path)])
    assert res.exit_code == 0
    out = res.stdout
    assert "- widget (active) [src/widget]" in out
    assert "- helper (active) [src/helper]" in out
    assert "- requests" in out and "- rich" in out


def test_module_map_json_maps_source_files_to_docs(tmp_path):
    from adda.sync import module_map_json

    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "cli.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "core.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    data = json.loads(module_map_json(tmp_path))
    assert data["map"] == {
        "src/pkg/cli.py": "docs/modules/cli.md",
        "src/pkg/core.py": "docs/modules/core.md",
    }
    # __init__.py is a version/export stub, not a documented code path.
    assert "src/pkg/__init__.py" in data["exempt"]


def test_module_map_json_ignores_non_python_and_ignored_dirs(tmp_path):
    from adda.sync import module_map_json

    pkg = tmp_path / "src" / "pkg"
    (pkg / "templates").mkdir(parents=True)
    (pkg / "core.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "notes.md").write_text("hi\n", encoding="utf-8")
    (pkg / "templates" / "seed.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n", encoding="utf-8")

    data = json.loads(module_map_json(tmp_path))
    assert list(data["map"]) == ["src/pkg/core.py"]


def test_sync_map_flag_writes_json(tmp_path):
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "core.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "MODULE_MAP.json"
    res = runner.invoke(app, ["sync", str(tmp_path), "--map", "--out", str(out)])
    assert res.exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["map"] == {
        "src/pkg/core.py": "docs/modules/core.md"
    }


def test_discover_modules_still_sees_a_templates_source_dir(tmp_path):
    # IGNORE_DIRS is shared with `adda diff`. A real templates/ source package
    # must stay drift-checked; only the MODULE_MAP generator skips it.
    (tmp_path / "src" / "templates").mkdir(parents=True)
    (tmp_path / "src" / "templates" / "views.py").write_text("x = 1\n", encoding="utf-8")
    assert ("templates", "src/templates") in discover_modules(tmp_path)
    assert json.loads(module_map_json(tmp_path))["map"] == {}
