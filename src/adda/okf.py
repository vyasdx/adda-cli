# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""OKF (Open Knowledge Format): the pydantic schema plus the /adda markdown -> OKF compiler.

OKF is deliberately provider-agnostic — it carries no Claude/Codex/Copilot-specific
fields, so the same JSON feeds any LLM (spec §12).
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field

OKF_VERSION = "0.2"

# A decision is "in force" (emitted by rehydrate) only in these statuses.
ACTIVE_DECISION_STATUSES = {"accepted", "active"}


class Module(BaseModel):
    name: str
    description: str = ""
    status: str = "active"  # active | planned | deprecated
    path: str = ""  # repo path this module maps to (used by `adda sync`/`adda diff`)


class Decision(BaseModel):
    id: str
    title: str = ""
    status: str = "accepted"  # accepted | proposed | superseded | rejected


class State(BaseModel):
    updated: str = ""
    summary: str = ""


class Architecture(BaseModel):
    overview: str = ""
    modules: list[Module] = Field(default_factory=list)
    domain_model: str = ""
    api_contracts: str = ""


class OKF(BaseModel):
    okf_version: str = OKF_VERSION
    project: str = ""
    version: str = ""
    architecture: Architecture = Field(default_factory=Architecture)
    constraints: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    state: State = Field(default_factory=State)


# --- active-item helpers (used by rehydrate) -------------------------------

def active_modules(okf: OKF) -> list[Module]:
    return [m for m in okf.architecture.modules if m.status.lower() == "active"]


def active_decisions(okf: OKF) -> list[Decision]:
    return [d for d in okf.decisions if d.status.lower() in ACTIVE_DECISION_STATUSES]


# --- tiny markdown parsing (stdlib only) -----------------------------------

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_KV = re.compile(r"^(\w+):\s*(.*\S)?\s*$")
_BULLET = re.compile(r"^-\s+(.*\S)\s*$")
_H1 = re.compile(r"^#\s+(.*\S)\s*$")
_TRAILING_STATUS = re.compile(r"\(([^)]*)\)\s*$")
_TRAILING_PATH = re.compile(r"\[([^\]]*)\]\s*$")


def _read(path: Path) -> str:
    """File text with HTML comments stripped, or '' if the file is absent."""
    if not path.is_file():
        return ""
    return _COMMENT.sub("", path.read_text(encoding="utf-8"))


def _kv(text: str) -> dict:
    """Parse `key: value` lines (ignores bullets and headings)."""
    out = {}
    for line in text.splitlines():
        m = _KV.match(line)
        if m:
            out[m.group(1).lower()] = (m.group(2) or "").strip()
    return out


def _section(text: str, heading: str) -> str:
    """Lines under a `## heading` up to the next `## ` (or end of file)."""
    out, capture = [], False
    for line in text.splitlines():
        if re.match(rf"^##\s+{re.escape(heading)}\s*$", line, re.I):
            capture = True
            continue
        if capture and re.match(r"^##\s+", line):
            break
        if capture:
            out.append(line)
    return "\n".join(out)


def _bullets(text: str) -> list[str]:
    return [m.group(1).strip() for line in text.splitlines() if (m := _BULLET.match(line))]


def _after_title(text: str) -> str:
    """Everything below the first `# ` heading, stripped."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _H1.match(line):
            return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def _h1(text: str) -> str:
    for line in text.splitlines():
        m = _H1.match(line)
        if m:
            return m.group(1).strip()
    return ""


def _parse_module(line: str) -> Module:
    """`name: description (status) [path]` -> Module.

    `(status)` defaults to active; `[path]` is optional. Both are stripped from
    the right before the remainder is split on the first colon into name/desc.
    """
    path = ""
    m = _TRAILING_PATH.search(line)
    if m:
        path = m.group(1).strip()
        line = line[: m.start()].rstrip()
    status = "active"
    m = _TRAILING_STATUS.search(line)
    if m:
        status = m.group(1).strip() or "active"
        line = line[: m.start()].rstrip()
    name, _, desc = line.partition(":")
    return Module(name=name.strip(), description=desc.strip(), status=status, path=path)


# --- the compiler ----------------------------------------------------------

def compile_okf(adda_dir: Path) -> OKF:
    """Compile an /adda directory tree into a validated OKF object."""
    version_md = _read(adda_dir / "VERSION.md")
    vkv = _kv(version_md)

    arch_md = _read(adda_dir / "ARCHITECTURE.md")
    # overview = text between the H1 and the first `## ` section. Use a line-anchored
    # split so a `## ` heading at the very start of body (empty overview) is matched.
    body = _after_title(arch_md)
    overview = re.split(r"(?m)^##\s", body, maxsplit=1)[0].strip() if body else ""
    modules = [_parse_module(b) for b in _bullets(_section(arch_md, "Modules"))]
    constraints = _bullets(_section(arch_md, "Constraints"))

    architecture = Architecture(
        overview=overview,
        modules=modules,
        domain_model=_after_title(_read(adda_dir / "DOMAIN_MODEL.md")),
        api_contracts=_after_title(_read(adda_dir / "API_CONTRACTS.md")),
    )

    decisions = []
    decisions_dir = adda_dir / "DECISIONS"
    if decisions_dir.is_dir():
        for md in sorted(decisions_dir.glob("*.md")):
            text = _read(md)
            dkv = _kv(text)
            decisions.append(
                Decision(
                    id=dkv.get("id") or md.stem,
                    title=_h1(text),
                    status=dkv.get("status", "accepted"),
                )
            )

    skv = _kv(_read(adda_dir / "STATE" / "CURRENT.md"))
    state = State(updated=skv.get("updated", ""), summary=skv.get("summary", ""))

    return OKF(
        okf_version=OKF_VERSION,
        project=vkv.get("project", ""),
        version=vkv.get("version", ""),
        architecture=architecture,
        constraints=constraints,
        decisions=decisions,
        state=state,
    )
