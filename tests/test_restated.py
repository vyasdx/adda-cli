# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""`adda restated` - a corrected fact left standing elsewhere (ENH-ADDA-031).

Given a commit, list the other files that still state, word for word, what the
commit removed. Built from a prototype run over this repo's last 40 commits:
about half its hits needed an edit and nearly all were worth reading, so it is
advisory and run on purpose - and it finds copies, never paraphrases.
"""

import json
import subprocess

from typer.testing import CliRunner

from adda.cli import app
from adda.restated import restated_report

runner = CliRunner()

OLD = "The nightly deploy runs on the blue cluster at nine every evening."
NEW = "The nightly deploy runs on the green cluster at ten every evening."


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(root, files):
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    _commit(root, files, "first")


def _commit(root, files, message):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            p.unlink()
        else:
            p.write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)


def _where(hits):
    return sorted(f"{h['file']}:{h['line']}" for h in hits)


def test_corrected_fact_left_standing_elsewhere_is_reported(tmp_path):
    _repo(tmp_path, {"ops.md": f"# Ops\n\n{OLD}\n", "README.md": f"# Readme\n\nIntro.\n\n{OLD}\n"})
    _commit(tmp_path, {"ops.md": f"# Ops\n\n{NEW}\n"}, "correct the cluster")
    current, records, skipped = restated_report(tmp_path, "HEAD")
    assert _where(current) == ["README.md:5"] and records == [] and skipped == []
    assert current[0]["source"] == "ops.md:3"


def test_nothing_left_standing_is_clean(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "README.md": "Unrelated text about something else.\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_unchanged_part_of_a_corrected_sentence_is_not_a_restatement(tmp_path):
    # Only the words the correction removed count; the sentence's unchanged
    # opening ("the nightly deploy runs on the") is still true.
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": "The nightly deploy runs on the schedule below.\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_moved_text_is_not_a_retraction(tmp_path):
    _repo(tmp_path, {"a.md": f"# A\n\n{OLD}\n", "keep.md": "x\n"})
    _commit(tmp_path, {"a.md": "# A\n", "b.md": f"# B\n\n{OLD}\n"}, "move the paragraph")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_code_and_fenced_blocks_are_not_searched(tmp_path):
    # Code idioms were nearly all of the prototype's false alarms.
    _repo(tmp_path, {
        "ops.md": f"{OLD}\n",
        "tool.py": f"HELP = \"{OLD}\"\n",  # a string, not a comment: `#` reads as a heading
        "guide.md": f"```\n{OLD}\n```\n",
    })
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_logs_checkpoints_and_history_sections_are_left_alone(tmp_path):
    _repo(tmp_path, {
        "ops.md": f"{OLD}\n",
        "notes/log/2026-09-01.md": f"{OLD}\n",
        "state/checkpoints/snap.md": f"{OLD}\n",
        "CHANGELOG.md": f"{OLD}\n",
        "guide.md": f"# Guide\n\n## Change Log\n\n- {OLD}\n",
    })
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_dated_records_are_reported_separately(tmp_path):
    _repo(tmp_path, {
        "ops.md": f"{OLD}\n",
        "status.md": f"**[2026-09-01]** {OLD}\n",
        "issues.md": f"| X-1 | {OLD} | closed 2026-09-02 |\n",
        "old-handover.md": f"# Handover\n\n> SUPERSEDED by the new one.\n\n{OLD}\n",
        "guide.md": f"{OLD}\n",
    })
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    current, records, _ = restated_report(tmp_path, "HEAD")
    assert _where(current) == ["guide.md:1"]
    assert _where(records) == ["issues.md:1", "old-handover.md:5", "status.md:1"]


def test_short_phrases_are_not_matched(tmp_path):
    _repo(tmp_path, {"ops.md": "Use the blue cluster.\n", "guide.md": "Use the blue cluster.\n"})
    _commit(tmp_path, {"ops.md": "Use the green cluster.\n"}, "fix")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_an_untracked_directory_can_be_searched_too(tmp_path):
    # The real incident's fourth copy lived in agent memory, outside the repo.
    repo, memory = tmp_path / "repo", tmp_path / "memory"
    repo.mkdir()
    memory.mkdir()
    (memory / "fact.md").write_text(f"---\nname: fact\n---\n\n{OLD}\n", encoding="utf-8")
    _repo(repo, {"ops.md": f"{OLD}\n"})
    _commit(repo, {"ops.md": f"{NEW}\n"}, "fix")
    assert restated_report(repo, "HEAD")[0] == []
    current = restated_report(repo, "HEAD", also=[memory])[0]
    assert [(h["file"], h["line"]) for h in current] == [(f"{memory.as_posix()}/fact.md", 5)]


def test_an_older_correction_is_checked_against_the_repo_as_it_is_now(tmp_path):
    # "Still stated" means now: a copy fixed after the correction is not reported.
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": f"{OLD}\n", "faq.md": f"{OLD}\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "correct ops")
    _commit(tmp_path, {"guide.md": f"{NEW}\n"}, "later: fix the guide too")
    current = restated_report(tmp_path, "HEAD~1")[0]
    assert _where(current) == ["faq.md:1"]


def test_root_commit_cannot_be_compared_and_says_so(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n"})
    current, records, skipped = restated_report(tmp_path, "HEAD")
    assert current == [] and records == []
    assert any("no parent" in s for s in skipped)


def test_cli_exits_one_only_for_current_files(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "status.md": f"[2026-09-01] {OLD}\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    res = runner.invoke(app, ["restated", str(tmp_path)])
    assert res.exit_code == 0  # a dated record is history, not something to fix
    assert "status.md:1" in res.stdout

    _commit(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": f"{OLD}\n"}, "restore")
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix again")
    res = runner.invoke(app, ["restated", str(tmp_path), "--rev", "HEAD"])
    assert res.exit_code == 1 and "guide.md:1" in res.stdout
    assert "copies, not paraphrases" in res.stdout


def test_cli_json(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": f"{OLD}\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    data = json.loads(runner.invoke(app, ["restated", str(tmp_path), "--json"]).stdout)
    assert [h["file"] for h in data["current"]] == ["guide.md"] and data["records"] == []


def test_not_a_git_repo_fails_clearly(tmp_path):
    res = runner.invoke(app, ["restated", str(tmp_path)])
    assert res.exit_code == 1 and "git" in res.stdout.lower()
