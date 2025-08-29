// web/pwa/agent_core_header_v1.js
// Minimal header helpers expected by the Agent UI.
// Provides PA.GET/POST (with bearer from localStorage), setBusy, setBadge.

(function (win, doc) {
    const uiBase = location.origin;

    function getToken() {
        try {
            return (localStorage.getItem('pa_token') || '').trim();
        } catch (_) { return ''; }
    }

    function GET(path) {
        const headers = {};
        const tok = getToken();
        if (tok) headers.Authorization = 'Bearer ' + tok;
        return fetch(uiBase + path, { cache: 'no-store', headers });
    }

    function POST(path, body) {
        const headers = { 'Content-Type': 'application/json' };
        const tok = getToken();
        if (tok) headers.Authorization = 'Bearer ' + tok;
        return fetch(uiBase + path, { method: 'POST', headers, body: JSON.stringify(body || {}) });
    }

    function setBusy(b, msg) {
        const spinner = doc.getElementById('busyIcon');
        if (spinner) spinner.classList.toggle('hidden', !b);
        const left = doc.getElementById('statusLeft');
        if (left) left.textContent = msg || (b ? 'Working…' : 'Ready');
    }

    function setBadge(id, cls, txt) {
        const el = doc.getElementById(id);
        if (!el) return;
        el.className = 'badge ' + (cls || '');
        el.textContent = txt || '';
    }

    win.PA = Object.assign(win.PA || {}, {
        uiBase, GET, POST, setBusy, setBadge
    });
})(window, document);
