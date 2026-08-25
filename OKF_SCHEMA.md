<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# OKF — Open Knowledge Format (v0.2)

OKF is a small, **provider-agnostic** JSON format that carries a software project's
architecture memory — version, constraints, modules, decisions, and state — in a
shape any LLM can consume. It is the centerpiece of ADDA: think "schema.org for
software-architecture context." ADDA (`src/adda/okf.py`) is its reference
implementation; this document is the locked spec for format version **0.2**.

`okf_version` is `"0.2"`. v0.2 adds `Module.path` (additive, optional) over v0.1.

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `okf_version` | string | OKF format version. `"0.2"`. |
| `project` | string | Project name. |
| `version` | string | Project version (the project's own, not OKF's). |
| `architecture` | object | See **Architecture** below. |
| `constraints` | string[] | Hard rules the LLM must never violate. |
| `decisions` | Decision[] | Architecture Decision Records (ADRs). |
| `state` | object | See **State** below. |

### Architecture (object)

| Field | Type | Meaning |
|---|---|---|
| `overview` | string | One-paragraph prose overview (free text). |
| `modules` | Module[] | The system's components. |
| `domain_model` | string | Free-text domain entities/relationships. |
| `api_contracts` | string | Free-text public interfaces/routes/schemas. |

### Module (object)

| Field | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | — | Module identifier. |
| `description` | string | `""` | One-line description. |
| `status` | string | `"active"` | `active` \| `planned` \| `deprecated`. |
| `path` | string | `""` | Repo path this module maps to. Populated by `adda sync`; checked by `adda diff`. |

### Decision (object)

| Field | Type | Default | Meaning |
|---|---|---|---|
| `id` | string | — | ADR id (e.g. `ADR-0001`). |
| `title` | string | `""` | Decision title. |
| `status` | string | `"accepted"` | `accepted` \| `proposed` \| `superseded` \| `rejected`. |

### State (object)

| Field | Type | Meaning |
|---|---|---|
| `updated` | string | Last-updated marker (date or checkpoint id). |
| `summary` | string | One-line current-state summary. |

## Active-item semantics (what `rehydrate` keeps)

The **minimal OKF** emitted by `adda rehydrate` (spec §13) keeps only:
`okf_version`, `project`, `version`, `constraints`, **active modules**
(`status == "active"`), and **active decisions** (`status` in `{accepted, active}`).
Everything else — `architecture.overview`, `domain_model`, `api_contracts`,
`state`, and any non-active items — is dropped to minimize the payload.

## Where each field comes from (`/adda` → OKF)

| `/adda` file | OKF target |
|---|---|
| `VERSION.md` (`project:` / `version:` lines) | `project`, `version` |
| `ARCHITECTURE.md` overview paragraph | `architecture.overview` |
| `ARCHITECTURE.md` `## Constraints` bullets | `constraints` |
| `ARCHITECTURE.md` `## Modules` bullets | `architecture.modules` |
| `DOMAIN_MODEL.md` body | `architecture.domain_model` |
| `API_CONTRACTS.md` body | `architecture.api_contracts` |
| `DECISIONS/*.md` (`id:` / `status:` / H1) | `decisions` |
| `STATE/CURRENT.md` (`updated:` / `summary:`) | `state` |

**Module line syntax:** `- name: description (status) [path]` — `(status)` and
`[path]` are optional and stripped from the right; the remainder splits on the
first `:` into name/description.

## Example

```json
{
  "okf_version": "0.2",
  "project": "My Project",
  "version": "0.1.0",
  "architecture": {
    "overview": "",
    "modules": [
      { "name": "core", "description": "Core domain logic.", "status": "active", "path": "src/core" }
    ],
    "domain_model": "",
    "api_contracts": ""
  },
  "constraints": ["Keep architecture docs in /adda up to date before changing code."],
  "decisions": [
    { "id": "ADR-0001", "title": "Keep decisions in /adda", "status": "accepted" }
  ],
  "state": { "updated": "2026-06-25", "summary": "Scaffolded." }
}
```

## Canonical JSON Schema

Generated from the pydantic models in `src/adda/okf.py` via
`OKF.model_json_schema()` — this file stays the documentation; the code stays the
source of truth.

```json
{
  "$defs": {
    "Architecture": {
      "properties": {
        "overview": { "default": "", "title": "Overview", "type": "string" },
        "modules": { "items": { "$ref": "#/$defs/Module" }, "title": "Modules", "type": "array" },
        "domain_model": { "default": "", "title": "Domain Model", "type": "string" },
        "api_contracts": { "default": "", "title": "Api Contracts", "type": "string" }
      },
      "title": "Architecture",
      "type": "object"
    },
    "Decision": {
      "properties": {
        "id": { "title": "Id", "type": "string" },
        "title": { "default": "", "title": "Title", "type": "string" },
        "status": { "default": "accepted", "title": "Status", "type": "string" }
      },
      "required": ["id"],
      "title": "Decision",
      "type": "object"
    },
    "Module": {
      "properties": {
        "name": { "title": "Name", "type": "string" },
        "description": { "default": "", "title": "Description", "type": "string" },
        "status": { "default": "active", "title": "Status", "type": "string" },
        "path": { "default": "", "title": "Path", "type": "string" }
      },
      "required": ["name"],
      "title": "Module",
      "type": "object"
    },
    "State": {
      "properties": {
        "updated": { "default": "", "title": "Updated", "type": "string" },
        "summary": { "default": "", "title": "Summary", "type": "string" }
      },
      "title": "State",
      "type": "object"
    }
  },
  "properties": {
    "okf_version": { "default": "0.2", "title": "Okf Version", "type": "string" },
    "project": { "default": "", "title": "Project", "type": "string" },
    "version": { "default": "", "title": "Version", "type": "string" },
    "architecture": { "$ref": "#/$defs/Architecture" },
    "constraints": { "items": { "type": "string" }, "title": "Constraints", "type": "array" },
    "decisions": { "items": { "$ref": "#/$defs/Decision" }, "title": "Decisions", "type": "array" },
    "state": { "$ref": "#/$defs/State" }
  },
  "title": "OKF",
  "type": "object"
}
```
