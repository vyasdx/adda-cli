# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""Measure ADDA against real repositories and emit a markdown table.

ENH-ADDA-015. The point is to replace self-reported numbers measured on ADDA's
own scaffold with numbers measured on codebases ADDA did not design.

WHAT THIS CAN AND CANNOT MEASURE, because the distinction matters:

- Mapping scale, collision count and wall time are measurable on ANY repository.
  Those are properties of the tool.
- Rehydration fidelity is NOT. It scores how much authored architecture memory
  survives `rehydrate`, so it needs a curated `/adda` — which real repositories
  do not have. Running `adda init` first would produce a fidelity number for an
  empty scaffold, which measures the template rather than the tool. So fidelity
  is reported only where real `/adda` memory exists, and left blank elsewhere
  rather than filled with a flattering placeholder.

Usage:
    python benchmarks/run.py <repo> [<repo> ...]
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adda.evaluate import evaluate          # noqa: E402
from adda.okf import compile_okf            # noqa: E402
from adda.sync import discover_modules, module_map_json   # noqa: E402


def _sha(repo: Path) -> str:
    """Short SHA of the benchmarked checkout, so a run is reproducible in time.

    Without it the table is mechanically reproducible but not scientifically:
    someone running this next month benchmarks different code and gets
    different numbers with no way to tell why.
    """
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def measure(repo: Path) -> dict:
    t0 = time.perf_counter()
    modules = discover_modules(repo)
    mapping = json.loads(module_map_json(repo))
    elapsed = time.perf_counter() - t0

    docs = list(mapping["map"].values())
    row = {
        "repo": repo.name,
        "sha": _sha(repo),
        "modules": len(modules),
        "mapped": len(docs),
        "exempt": len(mapping["exempt"]),
        "collisions": len(docs) - len(set(docs)),
        "seconds": round(elapsed, 2),
        "load_bearing": None,
        "overall": None,
        "payload_cut": None,
    }

    adda_dir = repo / "adda"
    if (adda_dir / "VERSION.md").is_file():
        r = evaluate(compile_okf(adda_dir))
        row["load_bearing"] = r["load_bearing_fidelity_pct"]
        row["overall"] = r["overall_fidelity_pct"]
        row["payload_cut"] = r["payload_reduction_pct"]
    return row


def render(rows: list) -> str:
    out = [
        "| repo | commit | modules | mapped | exempt | collisions | time | load-bearing | overall | payload cut |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        fid = f'{r["load_bearing"]}%' if r["load_bearing"] is not None else "n/a"
        ov = f'{r["overall"]}%' if r["overall"] is not None else "n/a"
        pc = f'{r["payload_cut"]}%' if r["payload_cut"] is not None else "n/a"
        out.append(
            f'| {r["repo"]} | `{r["sha"]}` | {r["modules"]} | {r["mapped"]} | {r["exempt"]} '
            f'| {r["collisions"]} | {r["seconds"]}s | {fid} | {ov} | {pc} |'
        )
    return "\n".join(out)


def main(paths: list) -> int:
    rows = [measure(Path(p).resolve()) for p in paths]
    print(render(rows))
    bad = [r for r in rows if r["collisions"]]
    if bad:
        print(f"\nFAIL: {len(bad)} repo(s) produced colliding doc paths: "
              f"{', '.join(r['repo'] for r in bad)}")
        return 1
    print(f"\n{len(rows)} repo(s), 0 collisions.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1:]))
