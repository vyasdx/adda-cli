# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""`adda doctor` must prove the commit gate is on, not assume it (ENH-ADDA-030).

Every way the gate can be installed and still enforce nothing - each one found
in this repo's own history or reproduced on a scratch repo - must come out as a
failed check and a non-zero exit, never as silence.
"""

import json
import os
import subprocess
import sys

from typer.testing import CliRunner

from adda.cli import app
from adda.doctor import diagnose
from adda.hook import hook_body
from adda.modulemap import MAP_FILENAME

runner = CliRunner()


def _repo(root, map_text=None):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    adda = root / "adda"
    adda.mkdir()
    (adda / "VERSION.md").write_text("project: P\n", encoding="utf-8")
    if map_text is None:
        map_text = json.dumps({"map": {"src/app.py": "docs/modules/app.md"}, "exempt": []})
    if map_text is not False:
        (adda / MAP_FILENAME).write_text(map_text, encoding="utf-8")


def _install(root):
    res = runner.invoke(app, ["hook", "install", str(root)])
    assert res.exit_code == 0, res.stdout


def _state(checks, name):
    return next(c["state"] for c in checks if c["check"] == name)


def _failed(checks):
    return [c["check"] for c in checks if c["state"] == "fail"]


def test_healthy_install_passes_every_check(tmp_path):
    _repo(tmp_path)
    _install(tmp_path)
    checks = diagnose(tmp_path)
    assert _failed(checks) == []
    res = runner.invoke(app, ["doctor", str(tmp_path)])
    assert res.exit_code == 0
    assert "0 failed" in res.stdout


def test_no_hook_installed_fails(tmp_path):
    _repo(tmp_path)
    checks = diagnose(tmp_path)
    assert _state(checks, "pre-commit hook") == "fail"
    assert runner.invoke(app, ["doctor", str(tmp_path)]).exit_code == 1


def test_interpreter_gone_fails_because_the_hook_fails_open(tmp_path):
    # The stub exits 0 when its interpreter vanishes - by design, so a deleted
    # venv cannot brick every commit. That makes it invisible; doctor is the
    # place it becomes visible.
    _repo(tmp_path)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text(hook_body(str(tmp_path / "gone" / "python")), encoding="utf-8", newline="\n")
    assert _state(diagnose(tmp_path), "interpreter") == "fail"


def test_interpreter_path_that_is_not_runnable_fails(tmp_path):
    _repo(tmp_path)
    not_python = tmp_path / "adda" / "VERSION.md"  # exists, cannot run at all
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text(hook_body(str(not_python)), encoding="utf-8", newline="\n")
    checks = diagnose(tmp_path)
    assert _state(checks, "interpreter") == "ok"
    assert _state(checks, "adda importable") == "fail"


def test_python_without_adda_installed_fails(tmp_path):
    # A real interpreter that runs, but whose environment has no adda - the
    # state after recreating a venv and forgetting `pip install -e .`.
    _repo(tmp_path)
    venv = tmp_path / "bare-venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text(hook_body(str(python)), encoding="utf-8", newline="\n")
    assert _state(diagnose(tmp_path), "adda importable") == "fail"


def test_foreign_pre_commit_hook_fails(tmp_path):
    _repo(tmp_path)
    (tmp_path / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\nnpm test\n", encoding="utf-8")
    assert _state(diagnose(tmp_path), "runs the ADDA gate") == "fail"


def test_hook_outside_core_hooks_path_fails(tmp_path):
    # BUG-ADDA-027: with core.hooksPath set, git never runs .git/hooks.
    _repo(tmp_path)
    _install(tmp_path)
    subprocess.run(["git", "config", "core.hooksPath", ".husky"], cwd=tmp_path, check=True)
    checks = diagnose(tmp_path)
    assert _state(checks, "pre-commit hook") == "fail"
    assert ".husky" in next(c["detail"] for c in checks if c["check"] == "pre-commit hook")


def test_missing_map_fails_because_the_gate_enforces_nothing(tmp_path):
    _repo(tmp_path, map_text=False)
    _install(tmp_path)
    checks = diagnose(tmp_path)
    assert _state(checks, "MODULE_MAP.json") == "fail"
    # the advice must be the fix for an absent map, not a read error
    assert "adda sync" in next(c["detail"] for c in checks if c["check"] == "MODULE_MAP.json")


def test_unreadable_map_fails(tmp_path):
    _repo(tmp_path, map_text="{not json")
    _install(tmp_path)
    assert _state(diagnose(tmp_path), "MODULE_MAP.json") == "fail"


def test_empty_map_fails(tmp_path):
    _repo(tmp_path, map_text=json.dumps({"map": {}, "exempt": []}))
    _install(tmp_path)
    assert _state(diagnose(tmp_path), "MODULE_MAP.json") == "fail"


def test_adda_skip_in_the_environment_fails(tmp_path, monkeypatch):
    _repo(tmp_path)
    _install(tmp_path)
    monkeypatch.setenv("ADDA_SKIP", "1")
    assert _state(diagnose(tmp_path), "ADDA_SKIP") == "fail"


def test_outside_a_git_repo_fails_clearly(tmp_path):
    res = runner.invoke(app, ["doctor", str(tmp_path)])
    assert res.exit_code == 1
    assert "git" in res.stdout.lower()
