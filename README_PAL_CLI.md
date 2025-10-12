
# PAL Python-first CLI Migration

This pack introduces `palctl` — a single Python CLI that replaces nearly all .ps1 logic.

## Install deps
```
pip install -r requirements.txt
```

## CLI usage
```
# show status
python -m pal.cli status

# start watchdog loop (replaces watchdog.ps1)
python -m pal.cli watchdog -c pal/config/pal.yaml

# create quick tunnel (replaces run_quick_tunnel.ps1)
python -m pal.cli tunnel-quick --port 8787 --install-if-missing

# force-write ops snapshot
python -m pal.cli ops-snapshot -c pal/config/pal.yaml

# tracker controls
python -m pal.cli tracker-ensure
python -m pal.cli tracker-restart

# smoke test
python -m pal.cli smoke-tunnel
```

## Windows convenience
Use `tools\cmd\palctl.cmd`:
```
tools\cmd\palctl.cmd watchdog -c pal/config/pal.yaml
```

## Tests
```
pytest -q
```
