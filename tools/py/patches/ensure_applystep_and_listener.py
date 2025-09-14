import re, sys, os, datetime, hashlib

PATH = os.path.join("web", "pwa", "settings_ext.js")

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

src = open(PATH, "r", encoding="utf-8").read()
before = sha256(src)
changed = []

# --- A) Ensure async function applyStep() exists (DOM-based, no coupling) ---
if not re.search(r'async\s+function\s+applyStep\s*\(', src):
    apply_fn = r"""
// ---- Back-compat / fallback: named handler expected by some probes ----
async function applyStep(ev) {
  try {
    const pane = document.querySelector('section[data-pane="actions"]');
    const out  = pane ? pane.querySelector('pre.codebox') : null;
    if (!out) return;

    const sel = document.querySelector('.action-sugg li.selected');
    const stepText = sel ? (sel.textContent || '') : '';
    // strip leading badge number if present
    const step = stepText.replace(/^\s*\d+\s*/, '').trim() || null;

    if (!step) { out.textContent = 'Pick a suggestion to apply.'; return; }
    out.textContent = 'Running apply…';

    const r = await fetchJson('/agent/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step })
    });

    const __body = r.json ? JSON.stringify(r.json, null, 2) : r.text;
    const __summary = (typeof extractPytestSummary === 'function') ? extractPytestSummary(r.json) : null;
    out.textContent = `POST /agent/apply -> ${r.status}\n` + __body + (__summary ? (`\n\nSummary: ${__summary}`) : '');
    if (__summary) {
      try { out.style.borderLeft = /failed|error/i.test(__summary) ? '4px solid #b00020' : '4px solid #0a7d2a'; } catch(_) {}
    }
  } catch (_) {}
}
"""
    # Insert just before extractPytestSummary() if present, else before IIFE close
    m = re.search(r'\nfunction\s+extractPytestSummary\s*\(', src)
    if m:
        insert_at = m.start()
        src = src[:insert_at] + apply_fn + src[insert_at:]
    else:
        m2 = re.search(r'\)\(document,\s*window\);\s*$', src)
        insert_at = m2.start() if m2 else len(src)
        src = src[:insert_at] + apply_fn + src[insert_at:]
    changed.append("inserted applyStep()")

# --- B) Ensure addEventListener(..., applyStep, ...) line exists inside mountActions ---
if not re.search(r'btnApply\.addEventListener\(\s*[\'"]click[\'"]\s*,\s*applyStep', src):
    # Try to place it alongside the other listeners inside mountActions
    # After the accept listener is a stable anchor in your file
    pat_block = r'(btnAccept\.addEventListener\(\s*[\'"]click[\'"]\s*,\s*accept[^;]*;\s*\))'
    repl = r"\1\n    btnApply.addEventListener('click', applyStep, { passive: true });"
    new_src, n = re.subn(pat_block, repl, src, count=1, flags=re.DOTALL)
    if n == 0:
        # Fallback: after the wireApplyButton call, if present
        pat_wire = r'(wireApplyButton\([^)]+\);\s*)'
        repl2 = r"\1\n    btnApply.addEventListener('click', applyStep, { passive: true });"
        new_src, n = re.subn(pat_wire, repl2, src, count=1, flags=re.DOTALL)
    if n == 0:
        # Last resort: before mountActions() close brace
        new_src, n = re.subn(r'(\n\s*}\s*\n\s*function\s+onReady\s*\()', 
                             "\n    btnApply.addEventListener('click', applyStep, { passive: true });\n\\1",
                             src, count=1, flags=re.DOTALL)
    if n > 0:
        src = new_src
        changed.append("added btnApply.addEventListener('click', applyStep, …)")

after = sha256(src)

if changed:
    # backup
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{PATH}.bak_{ts}"
    with open(bak, "w", encoding="utf-8", newline="") as f:
        f.write(open(PATH, "r", encoding="utf-8").read())
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("status: UPDATED")
    print("backup:", bak)
    print("sha256_before:", before)
    print("sha256_after :", after)
    for c in changed:
        print("-", c)
else:
    print("status: NOOP")
    print("sha256:", before)
