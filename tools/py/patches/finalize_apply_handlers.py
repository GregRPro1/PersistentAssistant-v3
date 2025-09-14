import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # tools/py -> repo root
PATH = os.path.join(ROOT, "web", "pwa", "settings_ext.js")
BACKUP = PATH + ".bak_final_apply"

APPLY_FUNC = r"""
async function applyStep() {
  if (!selectedStep) { out.textContent = 'Pick a suggestion to apply.'; return; }
  out.textContent = 'Running apply…';
  const r = await fetchJson('/agent/apply', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step: selectedStep, tests: 'tests', pytest_flags: ['-q'], retries: 0 })
  });
  const __body = r.json ? JSON.stringify(r.json, null, 2) : r.text;
  const __summary = (typeof extractPytestSummary === 'function') ? extractPytestSummary(r.json) : null;
  out.textContent = `POST /agent/apply -> ${r.status}\n` + __body + (__summary ? (`\n\nSummary: ${__summary}`) : '');
  if (__summary) {
    const isFail = /failed|error/i.test(__summary);
    try { out.style.borderLeft = isFail ? '4px solid #b00020' : '4px solid #0a7d2a'; } catch (_) {}
  }
}
""".strip() + "\n"

def load():
    with open(PATH, "r", encoding="utf-8") as f:
        return f.read()

def save(txt):
    if not os.path.exists(BACKUP):
        with open(BACKUP, "w", encoding="utf-8") as f:
            f.write(original)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(txt)

def remove_wire_apply_button_func(txt: str) -> str:
    key = "function wireApplyButton("
    i = txt.find(key)
    if i < 0:
        return txt
    # find first '{' after signature
    j = txt.find("{", i)
    if j < 0:
        return txt  # malformed; give up safely
    # brace-match to the end of function
    depth = 0
    k = j
    while k < len(txt):
        c = txt[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                # remove from i .. k (inclusive)
                return txt[:i] + txt[k+1:]
        k += 1
    return txt  # if unmatched braces, do nothing

def remove_wire_apply_button_calls(txt: str) -> str:
    # remove whole lines that call wireApplyButton(…)
    lines = txt.splitlines(True)
    out = []
    for L in lines:
        if "wireApplyButton(" in L:
            continue
        out.append(L)
    return "".join(out)

def ensure_apply_listener_once(txt: str) -> str:
    # Remove *all* existing btnApply listener lines for applyStep, then add one canonical line.
    lines = txt.splitlines(True)
    new_lines = []
    found_btn_def = False
    inserted_listener = False
    for L in lines:
        if re.search(r"btnApply\.addEventListener\(\s*['\"]click['\"]\s*,\s*applyStep\s*\)", L):
            # drop duplicates
            continue
        new_lines.append(L)
    txt2 = "".join(new_lines)

    # Insert the canonical listener right after the const btnApply declaration, if present
    m = re.search(r"(const\s+btnApply\s*=\s*el\([^)]*\)\s*;\s*)", txt2)
    if m:
        insert_at = m.end()
        listener = "btnApply.addEventListener('click', applyStep, { passive: true });\n"
        txt2 = txt2[:insert_at] + listener + txt2[insert_at:]
        inserted_listener = True
        return txt2

    # fallback: append near the controls.append(...) call
    m2 = re.search(r"(controls\.append\([^)]*\);\s*)", txt2)
    if m2:
        insert_at = m2.end()
        listener = "\nbtnApply.addEventListener('click', applyStep, { passive: true });\n"
        return txt2[:insert_at] + listener + txt2[insert_at:]

    # ultimate fallback: append at end (still valid)
    return txt2 + "\nbtnApply.addEventListener('click', applyStep, { passive: true });\n"

def ensure_apply_function(txt: str) -> str:
    if re.search(r"\basync\s+function\s+applyStep\s*\(", txt):
        # Replace existing body with canonical (simple approach: kill existing def block and insert fresh)
        # Remove the whole applyStep function via brace match (similar to wireApplyButton)
        key = "async function applyStep("
        i = txt.find(key)
        if i >= 0:
            j = txt.find("{", i)
            if j >= 0:
                depth = 0
                k = j
                while k < len(txt):
                    c = txt[k]
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            txt = txt[:i] + APPLY_FUNC + txt[k+1:]
                            return txt
                    k += 1
    # If not present, inject after accept() or before approve()
    anchor = re.search(r"\n\s*async\s+function\s+accept\s*\(", txt)
    if anchor:
        insert_at = anchor.end()
        return txt[:insert_at] + "\n\n" + APPLY_FUNC + txt[insert_at:]
    anchor2 = re.search(r"\n\s*async\s+function\s+approve\s*\(", txt)
    if anchor2:
        insert_at = anchor2.start()
        return txt[:insert_at] + "\n" + APPLY_FUNC + txt[insert_at:]
    # last resort: append near end but before the closing IIFE
    end_anchor = txt.rfind("})(document, window);")
    if end_anchor != -1:
        return txt[:end_anchor] + "\n" + APPLY_FUNC + txt[end_anchor:]
    return txt + "\n" + APPLY_FUNC

if __name__ == "__main__":
    original = load()
    modified = original

    # 1) remove legacy helper function + calls
    modified = remove_wire_apply_button_func(modified)
    modified = remove_wire_apply_button_calls(modified)

    # 2) ensure canonical applyStep() and single listener
    modified = ensure_apply_function(modified)
    modified = ensure_apply_listener_once(modified)

    if modified != original:
        save(modified)
        print("status: UPDATED")
        print(f"backup: {os.path.basename(BACKUP)}")
    else:
        print("status: NOOP")
