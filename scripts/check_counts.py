# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Fail when a published count no longer matches what the repo actually holds.

ENH-ADDA-020. The README's test badge is a claim about this repository, kept by
hand, and it drifted five times (66, 67, 75, 76, 82) — twice while fixing an
unrelated bug. A hand-maintained number is forged by forgetting, which is this
project's entire thesis pointed at itself.

Two counts are checked:

- the tests badge in README.md, against what pytest actually collects
- the version, which is written by hand in four places: `pyproject.toml`,
  `src/adda/__init__.py`, `adda/VERSION.md` and the README badge. A release
  publishes an immutable version number, so a disagreement between them is
  worse than a stale badge
- any `<dir>/status.md` that claims "N open work items", against the `issues.md`
  beside it. Discovered by glob rather than by naming a directory, so this file
  stays publishable and works in any repo that keeps a tracker that way.

It REPORTS and FAILS rather than rewriting the files. Auto-correcting a stale
number makes the drift invisible, and the point is to notice — the same reason
`audit` reports a stale doc instead of touching it.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collected_tests() -> int:
    """How many tests pytest actually collects, straight from pytest."""
    # `src` on the path so this runs the same on a bare clone as it does in CI,
    # where `pip install -e .` has already made the package importable.
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        filter(None, [str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]))}
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=300, env=env,
    )
    m = re.search(r"^(\d+) tests? collected", out.stdout, re.M)
    if not m:
        # Never guess. An uncountable suite is a failed check, not a pass.
        sys.exit(f"could not read a test count from pytest:\n{out.stdout[-800:]}")
    return int(m.group(1))


def check_badge(actual: int) -> list:
    """The badge states the number twice — in the URL and in the alt text."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    found = [int(n) for n in re.findall(r"tests-(\d+)%20passing", readme)]
    found += [int(n) for n in re.findall(r'alt="tests (\d+) passing"', readme)]
    if not found:
        return ["README.md: no tests badge found — it was removed or renamed"]
    return [
        f"README.md badge says {n} tests, pytest collects {actual}"
        for n in sorted(set(found)) if n != actual
    ]


def check_version() -> list:
    """pyproject is the source of truth; three other files restate it by hand.

    `src/adda/__init__.py` already drifted once and shipped in a release
    (BUG-ADDA-006). A version is the one number that cannot be corrected after
    the fact, because PyPI will not let a version be reused.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Plain-text read: tomllib is 3.11+, and this must run on the 3.10 floor.
    truth = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)

    others = {
        "src/adda/__init__.py": r'__version__\s*=\s*"([^"]+)"',
        "adda/VERSION.md": r"^version:\s*(\S+)",
        "README.md": r"badge/version-([0-9][^-]*)-",
    }
    problems = []
    for rel, pattern in others.items():
        path = ROOT / rel
        if not path.is_file():
            continue
        m = re.search(pattern, path.read_text(encoding="utf-8"), re.M)
        if not m:
            problems.append(f"{rel}: no version found - it was renamed or removed")
        elif m.group(1) != truth:
            problems.append(f"{rel} says {m.group(1)}, pyproject says {truth}")
    return problems


def check_open_items() -> list:
    """Cross-check every tracker that publishes an open-item count.

    A `## Active` row whose Status cell starts with "open" is live work;
    the rest are accepted decisions kept as a record. The rule is structural,
    not positional — mixing live work with history in one table is exactly how
    14 closed rows once hid inside it (RF-ADDA-008).
    """
    problems = []
    for status in sorted(ROOT.glob("*/status.md")):
        issues = status.with_name("issues.md")
        if not issues.is_file():
            continue
        claimed = re.findall(
            r"\*\*(\d+) open work items?\.?\*\*", status.read_text(encoding="utf-8")
        )
        if not claimed:
            continue  # states no count; nothing to contradict
        text = issues.read_text(encoding="utf-8")
        if "## Active" not in text or "## Recently Closed" not in text:
            continue
        active = text[text.index("## Active"):text.index("## Recently Closed")]
        live = [
            ln for ln in active.splitlines()
            if ln.startswith("| ")
            and ln.rsplit("|", 2)[-2].strip().lower().startswith("open")
        ]
        n = int(claimed[0])  # newest entry sits at the top
        if n != len(live):
            rel = status.relative_to(ROOT).as_posix()
            problems.append(
                f"{rel} claims {n} open work items; {issues.name} has {len(live)}"
            )
    return problems


def main() -> int:
    actual = collected_tests()
    problems = check_badge(actual) + check_version() + check_open_items()
    if problems:
        print("Stale published counts:")
        for p in problems:
            print("  " + p)
        return 1
    print(f"counts current: {actual} tests, version consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
