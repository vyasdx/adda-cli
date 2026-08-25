# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The commit gate: staged code without its staged doc must block the commit."""

import json
import subprocess

from typer.testing import CliRunner

from adda.cli import app
from adda.hook import check_staged
from adda.modulemap import MAP_FILENAME

runner = CliRunner()

MAP = {"src/pkg/cli.py": "docs/modules/cli.md"}


def _project(root, mapping=None, exempt=()):
    adda = root / "adda"
    adda.mkdir(parents=True, exist_ok=True)
    (adda / "VERSION.md").write_text("project: P\n", encoding="utf-8")
    (adda / MAP_FILENAME).write_text(
        json.dumps({"map": mapping or MAP, "exempt": list(exempt)}), encoding="utf-8"
    )


def test_staged_code_without_its_doc_is_blocked(tmp_path):
    _project(tmp_path)
    gaps = check_staged(tmp_path, tmp_path / "adda", ["src/pkg/cli.py"])
    assert gaps == [("src/pkg/cli.py", "docs/modules/cli.md")]


def test_staged_code_with_its_doc_passes(tmp_path):
    _project(tmp_path)
    gaps = check_staged(
        tmp_path, tmp_path / "adda", ["src/pkg/cli.py", "docs/modules/cli.md"]
    )
    assert gaps == []


def test_unmapped_staged_file_does_not_block(tmp_path):
    # The commit gate is commit-scoped. Unmapped files are `audit`'s business;
    # blocking here would make the hook fire on unrelated commits and get
    # permanently --no-verify'd.
    _project(tmp_path)
    assert check_staged(tmp_path, tmp_path / "adda", ["README.md"]) == []


def test_exempt_staged_file_does_not_block(tmp_path):
    _project(tmp_path, exempt=["src/pkg/__init__.py"])
    assert check_staged(tmp_path, tmp_path / "adda", ["src/pkg/__init__.py"]) == []


def test_missing_module_map_does_not_block_the_commit(tmp_path):
    # A repo that has not adopted MODULE_MAP must stay committable.
    (tmp_path / "adda").mkdir()
    (tmp_path / "adda" / "VERSION.md").write_text("project: P\n", encoding="utf-8")
    assert check_staged(tmp_path, tmp_path / "adda", ["src/pkg/cli.py"]) == []


def test_hook_run_honours_adda_skip(tmp_path, monkeypatch):
    _project(tmp_path)
    monkeypatch.setenv("ADDA_SKIP", "1")
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["hook", "run"])
    assert res.exit_code == 0


def _git(repo, *args):
    subprocess.run(
        ["git", *args], cwd=repo, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def test_non_ascii_staged_path_is_not_mangled(tmp_path):
    # git quotes non-ASCII paths by default; a mangled path matches no
    # MODULE_MAP entry, so the file would slip through the gate unnoticed.
    from adda.hook import staged_paths

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    target = tmp_path / "src" / "pkg"
    target.mkdir(parents=True)
    (target / "café.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")

    assert staged_paths(tmp_path) == ["src/pkg/café.py"]


def test_non_ascii_mapped_file_without_its_doc_still_blocks(tmp_path):
    # The end-to-end consequence of the quoting bug: this commit must be caught.
    _project(tmp_path, mapping={"src/pkg/café.py": "docs/modules/café.md"})
    gaps = check_staged(
        tmp_path, tmp_path / "adda", ["src/pkg/café.py"]
    )
    assert gaps == [("src/pkg/café.py", "docs/modules/café.md")]


def _git_dir(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    return hooks


def test_install_writes_stub_that_execs_hook_run(tmp_path):
    hooks = _git_dir(tmp_path)
    res = runner.invoke(app, ["hook", "install", str(tmp_path)])
    assert res.exit_code == 0
    body = (hooks / "pre-commit").read_text(encoding="utf-8")
    assert "-m adda.cli hook run" in body
    assert body.startswith("#!/bin/sh")


def test_install_bakes_the_current_interpreter_into_the_hook(tmp_path):
    # The hook must not depend on `adda` being on PATH: ADDA usually lives in
    # a venv that is not active when git runs hooks, and a bare `adda` can even
    # resolve to ADDA's own adda/ memory directory.
    import sys

    hooks = _git_dir(tmp_path)
    res = runner.invoke(app, ["hook", "install", str(tmp_path)])
    assert res.exit_code == 0
    body = (hooks / "pre-commit").read_text(encoding="utf-8")
    assert sys.executable.replace("\\", "/") in body
    assert "-m adda.cli hook run" in body
    assert "adda hook run" not in body  # the PATH-dependent form must be gone


def test_hook_body_fails_open_when_interpreter_is_missing():
    from adda.hook import hook_body

    body = hook_body("/nonexistent/python.exe")
    assert "exit 0" in body          # must not block commits forever
    assert "doc gate skipped" in body


def test_install_refuses_to_clobber_existing_hook(tmp_path):
    hooks = _git_dir(tmp_path)
    (hooks / "pre-commit").write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    res = runner.invoke(app, ["hook", "install", str(tmp_path)])
    assert res.exit_code == 1
    assert "--force" in res.stdout
    assert "echo mine" in (hooks / "pre-commit").read_text(encoding="utf-8")


def test_install_force_overwrites(tmp_path):
    hooks = _git_dir(tmp_path)
    (hooks / "pre-commit").write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    res = runner.invoke(app, ["hook", "install", str(tmp_path), "--force"])
    assert res.exit_code == 0
    assert "-m adda.cli hook run" in (hooks / "pre-commit").read_text(encoding="utf-8")


def test_install_outside_git_repo_fails_clearly(tmp_path):
    res = runner.invoke(app, ["hook", "install", str(tmp_path)])
    assert res.exit_code == 1
    assert "not a git repo" in res.stdout.lower()
