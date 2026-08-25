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

from adda.okf import OKF, active_decisions, active_modules
from adda.rehydrate import minimal_okf


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


def evaluate(okf: OKF) -> dict:
    """Compute the rehydration-fidelity report for an OKF."""
    full = _full_facts(okf)
    mini = _minimal_facts(okf)
    load_bearing = _load_bearing_facts(okf)

    full_json = json.dumps(okf.model_dump(), ensure_ascii=False)
    mini_json = json.dumps(minimal_okf(okf), ensure_ascii=False)

    return {
        "overall_fidelity_pct": _pct(len(full & mini), len(full)),
        "load_bearing_fidelity_pct": _pct(len(load_bearing & mini), len(load_bearing)),
        "facts_total": len(full),
        "facts_preserved": len(full & mini),
        "dropped": sorted(full - mini),
        "payload_reduction_pct": _pct(len(full_json) - len(mini_json), len(full_json)),
        "full_chars": len(full_json),
        "minimal_chars": len(mini_json),
    }
