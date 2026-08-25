# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""MODULE_MAP.json loading, path normalisation and exempt-glob matching."""

import json

import pytest

from adda.modulemap import MAP_FILENAME, is_exempt, load_map


def _write_map(adda_dir, mapping, exempt=()):
    adda_dir.mkdir(parents=True, exist_ok=True)
    (adda_dir / MAP_FILENAME).write_text(
        json.dumps({"map": mapping, "exempt": list(exempt)}), encoding="utf-8"
    )


def test_load_map_returns_mapping_and_exempt(tmp_path):
    adda = tmp_path / "adda"
    _write_map(adda, {"src/adda/cli.py": "docs/modules/cli.md"}, ["src/adda/__init__.py"])
    mapping, exempt = load_map(adda)
    assert mapping == {"src/adda/cli.py": "docs/modules/cli.md"}
    assert exempt == ["src/adda/__init__.py"]


def test_load_map_normalises_windows_separators(tmp_path):
    # The map may be hand-edited on Windows; both sides must normalise to posix.
    adda = tmp_path / "adda"
    _write_map(adda, {"src\\adda\\cli.py": "docs\\modules\\cli.md"})
    mapping, _ = load_map(adda)
    assert mapping == {"src/adda/cli.py": "docs/modules/cli.md"}


def test_load_map_missing_file_raises(tmp_path):
    adda = tmp_path / "adda"
    adda.mkdir()
    with pytest.raises(FileNotFoundError):
        load_map(adda)


def test_load_map_absent_keys_default_to_empty(tmp_path):
    adda = tmp_path / "adda"
    adda.mkdir()
    (adda / MAP_FILENAME).write_text("{}", encoding="utf-8")
    assert load_map(adda) == ({}, [])


def test_is_exempt_matches_exact_and_recursive_glob():
    exempt = ["src/adda/__init__.py", "src/adda/templates/**"]
    assert is_exempt("src/adda/__init__.py", exempt)
    assert is_exempt("src/adda/templates/adda/VERSION.md", exempt)
    assert is_exempt("src/adda/templates/adda/STATE/CURRENT.md", exempt)
    assert not is_exempt("src/adda/cli.py", exempt)


def test_is_exempt_empty_list_matches_nothing():
    assert not is_exempt("src/adda/cli.py", [])


def test_is_exempt_is_case_sensitive_on_every_platform():
    # fnmatch() would normcase and match this on Windows but not on Linux.
    # Enforcement must not depend on the developer's OS.
    assert not is_exempt("src/ADDA/Templates/x.py", ["src/adda/templates/**"])
    assert is_exempt("src/adda/templates/x.py", ["src/adda/templates/**"])
