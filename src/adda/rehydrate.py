# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""The north-star: emit the MINIMAL OKF to restore an LLM's architectural memory
after a context compaction (spec §13).

Minimal = project/version + constraints + active modules + active (in-force) ADRs.
Everything else in the full OKF (overview, domain model, API contracts, state,
and any planned/deprecated/superseded items) is intentionally dropped to keep the
payload small.
"""

from adda.okf import OKF, active_decisions, active_modules


def minimal_okf(okf: OKF) -> dict:
    """Build the minimal-OKF dict the LLM needs to regain its architecture memory."""
    return {
        "okf_version": okf.okf_version,
        "project": okf.project,
        "version": okf.version,
        "constraints": list(okf.constraints),
        "modules": [m.model_dump() for m in active_modules(okf)],
        "decisions": [d.model_dump() for d in active_decisions(okf)],
    }
