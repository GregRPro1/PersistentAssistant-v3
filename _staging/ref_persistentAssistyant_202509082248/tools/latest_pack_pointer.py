import sys, pathlib, time
try:
    import pyperclip
except Exception:
    pyperclip = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
FB = ROOT / "tmp" / "feedback"
OUT = FB / "latest_pack.txt"

def main():
    if not FB.exists():
        print("[PACK] no feedback dir")
        return 1
    packs = sorted(FB.glob("pack_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not packs:
        print("[PACK] none found")
        return 2
    latest = packs[0].resolve()
    OUT.write_text(str(latest), encoding="utf-8")
    print(f"LATEST_PACK: {latest}")
    if pyperclip:
        try: pyperclip.copy(str(latest))
        except Exception: pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
