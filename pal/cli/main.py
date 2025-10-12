from __future__ import annotations
import json, os, sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pal.core.logging_config import setup_logging
from pal.core.ops import write_ops_snapshot, read_ops
from pal.core.tunnel import (quick_tunnel, find_cloudflared, diagnose_tunnel_path, verify_tunnel_url, is_port_listening)
from pal.core.watchdog_py import WatchdogLoop
from pal.core.tracker import restart_tracker, start_tracker_if_needed
app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()
DEFAULT_CFG = Path('pal/config/pal.yaml')

@app.command()
def watchdog(config: Path = typer.Option(DEFAULT_CFG, '--config', '-c'), interval: float = typer.Option(5.0), start_tracker: bool = typer.Option(True), start_web: bool = typer.Option(True)):
    setup_logging()
    loop = WatchdogLoop(config_path=config, interval=interval, ensure_tracker=start_tracker, ensure_web=start_web)
    loop.run_forever()

@app.command('tunnel-quick')
def tunnel_quick_cmd(port: int = typer.Option(8787), install_if_missing: bool = typer.Option(False), stdout_timeout: float = typer.Option(45.0), verbose: bool = typer.Option(False)):
    setup_logging()
    exe = find_cloudflared(install_if_missing=install_if_missing)
    if not is_port_listening('127.0.0.1', port):
        console.print(Panel.fit(f'[yellow]Warning[/yellow]: 127.0.0.1:{port} not listening; start your web app.'))
    url, steps = quick_tunnel(exe_path=exe, port=port, wait_seconds=stdout_timeout, verbose=verbose)
    diag = {'ok': bool(url), 'url': url or '', 'steps': steps}
    Path('reports/smoke').mkdir(parents=True, exist_ok=True)
    (Path('reports/smoke')/'PAL-TUNNEL-RUN.json').write_text(json.dumps(diag, indent=2), encoding='utf-8')
    if url:
        console.print(f'[bold green]Tunnel URL:[/bold green] {url}')
        raise typer.Exit(0)
    else:
        console.print(Panel.fit('[red]No tunnel URL captured[/red]. See tmp/logs/cloudflared.*.log and reports/smoke/PAL-TUNNEL-RUN.json'))
        raise typer.Exit(2)

@app.command('tunnel-diagnose')
def tunnel_diagnose(port: int = typer.Option(8787), health: str = typer.Option('http://127.0.0.1:8787/healthz'), install_if_missing: bool = typer.Option(False), timeout: float = typer.Option(45.0), verbose: bool = typer.Option(False)):
    setup_logging()
    report = diagnose_tunnel_path(port=port, health_url=health, install_if_missing=install_if_missing, timeout=timeout, verbose=verbose)
    Path('reports/smoke').mkdir(parents=True, exist_ok=True)
    out = Path('reports/smoke')/'PAL-TUNNEL-DIAG.json'
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    ok = report.get('ok', False)
    console.print_json(data=report)
    raise typer.Exit(0 if ok else 3)

@app.command('tunnel-verify')
def tunnel_verify():
    setup_logging()
    ok, info = verify_tunnel_url()
    console.print_json(data={'ok': ok, **info})
    raise typer.Exit(0 if ok else 4)

@app.command('ops-snapshot')
def ops_snapshot(config: Path = typer.Option(DEFAULT_CFG, '--config', '-c')):
    setup_logging()
    st = write_ops_snapshot(config_path=config)
    console.print_json(data=st)

@app.command('tracker-restart')
def tracker_restart_cmd():
    setup_logging()
    ok = restart_tracker()
    console.print('[green]Tracker restart requested[/green]' if ok else '[yellow]No tracker to restart[/yellow]')

@app.command('tracker-ensure')
def tracker_ensure():
    setup_logging()
    start_tracker_if_needed()
    console.print('[green]Tracker ensured[/green]')

@app.command('status')
def status():
    ops = read_ops()
    if not ops:
        console.print('[red]No ops status yet.[/red]  Run: palctl ops-snapshot or start watchdog.')
        raise typer.Exit(1)
    table = Table(title='PAL Ops Status')
    table.add_column('Section'); table.add_column('Key'); table.add_column('Value')
    for sec in ('web','tunnel','phone','watcher'):
        data = ops.get(sec) or {}
        for k,v in data.items():
            table.add_row(sec, k, str(v))
    console.print(table)

if __name__ == '__main__':
    app()