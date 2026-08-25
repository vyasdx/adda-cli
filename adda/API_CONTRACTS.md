<!-- Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com -->
<!-- Coded by - Claude Code -->

# API Contracts

The `adda` console script (Typer). Commands:

- `adda init [PATH] [--force]` — scaffold the /adda layout into a project.
- `adda export [PATH] [--okf] [--out F] [--compress]` — compile /adda/*.md → okf.json.
- `adda monitor (--tokens N | --file F) [--model M] [--limit L]` — Context Sentinel: % + OK/CHECKPOINT/ALERT/FORCE.
- `adda rehydrate [PATH] [--out F] [--compress]` — emit the minimal OKF (stdout by default).
- `adda checkpoint [PATH] [-m MSG]` — snapshot STATE/CURRENT.md to a timestamped entry.
- `adda sync [REPO] [--out F]` — derive an ARCHITECTURE skeleton (modules + deps) from the code.
- `adda diff [PATH]` — detect drift (documented modules vs repo); exit 1 on drift.
- `adda eval [PATH] [--json]` — rehydration fidelity (overall + load-bearing %).
- `adda version` — print the package version.
