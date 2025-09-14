import os, re, sys, hashlib

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def find_settings_js() -> str:
    # Prefer CWD/web/pwa/settings_ext.js
    cwd = os.getcwd()
    cand1 = os.path.join(cwd, "web", "pwa", "settings_ext.js")
    if os.path.isfile(cand1): return cand1
    # Try 3-up from this script (tools/py/patches -> repo root)
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    cand2 = os.path.join(root, "web", "pwa", "settings_ext.js")
    if os.path.isfile(cand2): return cand2
    # Last resort: search for the file name near cwd
    for base in [cwd, root]:
        for dirpath, _, files in os.walk(base):
            if "settings_ext.js" in files and dirpath.replace("\\","/").endswith("web/pwa"):
                return os.path.join(dirpath, "settings_ext.js")
    raise FileNotFoundError("settings_ext.js not found. Searched:\n  "+cand1+"\n  "+cand2+"\n  + walked CWD and repo root")

APPLY_FUNC = ("""
async function applyStep() {
  if (!selectedStep) { out.textContent = 'Pick a suggestion to apply.'; return; }
  out.textContent = 'Running apply…';
  const r = await fetchJson('/agent/apply', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step: selectedStep, tests: 'tests', pytest_flags: ['-q'], retries: 0 })
  });
  const __body = r.json ? JSON.stringify(r.json, null, 2) : r.text;
  const __summary = (typeof extractPytestSummary === 'function') ? extractPytestSummary(r.json) : null;
  out.textContent = `POST /agent/apply -> ${r.status}\n` + __body + (__summary ? (`\\n\\nSummary: ${__summary}`) : '');
  if (__summary) {
    const isFail = /failed|error/i.test(__summary);
    try { out.style.borderLeft = isFail ? '4px solid #b00020' : '4px solid #0a7d2a'; } catch (_) {}
  }
}
""").strip() + "\n"

def remove_func_block(txt: str, func_name: str) -> str:
    key = f"function {func_name}("
    i = txt.find(key)
    if i < 0: return txt
    j = txt.find("{", i)
    if j < 0: return txt
    depth = 0; k = j
    while k < len(txt):
        c = txt[k]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return txt[:i] + txt[k+1:]
        k += 1
    return txt

def remove_lines_containing(txt: str, needle: str) -> str:
    return "".join(L for L in txt.splitlines(True) if needle not in L)

def ensure_apply_listener_once(txt: str) -> str:
    # Drop all existing applyStep listeners
    txt = re.sub(r"^\s*btnApply\.addEventListener\(\s*['\"]click['\"]\s*,\s*applyStep\s*,?\s*\{[^}]*\}\s*\)\s*;\s*$", "", txt, flags=re.M)
    txt = re.sub(r"^\s*btnApply\.addEventListener\(\s*['\"]click['\"]\s*,\s*applyStep\s*\)\s*;\s*$", "", txt, flags=re.M)
    # Insert canonical after const btnApply = ...
    m = re.search(r"(const\s+btnApply\s*=\s*el\([^)]*\)\s*;\s*)", txt)
    listener = "btnApply.addEventListener('click', applyStep, { passive: true });\n"
    if m:
        pos = m.end()
        return txt[:pos] + listener + txt[pos:]
    # fallback near controls.append(...)
    m2 = re.search(r"(controls\.append\([^)]*\);\s*)", txt)
    if m2:
        pos = m2.end()
        return txt[:pos] + "\n" + listener + txt[pos:]
    return txt + "\n" + listener

def ensure_apply_function(txt: str) -> str:
    key = "async function applyStep("
    i = txt.find(key)
    if i >= 0:
        j = txt.find("{", i)
        if j >= 0:
            depth = 0; k = j
            while k < len(txt):
                c = txt[k]
                if c == "{": depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return txt[:i] + APPLY_FUNC + txt[k+1:]
                k += 1
    # inject after accept() if present, else before approve(), else before IIFE end
    m = re.search(r"\n\s*async\s+function\s+accept\s*\(", txt)
    if m:
        return txt[:m.end()] + "\n\n" + APPLY_FUNC + txt[m.end():]
    m2 = re.search(r"\n\s*async\s+function\s+approve\s*\(", txt)
    if m2:
        return txt[:m2.start()] + "\n" + APPLY_FUNC + txt[m2.start():]
    end_iife = txt.rfind("})(document, window);")
    if end_iife != -1:
        return txt[:end_iife] + "\n" + APPLY_FUNC + txt[end_iife:]
    return txt + "\n" + APPLY_FUNC

if __name__ == "__main__":
    path = find_settings_js()
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()
    before = sha256(original)

    modified = original
    # 1) remove legacy function and calls
    modified = remove_func_block(modified, "wireApplyButton")
    modified = remove_lines_containing(modified, "wireApplyButton(")
    # 2) ensure canonical applyStep and single listener
    modified = ensure_apply_function(modified)
    modified = ensure_apply_listener_once(modified)

    after = sha256(modified)
    if before != after:
        backup = path + ".bak_finalize_v2"
        if not os.path.exists(backup):
            with open(backup, "w", encoding="utf-8") as bf: bf.write(original)
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print("status: UPDATED")
        print("path:", path)
        print("backup:", os.path.basename(backup))
        print("sha256_before:", before)
        print("sha256_after :", after)
    else:
        print("status: NOOP")
        print("path:", path)
        print("sha256:", before)
