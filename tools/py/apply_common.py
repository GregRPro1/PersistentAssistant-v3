from pathlib import Path
def have_git_repo(root: Path) -> bool:
    return (root / '.git').exists()
def find_repo_root(start: Path):
    p=start
    for _ in range(10):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p=p.parent
    return None
def resolve_repo_root(cli_root: str | None):
    if cli_root:
        p=Path(cli_root)
        if have_git_repo(p): return p
    cand=find_repo_root(Path(__file__).resolve())
    if cand: return cand
    hard=Path(r'C:\_Repos\PersistentAssistant')
    return hard if have_git_repo(hard) else None
