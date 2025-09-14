import re, sys, hashlib, datetime, os

PATH = r"web/pwa/settings_ext.js"

def sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def backup(path, text):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = f"{path}.bak_{ts}"
    write(bpath, text)
    return bpath

def find_matching_brace(s, start_idx):
    """Given s and index of first char *after* '{', return index of matching '}'."""
    depth = 1
    i = start_idx
    in_str = None
    esc = False
    while i < len(s):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"', "`"):
                in_str = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1

def replace_wire_apply_body(text):
    pat = re.compile(r"(function\s+wireApplyButton\s*\(\s*btnApply\s*,\s*out\s*,\s*getSelectedStep\s*\)\s*\{)", re.S)
    m = pat.search(text)
    if not m:
        return text, False, "wireApplyButton() not found"

    header_start = m.start(1)
    body_start_open = m.end(1)         # position right after '{'
    body_start = body_start_open        # first char after '{'

    body_end = find_matching_brace(text, body_start)
    if body_end < 0:
        return text, False, "wireApplyButton() brace matching failed"

    new_body = """
    btnApply.addEventListener('click', async () => {
      const step = (getSelectedStep && getSelectedStep()) || null;
      if (!step) { out.textContent = 'Pick a suggestion first.'; return; }
      out.textContent = 'Applying…';
      const payload = { step, tests: 'tests', pytest_flags: ['-q'], retries: 0 };
      const r = await fetchJson('/agent/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const __body = r.json ? JSON.stringify(r.json, null, 2) : r.text;
      const __summary = (typeof extractPytestSummary === 'function') ? extractPytestSummary(r.json) : null;
      out.textContent = `POST /agent/apply -> ${r.status}\n` + __body + (__summary ? (`\\n\\nSummary: ${__summary}`) : '');
      if (__summary) {
        const isFail = /failed|error/i.test(__summary);
        try { out.style.borderLeft = isFail ? '4px solid #b00020' : '4px solid #0a7d2a'; } catch(_) {}
      }
    }, { passive: true });
""".lstrip("\n")

    new_text = text[:body_start] + "\n" + new_body + text[body_end:]
    return new_text, True, "wireApplyButton() body replaced"

def ensure_wire_call(text):
    # After the line that appends the controls (contains btnApply), ensure we call the helper exactly once
    m = re.search(r"controls\.append\([^\)]*btnApply[^\)]*\);\s*", text)
    if not m:
        return text, False, "controls.append(...btnApply...) not found"
    insertion_point = m.end()
    already = re.search(r"wireApplyButton\s*\(\s*btnApply\s*,\s*out\s*,\s*\(\)\s*=>\s*selectedStep\s*\)", text)
    if already:
        return text, False, "wireApplyButton call already present"
    injection = "    // unified apply wiring\n    wireApplyButton(btnApply, out, () => selectedStep);\n"
    return text[:insertion_point] + injection + text[insertion_point:], True, "wireApplyButton call inserted"

def remove_applyStep_and_listener(text):
    changed = False
    # Remove listener
    new_text = re.sub(r"btnApply\.addEventListener\(\s*'click'\s*,\s*applyStep\s*,\s*\{\s*passive\s*:\s*true\s*\}\s*\);\s*", "", text)
    if new_text != text:
        text = new_text
        changed = True

    # Remove function applyStep() with brace matching
    m = re.search(r"(async\s+function\s+applyStep\s*\()", text)
    if m:
        # find start of function block "{"
        open_brace = text.find("{", m.end())
        if open_brace != -1:
            close_brace = find_matching_brace(text, open_brace + 1)
            if close_brace != -1:
                # Remove entire function definition (up to and including close brace)
                text = text[:m.start()] + text[close_brace + 1:]
                changed = True
    return text, changed, "applyStep() removed" if changed else "applyStep() not present"

def ensure_extractor(text):
    if re.search(r"function\s+extractPytestSummary\s*\(", text):
        return text, False, "extractPytestSummary already present"
    # Insert before final '})(document, window);'
    tail_pat = re.compile(r"\}\)\(document,\s*window\);\s*$")
    m = tail_pat.search(text)
    if not m:
        return text, False, "IIFE tail not found"
    func = r"""
function extractPytestSummary(resp) {
  try {
    const s = (resp && resp.run && resp.run.stdout) || '';
    const lines = String(s).trim().split(/\r?\n/);
    for (let i = lines.length - 1; i >= 0; i--) {
      const L = lines[i];
      if (/\bpassed\b|\bfailed\b|\bskipped\b|\berrors?\b/i.test(L) &&
          /(\d+\s+passed|\d+\s+failed|\d+\s+errors?|\d+\s+skipped)/i.test(L)) {
        return L.trim();
      }
    }
  } catch (_) {}
  return null;
}
""".lstrip("\n")
    insert_at = m.start()
    new_text = text[:insert_at] + func + text[insert_at:]
    return new_text, True, "extractPytestSummary injected"

def main():
    text = read(PATH)
    orig_hash = sha256(text)
    bak = backup(PATH, text)

    changes = []

    text, ok1, msg1 = replace_wire_apply_body(text);      changes.append((ok1, msg1))
    text, ok2, msg2 = ensure_wire_call(text);             changes.append((ok2, msg2))
    text, ok3, msg3 = remove_applyStep_and_listener(text);changes.append((ok3, msg3))
    text, ok4, msg4 = ensure_extractor(text);             changes.append((ok4, msg4))

    new_hash = sha256(text)
    if new_hash != orig_hash:
        write(PATH, text)
        status = "UPDATED"
    else:
        status = "NO-OP"

    print("status:", status)
    print("backup:", bak)
    print("sha256_before:", orig_hash)
    print("sha256_after :", new_hash)
    for ok, msg in changes:
        print(f"- {'changed' if ok else 'kept   '}: {msg}")

if __name__ == "__main__":
    main()
