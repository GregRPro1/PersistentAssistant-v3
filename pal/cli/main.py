
from __future__ import annotations
import json
import os
import sys
import time
import subprocess
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from pal.core.logging_config import setup_logging
from pal.core.ops import write_ops_snapshot, read_ops, ensure_dirs
from pal.core.tunnel import quick_tunnel, find_cloudflared
from pal.core.watchdog_py import WatchdogLoop
from pal.core.tracker import restart_tracker, start_tracker_if_needed

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()

DEFAULT_CFG = Path("pal/config/pal.yaml")

@app.command()
def watchdog(config: Path = typer.Option(DEFAULT_CFG, "--config", "-c"),
             interval: float = typer.Option(5.0, help="Seconds between snapshots"),
             start_tracker: bool = typer.Option(True, help="Ensure tracker running"),
             start_web: bool = typer.Option(True, help="Ensure web placeholder running")):
    """Run the Python watchdog loop (replaces watchdog.ps1)."""
    setup_logging()
    loop = WatchdogLoop(config_path=config, interval=interval,
                        ensure_tracker=start_tracker, ensure_web=start_web)
    loop.run_forever()

@app.command()
def tunnel_quick(port: int = typer.Option(8787, help="Local web port"),
                 install_if_missing: bool = typer.Option(False, help="Attempt winget/choco install"),
                 stdout_timeout: float = typer.Option(45.0, help="Secs to wait for URL")):
    """Start a Cloudflare quick tunnel and capture the URL."""
    setup_logging()
    exe = find_cloudflared(install_if_missing=install_if_missing)
    url = quick_tunnel(exe_path=exe, port=port, wait_seconds=stdout_timeout)
    console.print(f"[bold green]Tunnel URL:[/bold green] {url}" if url else "[yellow]No tunnel URL captured.[/yellow]")
    raise typer.Exit(code=0 if url else 1)

@app.command()
def ops_snapshot(config: Path = typer.Option(DEFAULT_CFG, "--config", "-c")):
    """Force-write ops_status.json (phone/web/tunnel)."""
    setup_logging()
    st = write_ops_snapshot(config_path=config)
    console.print_json(data=st)

@app.command()
def tracker_restart():
    """Restart the PAL tracker window (if running)."""
    setup_logging()
    ok = restart_tracker()
    console.print("[green]Tracker restart requested[/green]" if ok else "[yellow]No tracker to restart[/yellow]")

@app.command()
def tracker_ensure():
    """Ensure tracker is running (start if needed)."""
    setup_logging()
    start_tracker_if_needed()
    console.print("[green]Tracker ensured[/green]")

@app.command()
def smoke_tunnel():
    """Smoke test: find cloudflared, start quick tunnel, validate URL, write reports/smoke JSON."""
    setup_logging()
    from pal.core.tunnel import smoke_tunnel
    ok, rec_path = smoke_tunnel()
    msg = "PASS" if ok else "FAIL"
    console.print(f"[bold]{msg}[/bold]  {rec_path}")

@app.command()
def status():
    """Pretty-print current ops status."""
    ops = read_ops()
    if not ops:
        console.print("[red]No ops status yet.[/red]  Run: palctl ops-snapshot or start watchdog.")
        raise typer.Exit(1)
    table = Table(title="PAL Ops Status")
    table.add_column("Section"); table.add_column("Key"); table.add_column("Value")
    for sec in ("web","tunnel","phone","watcher"):
        data = ops.get(sec) or {}
        for k,v in data.items():
            table.add_row(sec, k, str(v))
    console.print(table)

if __name__ == "__main__":
    app()
