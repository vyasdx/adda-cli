# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""End-to-end CLI checks for the init -> export -> checkpoint flow."""

import re
from pathlib import Path

from typer.testing import CliRunner

from adda import __version__
from adda.cli import app

runner = CliRunner()


def test_version_matches_pyproject():
    # Plain-text read on purpose: tomllib is 3.11+, and this suite must run on
    # the 3.10 floor pyproject declares. Same reason as test_sentinel.py.
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)
    assert version == __version__


def test_init_export_checkpoint(tmp_path):
    assert runner.invoke(app, ["init", str(tmp_path)]).exit_code == 0
    assert (tmp_path / "adda" / "VERSION.md").is_file()

    assert runner.invoke(app, ["export", str(tmp_path)]).exit_code == 0
    assert (tmp_path / "okf.json").is_file()

    res = runner.invoke(app, ["checkpoint", str(tmp_path), "-m", "before compact"])
    assert res.exit_code == 0
    snaps = list((tmp_path / "adda" / "STATE" / "checkpoints").glob("*.md"))
    assert len(snaps) == 1
    body = snaps[0].read_text(encoding="utf-8")
    assert "before compact" in body
    assert "Current State" in body  # copied from CURRENT.md
