
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

from pal.core.logging_config import setup_logging
from pal.core.ops import write_ops_snapshot, read_ops
from pal.core.tunnel import (
    quick_tunnel, find_cloudflared, diagnose_tunnel_path,
    verify_tunnel_url, is_port_listening
)
from pal.core.watchdog_py import WatchdogLoop
from pal.core.tracker import restart_tracker, start_tracker_if_needed

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()

DEFAULT_CFG = Path("pal/config/pal.yaml")

@app.command()
def watchdog(config: Path = typer.Option(DEFAULT_CFG, "--config", "-c"),
             interval: float = typer.Option(5.0, help="Seconds between snapshots"),
             start_tracker: bool = typer.Option(True, help="Ensure tracker running"),
             start_web: bool = typer.Option(True, help="(Reserved) Ensure web running")):
    """BLOCKING: plain watchdog loop (no UI). Ctrl+C to stop. Child processes keep running."""
    setup_logging()
    console.print("[bold yellow]BLOCKING:[/bold yellow] Watchdog loop running. Ctrl+C to exit; child processes (web/tracker) are not killed.")
    loop = WatchdogLoop(config_path=config, interval=interval,
                        ensure_tracker=start_tracker, ensure_web=start_web)
    loop.run_forever()

@app.command("watchdog-ui")
def watchdog_ui(config: Path = typer.Option(DEFAULT_CFG, "--config", "-c"),
                interval: float = typer.Option(2.0, help="Seconds between updates"),
                auto_tracker: bool = typer.Option(True),
                auto_web: bool = typer.Option(True)):
    """BLOCKING: live dashboard for web/tunnel/phone/tracker. Ctrl+C to exit."""
    setup_logging()
    loop = WatchdogLoop(config_path=config, interval=interval,
                        ensure_tracker=auto_tracker, ensure_web=auto_web)

    console.print("[bold yellow]BLOCKING:[/bold yellow] Watchdog UI running. Ctrl+C to exit. Child processes keep running.")

    def render():
        ops = read_ops() or {}
        t = Table(title="PAL Supervisor", expand=True)
        t.add_column("Component"); t.add_column("State"); t.add_column("Detail")
        web = ops.get("web", {})
        tunnel = ops.get("tunnel", {})
        phone = ops.get("phone", {})
        watcher = ops.get("watcher", {})

        def light(ok): return "[green]●[/green]" if ok else "[red]●[/red]"

        t.add_row("Web Port", light(bool(web.get("port_ok"))), f"{web.get('host')}:{web.get('port')}")
        t.add_row("Web Health", light(bool(web.get("health_ok"))), f"{web.get('health_url')}")
        t.add_row("Tunnel", light(bool(tunnel.get("ok"))), f"{tunnel.get('url') or ''}")
        t.add_row("Phone URL", light(bool(phone.get("url"))), f"{phone.get('url') or ''}")
        t.add_row("Watcher", light(bool(watcher.get("on"))), "heartbeat < 20s")
        return t

    with Live(render(), refresh_per_second=max(1, int(1/interval))) as live:
        while True:
            try:
                loop.iterate_once()
                live.update(render())
                time.sleep(interval)
            except KeyboardInterrupt:
                break

@app.command("tunnel-quick")
def tunnel_quick_cmd(port: int = typer.Option(8787, help="Local web port"),
                 install_if_missing: bool = typer.Option(False, help="Attempt winget/choco install (may be interactive)"),
                 stdout_timeout: float = typer.Option(45.0, help="Secs to wait for URL"),
                 verbose: bool = typer.Option(True, help="Echo cloudflared stdout while waiting")):
    """RETURNS: start a Cloudflare quick tunnel and capture the URL."""
    setup_logging()
    exe = find_cloudflared(install_if_missing=install_if_missing)
    if not is_port_listening("127.0.0.1", port):
        console.print(Panel.fit(f"[yellow]Warning[/yellow]: 127.0.0.1:{port} not listening; start your web app first."))
    url, steps = quick_tunnel(exe_path=exe, port=port, wait_seconds=stdout_timeout, verbose=verbose)
    diag = {"ok": bool(url), "url": url or "", "steps": steps}
    Path("reports/smoke").mkdir(parents=True, exist_ok=True)
    (Path("reports/smoke")/"PAL-TUNNEL-RUN.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    if url:
        console.print(f"[bold green]Tunnel URL:[/bold green] {url}")
        raise typer.Exit(0)
    else:
        console.print(Panel.fit("[red]No tunnel URL captured[/red]. See tmp/logs/cloudflared.*.log and reports/smoke/PAL-TUNNEL-RUN.json"))
        raise typer.Exit(2)

@app.command("tunnel-diagnose")
def tunnel_diagnose(port: int = typer.Option(8787), health: str = typer.Option("http://127.0.0.1:8787/healthz"),
                    install_if_missing: bool = typer.Option(False, help="Try winget/choco if cloudflared missing"),
                    timeout: float = typer.Option(45.0), verbose: bool = typer.Option(True)):
    """RETURNS: end-to-end diagnosis (origin, discovery, quick tunnel, remote /healthz)."""
    setup_logging()
    report = diagnose_tunnel_path(port=port, health_url=health, install_if_missing=install_if_missing,
                                  timeout=timeout, verbose=verbose)
    Path("reports/smoke").mkdir(parents=True, exist_ok=True)
    out = Path("reports/smoke")/"PAL-TUNNEL-DIAG.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ok = report.get("ok", False)
    console.print_json(data=report)
    raise typer.Exit(0 if ok else 3)

@app.command("tunnel-verify")
def tunnel_verify():
    """RETURNS: verify /healthz through the current tunnel URL."""
    setup_logging()
    ok, info = verify_tunnel_url()
    console.print_json(data={"ok": ok, **info})
    raise typer.Exit(0 if ok else 4)

@app.command("ops-snapshot")
def ops_snapshot(config: Path = typer.Option(DEFAULT_CFG, "--config", "-c")):
    """RETURNS: force-write ops_status.json (phone/web/tunnel)."""
    setup_logging()
    st = write_ops_snapshot(config_path=config)
    console.print_json(data=st)

@app.command("tracker-restart")
def tracker_restart_cmd():
    """RETURNS: restart the PAL tracker window (if running)."""
    setup_logging()
    ok = restart_tracker()
    console.print("[green]Tracker restart requested[/green]" if ok else "[yellow]No tracker to restart[/yellow]")

@app.command("tracker-ensure")
def tracker_ensure():
    """RETURNS: ensure tracker is running (start if needed)."""
    setup_logging()
    start_tracker_if_needed()
    console.print("[green]Tracker ensured[/green]")

@app.command("status")
def status():
    """RETURNS: pretty-print current ops status."""
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
