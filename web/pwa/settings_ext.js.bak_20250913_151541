// web/pwa/settings_ext.js
(function (doc, win) {
  const TAG = 'ext-inline-v2';
  const log = (...a) => console.log(`[${TAG}]`, ...a);
  const err = (...a) => console.error(`[${TAG}]`, ...a);

  // ---------- tiny helpers ----------
  function $(sel, root = doc) { return root.querySelector(sel); }
  function el(tag, cls) { const n = doc.createElement(tag); if (cls) n.className = cls; return n; }
  function row(labelText, inputEl) {
    const l = el('label'); l.textContent = labelText; l.style.alignSelf = 'center';
    const wrap = el('div'); wrap.appendChild(inputEl);
    return [l, wrap];
  }

  async function httpGet(path) {
    try {
      const r = await fetch(path, { cache: 'no-store' });
      const text = await r.text();
      let json = null;
      try { json = JSON.parse(text); } catch (_) { }
      log('GET', path, r.status, json ? '[json]' : text.slice(0, 200));
      return { ok: r.ok, status: r.status, text, json };
    } catch (e) {
      err('GET failed', path, e);
      return { ok: false, status: 0, text: String(e || 'error'), json: null };
    }
  }

  async function httpPost(path, body) {
    try {
      const r = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      const text = await r.text();
      let json = null;
      try { json = JSON.parse(text); } catch (_) { }
      log('POST', path, r.status, json ? '[json]' : text.slice(0, 200));
      return { ok: r.ok, status: r.status, text, json };
    } catch (e) {
      err('POST failed', path, e);
      return { ok: false, status: 0, text: String(e || 'error'), json: null };
    }
  }

  // The fields we expect and render as a professional-looking form
  const FIELDS = [
    { key: 'plan_file', label: 'Plan file (YAML)', type: 'text', placeholder: 'C:\\_Repos\\PersistentAssistant\\project_plan_v3.yaml' },
    { key: 'tracker_file', label: 'Tracker file (YAML)', type: 'text', placeholder: 'C:\\_Repos\\PersistentAssistant\\project\\tracker.yaml' },
    { key: 'status_path', label: 'Status path (JSON)', type: 'text', placeholder: 'data\\runtime\\agent_status.json' },
    { key: 'projects_root', label: 'Projects root', type: 'text', placeholder: 'C:\\_Repos\\PersistentAssistant' },
    { key: 'active_project', label: 'Active project', type: 'text', placeholder: 'PersistentAssistant' },
    { key: 'tests_default', label: 'Default tests path', type: 'text', placeholder: 'tests' },
    { key: 'pytest_flags_default', label: 'Default pytest flags', type: 'text', placeholder: '-q' },
    { key: 'agent_base_url', label: 'Agent base URL', type: 'text', placeholder: 'http://127.0.0.1:8782' },
    { key: 'bearer_token', label: 'Bearer token', type: 'text', placeholder: '(optional)' },
    { key: 'auto_revise_default_iters', label: 'Auto-revise default iters', type: 'number', placeholder: '2' },
    { key: 'auto_revise_ui_soft_max', label: 'Auto-revise UI soft max', type: 'number', placeholder: '3' },
  ];

  function mountSettingsForm() {
    const pane = $('section[data-pane="settings"]');
    if (!pane) { err('settings pane not found'); return; }
    log('settings pane found');

    // Container card
    const card = el('div', 'card');
    const head = el('div', 'section-head');
    const h3 = el('h3'); h3.textContent = 'Extended Settings';
    head.appendChild(h3);

    // Form grid (label | input)
    const form = el('div');
    form.style.display = 'grid';
    form.style.gridTemplateColumns = '240px 1fr';
    form.style.gap = '8px';

    // Create inputs
    const inputs = {};
    for (const f of FIELDS) {
      const inp = el('input', 'btn');
      inp.type = f.type || 'text';
      inp.placeholder = f.placeholder || '';
      inp.id = 'es_' + f.key;
      inp.style.minWidth = f.type === 'number' ? '120px' : '320px';
      const [lab, wrap] = row(f.label, inp);
      form.append(lab, wrap);
      inputs[f.key] = inp;
    }

    // Buttons + output
    const rowBtns = el('div', 'rowflex');
    const bReload = el('button', 'btn'); bReload.textContent = 'Reload';
    const bSave = el('button', 'btn'); bSave.textContent = 'Save';
    rowBtns.append(bReload, bSave);

    const out = el('pre', 'codebox scroll'); out.id = 'extSettingsOut'; out.textContent = '[no logs yet]';

    card.append(head, form, rowBtns, out);
    pane.appendChild(card);
    log('mounted settings form');

    async function load() {
      out.textContent = 'Loading…';
      const r = await httpGet('/agent/settings');
      if (!r.ok) { out.textContent = `GET /agent/settings failed (${r.status}): ${r.text}`; return; }
      const cfg = r.json || {};
      for (const f of FIELDS) {
        const v = (cfg[f.key] ?? '');
        inputs[f.key].value = (f.type === 'number' && typeof v === 'number') ? String(v) : String(v);
      }
      out.textContent = 'Loaded settings.';
    }

    async function save() {
      const body = {};
      for (const f of FIELDS) {
        let v = inputs[f.key].value;
        if (f.type === 'number') {
          const n = Number(v); v = Number.isFinite(n) ? n : 0;
        }
        body[f.key] = v;
      }
      const r = await httpPost('/agent/settings', body);
      if (!r.ok) { out.textContent = `POST /agent/settings failed (${r.status}): ${r.text}`; return; }
      out.textContent = r.json ? JSON.stringify(r.json, null, 2) : r.text;
    }

    bReload.addEventListener('click', load, { passive: true });
    bSave.addEventListener('click', save, { passive: true });
    load(); // initial
  }

  function mountActionsPane() {
    const pane = $('section[data-pane="actions"]');
    if (!pane) { err('actions pane not found'); return; }
    log('actions pane found');

    const card = el('div', 'card');
    const head = el('div', 'section-head');
    const h3 = el('h3'); h3.textContent = 'Diagnostics';
    head.appendChild(h3);

    const btn = el('button', 'btn'); btn.textContent = 'Probe next step (/agent/next2)';
    const out = el('pre', 'codebox scroll'); out.textContent = '[no results yet]';

    card.append(head, btn, out);
    pane.appendChild(card);
    log('mounted actions diagnostics');

    btn.addEventListener('click', async () => {
      out.textContent = 'Probing…';
      const r = await httpGet('/agent/next2');
      const body = r.json ? JSON.stringify(r.json, null, 2) : r.text;
      out.textContent = `GET /agent/next2 -> ${r.status}\n${body}`;
    }, { passive: true });
  }

  doc.addEventListener('DOMContentLoaded', () => {
    log('DOMContentLoaded');
    mountSettingsForm();
    mountActionsPane();
  });
})(document, window);
