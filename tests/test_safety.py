# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The repository ADDA reads is untrusted input (ADR-0030).

Symlink cases need permission to create symlinks: CI (Linux) has it, a
Windows machine without developer mode does not, so they skip there.
"""

import json
import os
import stat
import subprocess

import pytest
from typer.testing import CliRunner

from adda.cli import app
from adda.safety import UnsafeWrite, write_text

runner = CliRunner()


def _symlink(link, target, is_dir=False):
    try:
        os.symlink(target, link, target_is_directory=is_dir)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks here")


def _project(root):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    assert runner.invoke(app, ["init", str(root)]).exit_code == 0


def test_write_text_replaces_the_file_and_keeps_its_mode(tmp_path):
    target = tmp_path / "out.json"
    target.write_text("old", encoding="utf-8")
    if os.name != "nt":
        target.chmod(0o640)
    write_text(target, "new", root=tmp_path)
    assert target.read_text(encoding="utf-8") == "new"
    if os.name != "nt":
        assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]  # no temp file left


def test_write_text_refuses_a_symlinked_target(tmp_path):
    # BUG-ADDA-046: a tracked okf.json -> ../../.bashrc was overwritten.
    victim = tmp_path / "victim"
    victim.write_text("keep", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _symlink(repo / "okf.json", victim)
    with pytest.raises(UnsafeWrite):
        write_text(repo / "okf.json", "payload", root=repo)
    assert victim.read_text(encoding="utf-8") == "keep"


def test_write_text_refuses_a_path_whose_folder_leaves_the_repo(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    _symlink(repo / "adda", outside, is_dir=True)
    with pytest.raises(UnsafeWrite):
        write_text(repo / "adda" / "MODULE_MAP.json", "{}", root=repo)
    assert not (outside / "MODULE_MAP.json").exists()


def test_a_deliberate_out_path_outside_the_repo_still_works(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    elsewhere = tmp_path / "elsewhere.json"
    write_text(elsewhere, "{}", root=repo)
    assert elsewhere.read_text(encoding="utf-8") == "{}"


def test_export_refuses_a_symlinked_okf_json(tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("keep", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _project(repo)
    _symlink(repo / "okf.json", victim)
    res = runner.invoke(app, ["export", str(repo)])
    assert res.exit_code == 1
    assert victim.read_text(encoding="utf-8") == "keep"


def test_export_still_writes_okf_json(tmp_path):
    _project(tmp_path)
    assert runner.invoke(app, ["export", str(tmp_path)]).exit_code == 0
    assert "architecture" in json.loads((tmp_path / "okf.json").read_text(encoding="utf-8"))


def test_init_force_refuses_a_scaffold_file_that_is_a_symlink(tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("keep", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _project(repo)
    (repo / "adda" / "VERSION.md").unlink()
    _symlink(repo / "adda" / "VERSION.md", victim)
    res = runner.invoke(app, ["init", str(repo), "--force"])
    assert res.exit_code == 1
    assert victim.read_text(encoding="utf-8") == "keep"
