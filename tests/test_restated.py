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


# ENH-ADDA-062: mutation testing found 74 of 306 changes to restated.py that no
# test noticed. Every test above edits one line in place, so removed and added
# line numbers were always equal, and none checked a hit's fields exactly.

COPY = "nightly deploy runs on the blue cluster at nine every evening"


def test_a_hit_reports_exact_fields_when_lines_shift(tmp_path):
    # Two lines prepended and two removed: old and new line numbers differ.
    # The copy appears twice on one line: two spans, one hit, the longest.
    _repo(tmp_path, {"ops.md": f"# Ops\n\nIntro.\n{OLD}\n", "guide.md": f"# Guide\n\n{OLD} {OLD}\n"})
    _commit(tmp_path, {"ops.md": f"Preface one.\nPreface two.\n# Ops\n\n{NEW}\n"}, "fix")
    current, records, _ = restated_report(tmp_path, "HEAD")
    assert records == []
    assert current == [{"file": "guide.md", "line": 3, "source": "ops.md:4", "words": 11, "text": COPY}]


def test_a_renamed_file_is_compared_with_its_old_self(tmp_path):
    body = "# Ops\n\nLine about things.\nLine about stuff.\nLine about more.\n"
    _repo(tmp_path, {"ops.md": f"{body}{OLD}\n", "guide.md": f"{OLD}\n"})
    _commit(tmp_path, {"ops.md": None, "runbook.md": f"{body}{NEW}\n"}, "rename and fix")
    current = restated_report(tmp_path, "HEAD")[0]
    assert [(h["file"], h["source"]) for h in current] == [("guide.md", "ops.md:6")]


def test_which_files_are_searched(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "docs/guide.md": f"{OLD}\n", "notes.txt": f"{OLD}\n",
                     "page.rst": f"{OLD}\n", "logs/run.md": f"{OLD}\n", "app.py": f"X = '{OLD}'\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert _where(restated_report(tmp_path, "HEAD")[0]) == ["docs/guide.md:1", "notes.txt:1", "page.rst:1"]


def test_six_words_are_enough_and_line_is_where_the_phrase_starts(tmp_path):
    # No trailing newline: the last word of the file must be read whole.
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": "Intro.\nThe\nnightly\ndeploy runs on the blue"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    current = restated_report(tmp_path, "HEAD")[0]
    assert [(h["line"], h["words"]) for h in current] == [(3, 6)]


def test_prose_after_a_fence_history_and_tables(tmp_path):
    guide = ("```\ncode\n```\n\n"                                  # prose after a fence counts
             f"{OLD}\n\n"                                          # line 5
             "## Change Log\n\n### 2026\n\n"                       # a subsection stays history
             f"- {OLD}\n\n"
             "## Current\n\n"                                      # a same-level heading ends it
             f"{OLD}\n\n"                                          # line 15
             "| the nightly deploy runs on |\n| the blue cluster at nine |\n\n"  # rows break phrases
             "the nightly deploy runs on\n---\nthe blue cluster at nine\n---\nevery evening\n")
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": guide})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    assert _where(restated_report(tmp_path, "HEAD")[0]) == ["guide.md:15", "guide.md:5"]


def test_a_fact_split_across_lines_when_only_its_second_line_changes(tmp_path):
    _repo(tmp_path, {"ops.md": "The nightly deploy runs on the blue cluster at\nnine every evening.\n",
                     "guide.md": f"{OLD}\n"})
    _commit(tmp_path, {"ops.md": "The nightly deploy runs on the blue cluster at\nten every evening.\n"}, "fix")
    current = restated_report(tmp_path, "HEAD")[0]
    assert [(h["source"], h["words"], h["text"]) for h in current] == [
        ("ops.md:1", 8, "on the blue cluster at nine every evening")]


def test_one_commit_touching_several_files(tmp_path):
    # a.md loses a short line (nothing to search), b.md is new, tool.py is code,
    # and a move into c-new.md is followed by an unrelated addition to d.md.
    _repo(tmp_path, {"a.md": "x\nkeep this line\n", "d.md": "Old notes.\n", "ops.md": f"{OLD}\n",
                     "keep.md": f"# Keep\n\n{OLD.replace('nightly', 'weekly')}\n",
                     "tool.py": "x = 1\n", "guide.md": f"{OLD}\n"})
    _commit(tmp_path, {"a.md": "keep this line\n", "b.md": "Brand new file.\n", "tool.py": "x = 2\n",
                       "keep.md": "# Keep\n", "c-new.md": f"{OLD.replace('nightly', 'weekly')}\n",
                       "d.md": "Old notes.\nNew unrelated line here for the record.\n",
                       "ops.md": f"{NEW}\n"}, "several")
    assert _where(restated_report(tmp_path, "HEAD")[0]) == ["guide.md:1"]


def test_a_dated_line_marks_only_itself(tmp_path):
    _repo(tmp_path, {"ops.md": f"{OLD}\n", "guide.md": f"**[2026-09-01]** a dated note.\n{OLD}\n"})
    _commit(tmp_path, {"ops.md": f"{NEW}\n"}, "fix")
    current, records, _ = restated_report(tmp_path)  # rev defaults to HEAD
    assert _where(current) == ["guide.md:2"] and records == []


def test_a_move_into_a_file_that_gains_several_lines(tmp_path):
    _repo(tmp_path, {"a.md": f"# A\n\n{OLD}\n", "b.md": "# B\n"})
    _commit(tmp_path, {"a.md": "# A\n", "b.md": f"# B\nA new first line.\n{OLD}\n"}, "move it")
    assert restated_report(tmp_path, "HEAD")[:2] == ([], [])


def test_not_a_git_repo_fails_clearly(tmp_path):
    res = runner.invoke(app, ["restated", str(tmp_path)])
    assert res.exit_code == 1 and "git" in res.stdout.lower()
