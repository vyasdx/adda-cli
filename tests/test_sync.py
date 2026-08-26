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
        "src/pkg/cli.py": "docs/modules/pkg/cli.md",
        "src/pkg/core.py": "docs/modules/pkg/core.md",
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
        "src/pkg/core.py": "docs/modules/pkg/core.md"
    }


def test_discover_modules_still_sees_a_templates_source_dir(tmp_path):
    # IGNORE_DIRS is shared with `adda diff`. A real templates/ source package
    # must stay drift-checked; only the MODULE_MAP generator skips it.
    (tmp_path / "src" / "templates").mkdir(parents=True)
    (tmp_path / "src" / "templates" / "views.py").write_text("x = 1\n", encoding="utf-8")
    assert ("templates", "src/templates") in discover_modules(tmp_path)
    assert json.loads(module_map_json(tmp_path))["map"] == {}


def test_same_named_files_in_different_packages_do_not_collide(tmp_path):
    # BUG-ADDA-011. Stem-only naming routed both of these to
    # docs/modules/utils.md, so one doc satisfied two modules and `audit`
    # reported "no doc drift" over a module that had none — a false pass in
    # the routing table itself.
    for pkg in ("payments", "users"):
        (tmp_path / "src" / pkg).mkdir(parents=True)
        (tmp_path / "src" / pkg / "utils.py").write_text("x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {
        "src/payments/utils.py": "docs/modules/payments/utils.md",
        "src/users/utils.py": "docs/modules/users/utils.md",
    }
    # the property that actually matters: no two code paths share a doc
    docs = list(mapping.values())
    assert len(docs) == len(set(docs)), "two code paths route to the same doc"

def test_map_prefers_real_packages_over_example_directories(tmp_path):
    # ENH-ADDA-017, found by running against fastapi: docs_src/ holds 369
    # tutorial snippets and no __init__.py, against 41 files in the fastapi
    # package. Without preferring packages, 90% of the generated map demanded
    # module docs for documentation examples.
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "lib" / "core.py").write_text("x = 1\n", encoding="utf-8")

    (tmp_path / "docs_src" / "tutorial").mkdir(parents=True)
    (tmp_path / "docs_src" / "tutorial" / "example.py").write_text("x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {"lib/core.py": "docs/modules/lib/core.md"}


def test_map_falls_back_to_all_dirs_when_no_package_exists(tmp_path):
    # A loose-script layout with no __init__.py anywhere must still be mapped,
    # rather than silently producing an empty map.
    (tmp_path / "src" / "billing").mkdir(parents=True)
    (tmp_path / "src" / "billing" / "limiter.py").write_text("x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {"src/billing/limiter.py": "docs/modules/billing/limiter.md"}

def test_map_covers_typescript_and_javascript(tmp_path):
    # ENH-ADDA-016. discover_deps already read package.json, but the map
    # generator globbed *.py only, so doc enforcement stopped at Python.
    src = tmp_path / "src" / "app"
    src.mkdir(parents=True)
    for f in ("index.ts", "widget.tsx", "legacy.js", "helper.mjs"):
        (src / f).write_text("export const x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {
        "src/app/helper.mjs": "docs/modules/app/helper.md",
        "src/app/index.ts": "docs/modules/app/index.md",
        "src/app/legacy.js": "docs/modules/app/legacy.md",
        "src/app/widget.tsx": "docs/modules/app/widget.md",
    }


def test_map_excludes_declarations_bundles_and_tests(tmp_path):
    # `.d.ts` documents code documented elsewhere and `.min.js` is a build
    # artefact. The bare `test.ts` case is from date-fns, which names the test
    # beside its module 253 times rather than infixing `.test.` — without the
    # stem check that was 17% of its generated map.
    src = tmp_path / "src" / "app"
    src.mkdir(parents=True)
    for f in ("real.ts", "types.d.ts", "bundle.min.js", "real.test.ts", "test.ts", "spec.js"):
        (src / f).write_text("export const x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {"src/app/real.ts": "docs/modules/app/real.md"}

def test_python_root_without_init_is_examples_even_with_stray_js(tmp_path):
    """ENH-ADDA-017 / BUG-ADDA-014. fastapi's docs_src/ holds 369 .py snippets
    AND a couple of .js files, so an "all Python" test was defeated by one
    stray file. A root that CONTAINS Python must be a package."""
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "__init__.py").write_text("", encoding="utf-8")
    (lib / "core.py").write_text("x = 1\n", encoding="utf-8")

    ex = tmp_path / "docs_src"
    ex.mkdir()
    (ex / "tutorial.py").write_text("x = 1\n", encoding="utf-8")
    (ex / "demo.js").write_text("const x = 1\n", encoding="utf-8")

    mapping = json.loads(module_map_json(tmp_path))["map"]
    assert mapping == {"lib/core.py": "docs/modules/lib/core.md"}
