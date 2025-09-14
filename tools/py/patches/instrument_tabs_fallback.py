import io, os, re

# tools/py/patches -> tools/py -> tools -> <repo root>
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PATH = os.path.join(ROOT, "web", "pwa", "settings_ext.js")

APPEND_SNIPPET = r"""
/* ext-fallback binder + boot flag */
(function(doc){
  try{
    // brief boot message
    try {
      var sr = doc.getElementById('statusRight');
      if (sr) { sr.textContent = 'ext ok'; setTimeout(function(){ sr.textContent=''; }, 1500); }
    } catch(_) {}

    // bind tabs only if not already bound
    var tabs = Array.prototype.slice.call(doc.querySelectorAll('.tab'));
    tabs.forEach(function(t){
      if (t.dataset && t.dataset.extBound) return;
      t.dataset.extBound = '1';
      t.addEventListener('click', function(){
        var name = t.getAttribute('data-tab');
        Array.prototype.slice.call(doc.querySelectorAll('.tab')).forEach(function(x){ x.classList.remove('active'); });
        t.classList.add('active');
        Array.prototype.slice.call(doc.querySelectorAll('[data-pane]')).forEach(function(p){
          p.classList.toggle('hidden', p.getAttribute('data-pane') !== name);
        });
      }, { passive: true });
    });
  } catch(e) { try { console.error('[ext-actions-v2] fallback binder error:', e); } catch(_) {} }
})(document);
"""

def main():
  with io.open(PATH, 'r', encoding='utf-8') as f:
    src = f.read()
  if 'ext-fallback binder + boot flag' in src:
    print('status: NOOP (already present)'); return
  # Prefer inserting just before the final "})(document, window);" (end of IIFE)
  m = re.search(r'\}\)\(document,\s*window\);\s*$', src, flags=re.S)
  if m:
    new = src[:m.start()] + APPEND_SNIPPET + src[m.start():]
  else:
    new = src + "\n" + APPEND_SNIPPET + "\n"

  bak = PATH + ".bak_tabs_fallback"
  if not os.path.exists(bak):
    with io.open(bak, 'w', encoding='utf-8') as f: f.write(src)
  with io.open(PATH, 'w', encoding='utf-8') as f:
    f.write(new)
  print('status: UPDATED'); print('path:', PATH)

if __name__ == "__main__":
  main()
