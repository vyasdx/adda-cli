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


def _fsmonitor_repo(root):
    """A repo whose own git config names a program for git to run (core.fsmonitor)."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    marker = root / "fsmonitor-ran"
    script = root / "fsm.sh"
    script.write_text(f"#!/bin/sh\necho x > '{marker.as_posix()}'\n", encoding="utf-8", newline="\n")
    script.chmod(0o755)
    subprocess.run(["git", "config", "core.fsmonitor", script.as_posix()], cwd=root, check=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.py"], cwd=root, check=True,
                   env={**os.environ, "GIT_CONFIG_PARAMETERS": "'core.fsmonitor'='false'"})
    return marker


def test_git_calls_do_not_run_the_repositorys_fsmonitor(tmp_path):
    # BUG-ADDA-047: a downloaded archive can carry git config; core.fsmonitor
    # fires on index refreshes such as `git diff --cached` and `ls-files --others`.
    from adda.hook import staged_paths
    from adda.sync import git_ignored, source_files

    marker = _fsmonitor_repo(tmp_path)
    assert staged_paths(tmp_path) == ["a.py"]
    source_files(tmp_path)
    git_ignored(tmp_path, ["a.py"])
    assert not marker.exists()
    subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=tmp_path, capture_output=True)
    if not marker.exists():
        pytest.skip("this git does not run core.fsmonitor here, so the test proves nothing")


def test_map_entries_outside_the_repository_are_dropped(tmp_path):
    # BUG-ADDA-048: `../x` and absolute paths in MODULE_MAP.json made ADDA read
    # a file outside the repository and print the names it cites.
    from adda.modulemap import load_map
    from adda.refs import refs_report

    secret = tmp_path / "secret.md"
    secret.write_text("token `sk_live_planted_value`\n", encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / "adda").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "a.md").write_text("cites `x`\n", encoding="utf-8")
    entries = {"src/a.py": "docs/a.md", "src/b.py": "../secret.md", "src/c.py": secret.as_posix()}
    (repo / "adda" / "MODULE_MAP.json").write_text(json.dumps({"map": entries}), encoding="utf-8")
    mapping, _ = load_map(repo / "adda")
    assert mapping == {"src/a.py": "docs/a.md"}
    assert "sk_live_planted_value" not in json.dumps(refs_report(repo, repo / "adda"), default=str)


def test_a_path_that_looks_like_an_option_is_not_read_as_one(tmp_path):
    # BUG-ADDA-050 (L1): a doc path reached `git check-ignore` as an option:
    # `[x](--stdin)` waited 10 s for input, and an ignored `-x.md` read as not ignored.
    from adda.refs import _ignored

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("-x.md\n", encoding="utf-8")
    assert _ignored(tmp_path, "-x.md") is True


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
