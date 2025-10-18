# Lesson: Guard against self-copy and syntax regressions
- Apply **in-place edits** only; never copy files from pack to identical paths.
- Validate with `python -m py_compile` before replacing target file; **abort on failure**.
- Append features (e.g., /context panel, startup URL print) **idempotently** and only when Flask `app = Flask(...)` exists.
- Preserve the existing UI — no wholesale overwrites.
Recorded: 2025-10-12 15:21:31
