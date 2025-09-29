import argparse, subprocess, sys, datetime, base64
from pathlib import Path

FILES = {
    'tools/ps1/run_pack_fetcher.ps1': b'cGFyYW0oW3N3aXRjaF0kT25jZSwgW2ludF0kSW50ZXJ2YWxTZWNvbmRzID0gNjAsIFtpbnRdJFRhaWwgPSA4MCkKJEVycm9yQWN0aW9uUHJlZmVyZW5jZT0nU3RvcCcKCmZ1bmN0aW9uIEZpbmQtUmVwb1Jvb3QoW3N0cmluZ10kc3RhcnQpIHsKICBpZiAoLW5vdCAkc3RhcnQpIHsgJHN0YXJ0ID0gJFBTU2NyaXB0Um9vdCB9CiAgJGN1ciA9IFJlc29sdmUtUGF0aCAtTGl0ZXJhbFBhdGggJHN0YXJ0CiAgZm9yICgkaT0wOyAkaSAtbHQgMTA7ICRpKyspIHsKICAgIGlmIChUZXN0LVBhdGggKEpvaW4tUGF0aCAkY3VyICcuZ2l0JykpIHsgcmV0dXJuICRjdXIgfQogICAgJHBhcmVudCA9IFNwbGl0LVBhdGggLVBhcmVudCAkY3VyCiAgICBpZiAoJHBhcmVudCAtZXEgJGN1cikgeyBicmVhayB9CiAgICAkY3VyID0gJHBhcmVudAogIH0KICByZXR1cm4gKEdldC1Mb2NhdGlvbikuUGF0aAp9Cgokcm9vdCA9IEZpbmQtUmVwb1Jvb3QgJG51bGwKJHB5ID0gSm9pbi1QYXRoICRyb290ICd0b29sc1xweVxwYWNrX2ZldGNoZXIucHknCmlmICgtbm90IChUZXN0LVBhdGggJHB5KSkgeyBXcml0ZS1FcnJvciAicGFja19mZXRjaGVyLnB5IG5vdCBmb3VuZCBhdCAkcHkiOyBleGl0IDIgfQoKV3JpdGUtSG9zdCAicnVuX3BhY2tfZmV0Y2hlcjogcm9vdD0kcm9vdCIKaWYgKCRPbmNlKSB7CiAgJiBweXRob24gJHB5IC0tb25jZQp9IGVsc2UgewogICYgcHl0aG9uICRweSAtLWludGVydmFsICRJbnRlcnZhbFNlY29uZHMKfQokY29kZSA9ICRMQVNURVhJVENPREUKV3JpdGUtSG9zdCAicnVuX3BhY2tfZmV0Y2hlcjogZXhpdCAkY29kZSIKCiRsb2cgPSBKb2luLVBhdGggJHJvb3QgJ3JlcG9ydHNcb3BzXHBhY2tfZmV0Y2hlci5sb2cnCmlmIChUZXN0LVBhdGggJGxvZykgewogIFdyaXRlLUhvc3QgIi0tLS0gdGFpbCBwYWNrX2ZldGNoZXIubG9nIChsYXN0ICRUYWlsIGxpbmVzKSAtLS0tIgogIEdldC1Db250ZW50ICRsb2cgLVRhaWwgJFRhaWwKfSBlbHNlIHsKICBXcml0ZS1Ib3N0ICJwYWNrX2ZldGNoZXIubG9nIG5vdCBmb3VuZCB5ZXQuIgp9CmV4aXQgJGNvZGU=',
}

def run(a, cwd=None, check=True): subprocess.run(a, cwd=cwd, check=check)

def find_root(seed: Path) -> Path:
    p = seed
    for _ in range(8):
        if (p/'.git').exists(): return p
        p = p.parent
    return seed

def main():
    here = Path(__file__).resolve()
    root = find_root(here)

    for rel, b64 in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(b64))

    step='PA-312'; branch=f'step/{step}-fix-runfetcher'
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    run(['git','checkout','-B',branch], root)
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: fix run_pack_fetcher.ps1 inline-if; add diagnostics'], root, check=False)
    run(['git','push','-u','origin',branch], root, check=False)
    print(f'{step} done.')

if __name__ == '__main__': sys.exit(main())