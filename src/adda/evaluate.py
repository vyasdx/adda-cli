# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""adda eval — rehydration fidelity % (spec §6.5 item 4).

Turns `rehydrate` from a vibe into a metric. It is a DETERMINISTIC, offline
content-preservation measure (no LLM call) so it is reproducible and stays in
ADDA's lane (a context/memory tool, not an LLM executor — the §6.5 scope guard).

It enumerates the architecture "facts" in the full OKF (the full-context baseline)
and checks how many survive into the minimal OKF that `rehydrate` emits:

- overall_fidelity_pct      — fraction of ALL facts retained (dropping prose like
                              domain model / API contracts / inactive items is the
                              intended compression trade-off, so this is < 100%).
- load_bearing_fidelity_pct — fraction of the load-bearing facts (constraints,
                              active modules, active ADRs, project/version) retained.
                              This MUST be 100%: it proves rehydrate loses none of
                              the critical architecture memory. A regression here is
                              a real bug.
"""

import json
from pathlib import Path

from adda.okf import OKF, active_decisions, active_modules
from adda.rehydrate import minimal_okf

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "adda"

# Scaffold files that produce OKF facts. `PROMPT_BASE/SYSTEM.md` is excluded:
# it is a prompt preamble, not architecture memory, so leaving it at its default
# says nothing about whether the memory was authored.
FACT_BEARING = (
    "VERSION.md", "ARCHITECTURE.md", "DOMAIN_MODEL.md",
    "API_CONTRACTS.md", "STATE/CURRENT.md",
)


def _same_as_template(adda_dir: Path, rel: str) -> bool:
    """True when the scaffold file is still byte-identical to what `init` wrote.

    Line endings are normalised: `init` copies the template, but a checkout on
    Windows can rewrite them, and a doc that differs only in CRLF was not
    authored by anyone.
    """
    live, tmpl = adda_dir / rel, TEMPLATE_DIR / rel
    if not live.is_file() or not tmpl.is_file():
        return False
    try:
        a = [ln.rstrip() for ln in live.read_text(encoding="utf-8").splitlines()]
        b = [ln.rstrip() for ln in tmpl.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError):
        return False
    return a == b


def unauthored_files(adda_dir: Path) -> list:
    """Fact-bearing scaffold files nobody has written into yet.

    BUG-ADDA-021. `adda eval` on a fresh `adda init` reported a confident
    "58.3% overall, 100.0% load-bearing" computed entirely from template
    placeholder text — and that number is where the README's long-standing
    stale 58% came from. It measured the template, not the tool, and said so
    nowhere. A fidelity score over memory nobody wrote is not a low score, it
    is not a score at all.
    """
    return [rel for rel in FACT_BEARING if _same_as_template(adda_dir, rel)]


def _full_facts(okf: OKF) -> set:
    facts = set()
    if okf.project:
        facts.add("project")
    if okf.version:
        facts.add("version")
    facts.update(f"constraint:{i}" for i, _ in enumerate(okf.constraints))
    facts.update(f"module:{m.name}" for m in okf.architecture.modules)
    facts.update(f"decision:{d.id}" for d in okf.decisions)
    if okf.architecture.overview.strip():
        facts.add("overview")
    if okf.architecture.domain_model.strip():
        facts.add("domain_model")
    if okf.architecture.api_contracts.strip():
        facts.add("api_contracts")
    if okf.state.summary.strip() or okf.state.updated.strip():
        facts.add("state")
    return facts


def _minimal_facts(okf: OKF) -> set:
    mini = minimal_okf(okf)
    facts = set()
    if mini["project"]:
        facts.add("project")
    if mini["version"]:
        facts.add("version")
    facts.update(f"constraint:{i}" for i, _ in enumerate(mini["constraints"]))
    facts.update(f"module:{m['name']}" for m in mini["modules"])
    facts.update(f"decision:{d['id']}" for d in mini["decisions"])
    return facts


def _load_bearing_facts(okf: OKF) -> set:
    facts = set()
    if okf.project:
        facts.add("project")
    if okf.version:
        facts.add("version")
    facts.update(f"constraint:{i}" for i, _ in enumerate(okf.constraints))
    facts.update(f"module:{m.name}" for m in active_modules(okf))
    facts.update(f"decision:{d.id}" for d in active_decisions(okf))
    return facts


def _pct(part: int, whole: int) -> float:
    return 100.0 if whole == 0 else round(100 * part / whole, 1)


def evaluate(okf: OKF, adda_dir=None) -> dict:
    """Compute the rehydration-fidelity report for an OKF.

    Pass `adda_dir` to have the report say whether the memory was authored at
    all. Without it the percentages are reported as before — callers that hold
    only an OKF cannot know where it came from.
    """
    full = _full_facts(okf)
    mini = _minimal_facts(okf)
    load_bearing = _load_bearing_facts(okf)

    full_json = json.dumps(okf.model_dump(), ensure_ascii=False)
    mini_json = json.dumps(minimal_okf(okf), ensure_ascii=False)

    unauthored = unauthored_files(Path(adda_dir)) if adda_dir is not None else []
    # Every fact-bearing file still untouched: there is no authored memory to
    # score, so there is no number. Reporting one would measure the template.
    # ponytail: three-state, like the staleness check - a metric that cannot be
    # computed says so instead of printing something confident and wrong.
    scored = len(unauthored) < len(FACT_BEARING)

    return {
        "overall_fidelity_pct": _pct(len(full & mini), len(full)) if scored else None,
        "load_bearing_fidelity_pct": (
            _pct(len(load_bearing & mini), len(load_bearing)) if scored else None
        ),
        "unauthored_template_files": unauthored,
        "facts_total": len(full),
        "facts_preserved": len(full & mini),
        "dropped": sorted(full - mini),
        "payload_reduction_pct": _pct(len(full_json) - len(mini_json), len(full_json)),
        "full_chars": len(full_json),
        "minimal_chars": len(mini_json),
    }
