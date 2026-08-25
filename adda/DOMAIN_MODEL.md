<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# Domain Model

The OKF (Open Knowledge Format) is the provider-agnostic JSON ADDA compiles to and
rehydrates. Core entities (the locked v0.2 spec lives in `OKF_SCHEMA.md`):

- OKF — okf_version, project, version, architecture, constraints[], decisions[], state.
- Architecture — overview, modules[], domain_model, api_contracts.
- Module — name, description, status (active | planned | deprecated), path.
- Decision — id, title, status (accepted | proposed | superseded | rejected).
- State — updated, summary.

Active-item rule: `rehydrate` keeps constraints + active modules + active decisions
(status accepted/active) + project/version, and drops prose, state, and inactive items.
