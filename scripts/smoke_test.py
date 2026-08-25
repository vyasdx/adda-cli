# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""ADDA v0.1.0 smoke test — runs the closed loop end to end and asserts each step.

Run with the same interpreter whose environment has `adda` installed:

    python scripts/smoke_test.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _adda() -> str:
    """Resolve the `adda` console script that sits next to the running interpreter."""
    scripts = Path(sys.executable).parent
    exe = scripts / ("adda.exe" if os.name == "nt" else "adda")
    return str(exe) if exe.exists() else "adda"


ADDA = _adda()
FAILS = []


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([ADDA, *args], capture_output=True, text=True)


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"

        r = run("init", str(proj))
        check("init scaffolds adda/", r.returncode == 0 and (proj / "adda" / "VERSION.md").is_file(), r.stderr)

        r = run("export", str(proj), "--okf")
        okf_path = proj / "okf.json"
        ok = r.returncode == 0 and okf_path.is_file()
        if ok:
            data = json.loads(okf_path.read_text(encoding="utf-8"))
            ok = data["project"] == "My Project" and len(data["architecture"]["modules"]) == 3
        check("export -> valid OKF JSON", ok, r.stderr)

        r = run("monitor", "--tokens", "130000", "--limit", "200000")
        check("monitor 65% -> CHECKPOINT", r.returncode == 0 and "CHECKPOINT" in r.stdout, r.stdout + r.stderr)

        r = run("rehydrate", str(proj))
        ok = r.returncode == 0
        if ok:
            mini = json.loads(r.stdout)
            ok = (
                [m["name"] for m in mini["modules"]] == ["core", "api"]  # active only
                and "architecture" not in mini                          # minimal
                and mini["constraints"]
            )
        check("rehydrate -> minimal, active-only OKF", ok, r.stdout + r.stderr)

        r = run("checkpoint", str(proj), "-m", "smoke")
        snaps = list((proj / "adda" / "STATE" / "checkpoints").glob("*.md"))
        check("checkpoint -> timestamped snapshot", r.returncode == 0 and len(snaps) == 1, r.stderr)

    print()
    if FAILS:
        print(f"SMOKE TEST FAILED: {len(FAILS)} step(s) failed -> {', '.join(FAILS)}")
        return 1
    print("SMOKE TEST PASSED: closed loop (init -> export -> monitor -> rehydrate -> checkpoint) works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
