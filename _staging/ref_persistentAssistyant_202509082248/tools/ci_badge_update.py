import re, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

def get_origin():
    try:
        url = subprocess.check_output(["git","remote","get-url","origin"], text=True).strip()
        return url
    except Exception:
        return ""

def parse_owner_repo(url: str):
    if "github.com" not in url:
        return None
    # https://github.com/owner/repo.git  OR git@github.com:owner/repo.git
    m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", url)
    if not m: 
        return None
    return m.group("owner"), m.group("repo")

def ensure_badge(owner, repo):
    badge = f"[![CI](https://github.com/{owner}/{repo}/actions/workflows/windows_ci.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/windows_ci.yml)"
    if not README.exists():
        README.write_text(f"# {repo}\n\n{badge}\n", encoding="utf-8")
        print("[CI BADGE] README created with badge.")
        return
    text = README.read_text(encoding="utf-8")
    if "actions/workflows/windows_ci.yml/badge.svg" in text:
        # replace existing CI line
        text = re.sub(r"\[!\[CI\]\(.+?badge\.svg\)\]\(.+?\)", badge, text, flags=re.IGNORECASE)
        README.write_text(text, encoding="utf-8")
        print("[CI BADGE] updated.")
    else:
        README.write_text(badge + "\n\n" + text, encoding="utf-8")
        print("[CI BADGE] inserted at top.")

def main():
    url = get_origin()
    parsed = parse_owner_repo(url)
    if not parsed:
        print("[CI BADGE] Could not parse origin for owner/repo. Skipping.")
        return 0
    owner, repo = parsed
    ensure_badge(owner, repo)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
