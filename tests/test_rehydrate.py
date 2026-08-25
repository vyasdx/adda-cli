# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The minimal OKF must be smaller than the full OKF and carry only active items."""

import json
from pathlib import Path

from adda.okf import compile_okf
from adda.rehydrate import minimal_okf

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "adda" / "templates" / "adda"


def test_minimal_is_smaller_and_active_only():
    okf = compile_okf(TEMPLATES)
    minimal = minimal_okf(okf)

    full_json = json.dumps(okf.model_dump())
    mini_json = json.dumps(minimal)
    assert len(mini_json) < len(full_json)  # the whole point: smaller payload

    # active modules only — the planned "worker" is dropped
    names = [m["name"] for m in minimal["modules"]]
    assert names == ["core", "api"]

    # load-bearing fields kept (spec §13)
    assert minimal["version"] == "0.1.0"
    assert minimal["constraints"]
    assert minimal["decisions"][0]["id"] == "ADR-0001"

    # heavy fields dropped
    assert "architecture" not in minimal
    assert "state" not in minimal
