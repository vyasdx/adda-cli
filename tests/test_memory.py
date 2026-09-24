# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""`adda memory` - an agent's memory drifts like docs do (ENH-ADDA-029).

Each rule comes from a real incident in this project's own memory:
BUG-ADDA-024 orphaned three files (on disk, absent from the index the agent
loads), and RF-ADDA-009 found one fact recorded twice, where the copy marked
for deletion was the correct one.
"""

import json

from typer.testing import CliRunner

from adda.cli import app
from adda.memory import memory_report

runner = CliRunner()


def _note(d, stem, name=None, description="d", body=""):
    fm = f"---\nname: {name or stem}\ndescription: {description}\n---\n\n{body}"
    (d / f"{stem}.md").write_text(fm, encoding="utf-8")


def _index(d, *stems, extra=""):
    lines = ["# Memory Index", ""] + [f"- [{s}]({s}.md) — hook" for s in stems]
    (d / "MEMORY.md").write_text("\n".join(lines) + "\n" + extra, encoding="utf-8")


def _issues(findings):
    return sorted((f["issue"], f["item"]) for f in findings)


def test_consistent_memory_is_clean_and_says_how_much_it_checked(tmp_path):
    _note(tmp_path, "a", description="one", body="see [[b]]")
    _note(tmp_path, "b", description="two")
    _index(tmp_path, "a", "b")
    findings, skipped, stats = memory_report(tmp_path)
    assert findings == [] and skipped == []
    assert stats == {"files": 2, "entries": 2, "links": 1}


def test_file_missing_from_the_index_is_invisible_to_the_agent(tmp_path):
    # BUG-ADDA-024: the index was overwritten and three files fell out of it.
    _note(tmp_path, "a", description="one")
    _note(tmp_path, "b", description="two")
    _index(tmp_path, "a")
    assert _issues(memory_report(tmp_path)[0]) == [("not indexed", "b.md")]


def test_index_entry_pointing_at_nothing_is_flagged(tmp_path):
    _note(tmp_path, "a")
    _index(tmp_path, "a", "gone")
    assert _issues(memory_report(tmp_path)[0]) == [("index entry dangling", "gone.md")]


def test_file_indexed_twice_is_flagged(tmp_path):
    _note(tmp_path, "a")
    _index(tmp_path, "a", "a")
    assert _issues(memory_report(tmp_path)[0]) == [("indexed twice", "a.md")]


def test_wiki_link_to_no_memory_is_flagged_with_its_line(tmp_path):
    _note(tmp_path, "a", body="intro\nrelated: [[missing-thing]]\n")
    _index(tmp_path, "a")
    findings = memory_report(tmp_path)[0]
    assert [(f["issue"], f["item"], f["ref"]) for f in findings] == [
        ("link dangling", "a.md:7", "missing-thing")
    ]


def test_wiki_link_resolves_by_frontmatter_name_or_filename(tmp_path):
    _note(tmp_path, "file-stem", name="the-name", body="[[the-name]] [[file-stem]]")
    _index(tmp_path, "file-stem")
    assert memory_report(tmp_path)[0] == []


def test_same_name_twice_is_one_fact_recorded_twice(tmp_path):
    # RF-ADDA-009: two records of one fact drift apart; nothing said so.
    _note(tmp_path, "silo1-is-primary", name="primary-machine", description="one")
    _note(tmp_path, "adda-primary", name="primary-machine", description="two")
    _index(tmp_path, "silo1-is-primary", "adda-primary")
    assert _issues(memory_report(tmp_path)[0]) == [
        ("duplicate name", "adda-primary.md, silo1-is-primary.md")
    ]


def test_same_description_twice_is_flagged(tmp_path):
    _note(tmp_path, "a", description="Work happens on silo1")
    _note(tmp_path, "b", description="work happens on  silo1.")
    _index(tmp_path, "a", "b")
    assert _issues(memory_report(tmp_path)[0]) == [("duplicate description", "a.md, b.md")]


def test_links_inside_code_fences_and_external_urls_are_not_entries(tmp_path):
    _note(tmp_path, "a", body="```\n[[not-a-link]]\n```\n")
    _index(tmp_path, "a", extra="- [guide](https://example.com/guide.md) — external, and ends in .md\n")
    findings, _, stats = memory_report(tmp_path)
    assert findings == [] and stats["entries"] == 1


def test_no_index_is_reported_not_passed(tmp_path):
    _note(tmp_path, "a")
    findings, skipped, _ = memory_report(tmp_path)
    assert findings == []
    assert any("MEMORY.md" in s for s in skipped)


def test_index_name_can_be_chosen(tmp_path):
    _note(tmp_path, "a")
    (tmp_path / "INDEX.md").write_text("- [a](a.md)\n", encoding="utf-8")
    findings, skipped, stats = memory_report(tmp_path, index="INDEX.md")
    assert findings == [] and skipped == [] and stats["entries"] == 1


def test_cli_exits_one_on_findings_and_prints_counts(tmp_path):
    _note(tmp_path, "a")
    _note(tmp_path, "b")
    _index(tmp_path, "a")
    res = runner.invoke(app, ["memory", str(tmp_path)])
    assert res.exit_code == 1
    assert "not indexed" in res.stdout and "b.md" in res.stdout
    assert "2 file(s)" in res.stdout


def test_cli_json_and_clean_exit(tmp_path):
    _note(tmp_path, "a")
    _index(tmp_path, "a")
    res = runner.invoke(app, ["memory", str(tmp_path), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["findings"] == [] and data["stats"]["files"] == 1


def test_missing_directory_fails_clearly(tmp_path):
    res = runner.invoke(app, ["memory", str(tmp_path / "nope")])
    assert res.exit_code == 1
    assert "not a directory" in res.stdout.lower()
