# Developed by - Vedavyas Vayalpadu - vyas4c3@gmail.com
# Coded by - Claude Code
"""ADDA command-line entrypoint (Typer)."""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from adda import __version__
from adda.audit import audit_report
from adda.compress import compress_text
from adda.diff import diff_report
from adda.evaluate import evaluate
from adda.hook import check_staged, hook_body, staged_paths
from adda.okf import compile_okf
from adda.rehydrate import minimal_okf
from adda.sentinel import ContextSentinel, count_tokens, limit_for
from adda.sync import skeleton_markdown


def _force_utf8_output() -> None:
    """Emit UTF-8 on stdout/stderr regardless of the console codepage.

    BUG-ADDA-022. On Windows a REDIRECTED stdout gets the console codepage
    (cp1252), so the first non-ASCII byte raises UnicodeEncodeError. ADDA's own
    OKF carries `->` arrows, so `adda rehydrate . > out.json` crashed - and
    stdout is the documented default for `rehydrate`, the command the whole
    tool is built around. `--out` was unaffected because it writes explicit
    UTF-8, which is why this survived every local run.

    JSON is UTF-8 by specification, so forcing it is correct rather than merely
    convenient. Guarded because a captured or already-detached stream may not
    be reconfigurable.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):  # detached, or not a real text stream
            pass


_force_utf8_output()

app = typer.Typer(
    help="ADDA - anti-drift architecture memory + OKF + Context Sentinel.",
    no_args_is_help=True,
    add_completion=False,
)

# Seed scaffold shipped with the package (see src/adda/templates/adda/).
TEMPLATES = Path(__file__).parent / "templates" / "adda"


def _resolve_adda_dir(path: Path) -> Path:
    """Accept either a project root (containing adda/) or an adda/ dir itself."""
    if (path / "adda").is_dir():
        return path / "adda"
    if (path / "VERSION.md").is_file():
        return path
    raise typer.BadParameter(
        f"No adda/ directory found under {path}. Run `adda init` first."
    )


def _maybe_compress(text: str, compress: bool) -> str:
    """Apply opt-in headroom compression, reporting savings or why it was skipped."""
    if not compress:
        return text
    out, info = compress_text(text)
    if info.get("applied"):
        saved, ratio = info.get("tokens_saved"), info.get("compression_ratio")
        detail = f"{saved} tokens saved" if saved is not None else "applied"
        if ratio is not None:
            detail += f" ({ratio:.0%} smaller)"
        typer.secho(f"[compress] headroom: {detail}", fg=typer.colors.CYAN)
        return out
    typer.secho(
        f"[compress] skipped ({info.get('reason')}) - emitting uncompressed.",
        fg=typer.colors.YELLOW,
    )
    return text


@app.command()
def version() -> None:
    """Print the ADDA version."""
    typer.echo(__version__)


@app.command()
def init(
    path: Path = typer.Argument(
        Path("."), help="Target project directory (default: current directory)."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing adda/ directory."
    ),
) -> None:
    """Scaffold an /adda architecture-memory directory into a target project."""
    dest = path / "adda"
    if dest.exists():
        if not force:
            typer.secho(
                f"{dest} already exists. Use --force to overwrite.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
    if dest.exists():
        # NEVER rmtree. --force means "overwrite the scaffold", not "delete
        # everything accumulated here". It used to remove the whole directory,
        # taking MODULE_MAP.json and STATE/checkpoints with it - and with no
        # map the commit gate silently stops blocking anything, so a routine
        # re-scaffold disarmed enforcement with no signal at all.
        kept = [
            f for f in sorted(dest.rglob("*"))
            if f.is_file() and not (TEMPLATES / f.relative_to(dest)).exists()
        ]
        shutil.copytree(TEMPLATES, dest, dirs_exist_ok=True)
        if kept:
            typer.secho(
                f"Kept {len(kept)} file(s) that are not part of the scaffold:",
                fg=typer.colors.YELLOW,
            )
            for f in kept:
                typer.echo(f"  {f.relative_to(dest).as_posix()}")
    else:
        shutil.copytree(TEMPLATES, dest)
    typer.secho(f"Scaffolded ADDA memory at {dest}", fg=typer.colors.GREEN)


@app.command()
def export(
    path: Path = typer.Argument(
        Path("."), help="Project dir containing adda/ (default: current)."
    ),
    okf: bool = typer.Option(
        True, "--okf", help="Emit OKF JSON (default, and the only format today)."
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Output path (default: <project>/okf.json)."
    ),
    compress: bool = typer.Option(
        False, "--compress", help="Compress with headroom-ai if installed (lossy; opt-in)."
    ),
) -> None:
    """Compile the /adda markdown into validated OKF JSON."""
    adda_dir = _resolve_adda_dir(path)
    okf_obj = compile_okf(adda_dir)  # pydantic-validated by construction
    target = out or (adda_dir.parent / "okf.json")
    text = _maybe_compress(
        json.dumps(okf_obj.model_dump(), indent=2, ensure_ascii=False), compress
    )
    target.write_text(text + "\n", encoding="utf-8")
    typer.secho(
        f"Wrote OKF -> {target}  "
        f"({len(okf_obj.architecture.modules)} modules, "
        f"{len(okf_obj.decisions)} decisions, "
        f"{len(okf_obj.constraints)} constraints)",
        fg=typer.colors.GREEN,
    )


@app.command()
def monitor(
    tokens: Optional[int] = typer.Option(
        None, "--tokens", "-t", help="Current token count to gauge."
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Count tokens of this file instead of --tokens."
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model id (sets default limit and counting accuracy)."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Context window (default: model's window or 200000)."
    ),
) -> None:
    """Context Sentinel: print context usage % and OK/CHECKPOINT/ALERT/FORCE."""
    if (tokens is None) == (file is None):
        raise typer.BadParameter("Provide exactly one of --tokens or --file.")

    method = "given"
    if file is not None:
        tokens, method = count_tokens(file.read_text(encoding="utf-8"), model=model)

    eff_limit = limit or limit_for(model)
    sentinel = ContextSentinel(eff_limit)
    status = sentinel.check(tokens)
    color = {
        "OK": typer.colors.GREEN,
        "CHECKPOINT": typer.colors.YELLOW,
        "ALERT": typer.colors.RED,
        "FORCE": typer.colors.RED,
    }[status]
    typer.secho(
        f"{status}  {sentinel.percent(tokens):.1f}%  "
        f"({tokens}/{eff_limit} tokens via {method})",
        fg=color,
    )
    if status != "OK":
        typer.echo("-> Checkpoint now: run `adda checkpoint`, then `adda rehydrate` after a compaction.")


@app.command()
def rehydrate(
    path: Path = typer.Argument(
        Path("."), help="Project dir containing adda/ (default: current)."
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Write here (default: print to stdout for piping)."
    ),
    compress: bool = typer.Option(
        False, "--compress", help="Compress with headroom-ai if installed (lossy; opt-in)."
    ),
) -> None:
    """Emit the MINIMAL OKF to restore an LLM's architecture memory after a compaction."""
    adda_dir = _resolve_adda_dir(path)
    data = minimal_okf(compile_okf(adda_dir))
    text = _maybe_compress(json.dumps(data, indent=2, ensure_ascii=False), compress)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        typer.secho(f"Wrote minimal OKF -> {out}", fg=typer.colors.GREEN)
    else:
        typer.echo(text)


@app.command()
def checkpoint(
    path: Path = typer.Argument(
        Path("."), help="Project dir containing adda/ (default: current)."
    ),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Note to attach to the snapshot."
    ),
) -> None:
    """Snapshot the current STATE/ into a timestamped checkpoint entry."""
    adda_dir = _resolve_adda_dir(path)
    current = adda_dir / "STATE" / "CURRENT.md"
    if not current.is_file():
        raise typer.BadParameter(f"No STATE/CURRENT.md under {adda_dir}.")

    # UTC, colon-free, sortable -> safe as a Windows filename.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshots = adda_dir / "STATE" / "checkpoints"
    snapshots.mkdir(exist_ok=True)
    dest = snapshots / f"{stamp}.md"

    header = f"# Checkpoint {stamp}\n"
    if message:
        header += f"\nmessage: {message}\n"
    dest.write_text(header + "\n" + current.read_text(encoding="utf-8"), encoding="utf-8")
    typer.secho(f"Checkpoint saved -> {dest}", fg=typer.colors.GREEN)


@app.command()
def sync(
    repo: Path = typer.Argument(Path("."), help="Repo root to scan."),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Write the output here (default: stdout)."
    ),
    map_: bool = typer.Option(
        False, "--map", help="Emit MODULE_MAP.json (code->doc routing) instead of the skeleton."
    ),
) -> None:
    """Derive an ARCHITECTURE skeleton (or, with --map, the code->doc map)."""
    from adda.sync import module_map_json

    include = None
    if map_ and out is not None and out.is_file():
        # Regenerating must not silently re-drop roots the user opted back in.
        try:
            include = json.loads(out.read_text(encoding="utf-8")).get("include") or None
        except (OSError, ValueError):
            include = None  # unreadable or not a map: regenerate from scratch

    text = module_map_json(repo, include=include) if map_ else skeleton_markdown(repo)
    label = "MODULE_MAP" if map_ else "skeleton"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        typer.secho(f"Wrote {label} -> {out}", fg=typer.colors.GREEN)
    else:
        typer.echo(text)


@app.command()
def diff(
    path: Path = typer.Argument(
        Path("."), help="Project root (contains adda/ and the code)."
    ),
) -> None:
    """Detect drift between documented OKF modules and the actual repo."""
    adda_dir = _resolve_adda_dir(path)
    gaps = diff_report(adda_dir.parent, adda_dir)
    if not gaps:
        typer.secho("No drift: documented modules match the repo.", fg=typer.colors.GREEN)
        return
    typer.secho(f"Drift detected: {len(gaps)} gap(s)", fg=typer.colors.RED)
    for g in gaps:
        c = typer.colors.RED if g["severity"] == "high" else typer.colors.YELLOW
        typer.secho(
            f"  [{g['severity']:<6}] {g['module']}: "
            f"documented={g['documented']}  actual={g['actual']}",
            fg=c,
        )
    raise typer.Exit(1)


@app.command()
def audit(
    path: Path = typer.Argument(
        Path("."), help="Project root (contains adda/ and the code)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit the report as JSON."),
) -> None:
    """Detect doc-layer drift: missing, stale, unmapped or orphaned module docs."""
    adda_dir = _resolve_adda_dir(path)
    try:
        findings, skipped = audit_report(adda_dir.parent, adda_dir)
    except FileNotFoundError as exc:
        if json_out:
            typer.echo(json.dumps({"error": str(exc), "findings": [], "skipped": []}, indent=2))
        else:
            typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1)

    if json_out:
        typer.echo(json.dumps({"findings": findings, "skipped": skipped}, indent=2))
        raise typer.Exit(1 if findings else 0)

    for note in skipped:
        typer.secho(f"[skipped] {note}", fg=typer.colors.YELLOW)
    if not findings:
        typer.secho("No doc drift: every mapped code path has a current doc.", fg=typer.colors.GREEN)
        return
    typer.secho(f"Doc drift detected: {len(findings)} finding(s)", fg=typer.colors.RED)
    colors = {"high": typer.colors.RED, "medium": typer.colors.YELLOW, "low": typer.colors.CYAN}
    for f in findings:
        typer.secho(
            f"  [{f['severity']:<6}] {f['issue']:<14} {f['item']}",
            fg=colors.get(f["severity"], typer.colors.WHITE),
        )
    raise typer.Exit(1)


@app.command(name="eval")
def eval_cmd(
    path: Path = typer.Argument(
        Path("."), help="Project dir containing adda/ (default: current)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit the report as JSON."),
) -> None:
    """Score rehydration fidelity: how much architecture memory survives `rehydrate`."""
    adda_dir = _resolve_adda_dir(path)
    report = evaluate(compile_okf(adda_dir), adda_dir)
    if json_out:
        typer.echo(json.dumps(report, indent=2))
        return
    if report["overall_fidelity_pct"] is None:
        typer.secho(
            "Rehydration fidelity: n/a - every architecture file is still the "
            "scaffold `adda init` wrote. There is no authored memory to score.",
            fg=typer.colors.YELLOW,
        )
        typer.echo("  write your constraints, modules and decisions into adda/, then re-run.")
        return
    typer.secho(
        f"Rehydration fidelity: {report['overall_fidelity_pct']}% overall, "
        f"{report['load_bearing_fidelity_pct']}% load-bearing",
        fg=typer.colors.GREEN,
    )
    if report["unauthored_template_files"]:
        typer.secho(
            "  [partial] still unwritten scaffold: "
            + ", ".join(report["unauthored_template_files"])
            + " - the score counts placeholder text as memory.",
            fg=typer.colors.YELLOW,
        )
    typer.echo(
        f"  facts preserved: {report['facts_preserved']}/{report['facts_total']}  |  "
        f"payload {report['payload_reduction_pct']}% smaller "
        f"({report['minimal_chars']} vs {report['full_chars']} chars)"
    )
    if report["dropped"]:
        typer.echo("  dropped (non-load-bearing): " + ", ".join(report["dropped"]))


hook_app = typer.Typer(help="Pre-commit enforcement: code changes must carry their doc.")
app.add_typer(hook_app, name="hook")


@hook_app.command("run")
def hook_run(
    path: Path = typer.Argument(Path("."), help="Repo root (default: current)."),
) -> None:
    """Block the commit when staged code is missing its staged doc."""
    if os.environ.get("ADDA_SKIP"):
        typer.secho("[adda] ADDA_SKIP set - doc gate bypassed.", fg=typer.colors.YELLOW)
        return
    try:
        adda_dir = _resolve_adda_dir(path)
    except typer.BadParameter:
        return  # no /adda here - nothing to enforce
    gaps = check_staged(adda_dir.parent, adda_dir, staged_paths(adda_dir.parent))
    if not gaps:
        return
    typer.secho(f"Commit blocked: {len(gaps)} code change(s) without their doc.", fg=typer.colors.RED)
    for code, doc in gaps:
        typer.secho(f"  {code}  ->  update and stage {doc}", fg=typer.colors.RED)
    typer.echo("\nUpdate the doc (bump `Last verified`, append to its Change Log), then stage it.")
    typer.echo("To bypass deliberately: `git commit --no-verify`, or set ADDA_SKIP=1.")
    raise typer.Exit(1)


@hook_app.command("install")
def hook_install(
    path: Path = typer.Argument(Path("."), help="Repo root (default: current)."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing pre-commit hook."),
) -> None:
    """Install the pre-commit doc gate into .git/hooks/pre-commit."""
    hooks = path / ".git" / "hooks"
    if not hooks.is_dir():
        typer.secho(f"{path} is not a git repo (no .git/hooks).", fg=typer.colors.RED)
        raise typer.Exit(1)
    target = hooks / "pre-commit"
    if target.exists() and not force:
        typer.secho(f"{target} already exists. Re-run with --force, or add this line yourself:", fg=typer.colors.RED)
        typer.echo(f'  exec "{sys.executable}" -m adda.cli hook run')
        raise typer.Exit(1)
    body = hook_body(sys.executable)
    target.write_text(body, encoding="utf-8", newline="\n")
    # chmod is a no-op on Windows (git's bundled sh runs the hook via its
    # shebang, not the execute bit) but is required on POSIX.
    target.chmod(0o755)
    written = target.read_text(encoding="utf-8")
    if "hook run" not in written:
        typer.secho(f"Wrote {target} but the content looks wrong - install failed.", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(f"Installed doc gate -> {target}", fg=typer.colors.GREEN)
    typer.echo("Bypass when you must: `git commit --no-verify` or ADDA_SKIP=1.")


if __name__ == "__main__":  # `python -m adda.cli` - used by the installed git hook
    app()
