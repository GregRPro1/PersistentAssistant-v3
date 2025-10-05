(function (win, doc) {
    // ===== crash banner (first error only) =====
    (function () {
        var shown = false;
        function banner(msg) {
            if (shown) return; shown = true;
            try {
                var d = doc.createElement('div');
                d.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:999999;background:#1f2937;color:#fff;border:1px solid #ef4444;padding:8px 10px;border-radius:8px;font:12px system-ui';
                d.textContent = 'UI runtime error: ' + msg;
                doc.body.appendChild(d);
            } catch (_) { }
        }
        win.addEventListener('error', function (e) { banner((e && (e.message || e.error)) || 'error'); });
        win.addEventListener('unhandledrejection', function (e) { var r = e && e.reason; banner((r && (r.message || String(r))) || 'promise rejection'); });
    })();

    // ===== small utils =====
    function el(id) { return doc.getElementById(id); }
    function qa(sel) { return Array.prototype.slice.call(doc.querySelectorAll(sel)); }
    var uiBase = win.location.origin;

    function escapeHtml(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
    function jsonHtml(objOrStr) {
        var s = (typeof objOrStr === 'string') ? objOrStr : JSON.stringify(objOrStr || {}, null, 2);
        try { if (typeof objOrStr === 'string') s = JSON.stringify(JSON.parse(objOrStr), null, 2); } catch (_) { }
        s = escapeHtml(s);
        return s.replace(/("(?:\\.|[^"\\])*"(?=\s*:)|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (m) {
            if (m.charAt(0) === '"') return (/":$/.test(m) ? '<span class="j-key">' + m + '</span>' : '<span class="j-str">' + m + '</span>');
            if (m === 'true' || m === 'false') return '<span class="j-bool">' + m + '</span>';
            if (m === 'null') return '<span class="j-null">' + m + '</span>';
            return '<span class="j-num">' + m + '</span>';
        });
    }

    // ===== public core =====
    var PA = {
        uiBase: uiBase,
        routes: {},
        busy: false,
        workerStr: '',
        tok: (win.localStorage && win.localStorage.getItem('pa_token')) || '',
        el: el, qa: qa,
        pretty: function (o) { try { return JSON.stringify(o, null, 2); } catch (e) { return String(o); } },
        setBadge: function (id, cls, txt) { var b = el(id); if (!b) return; b.className = 'badge ' + (cls || ''); b.textContent = txt || ''; },
        setDot: function (id, cls) { var d = el(id); if (!d) return; d.className = 'dot ' + cls; },
        logPre: function (id, val) { var p = el(id); if (!p) return; p.textContent = (typeof val === 'string') ? val : PA.pretty(val); },
        logJson: function (id, val) { var p = el(id); if (!p) return; p.className += ' codebox'; p.innerHTML = jsonHtml(val); },
        ts: function () { return new Date().toLocaleTimeString(); },

        _timer: null, _start: 0,
        setBusy: function (b, msg) {
            PA.busy = b;
            var bi = el('busyIcon'); if (bi) { if (bi.classList) { bi.classList.toggle('hidden', !b); } }
            var sl = el('statusLeft'); if (sl) { sl.textContent = msg || (b ? 'Working…' : 'Ready'); }
            if (b) {
                PA._start = Date.now();
                if (PA._timer) clearInterval(PA._timer);
                PA._timer = setInterval(function () {
                    var s = Math.floor((Date.now() - PA._start) / 1000);
                    var sr = el('statusRight');
                    if (sr) sr.textContent = '⏱ ' + String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0') + ' · ' + (PA.workerStr || '');
                }, 500);
            } else {
                if (PA._timer) clearInterval(PA._timer);
                var sr2 = el('statusRight'); if (sr2) sr2.textContent = PA.workerStr || '';
            }
        },

        commsEnabled: function () { return !win.localStorage || win.localStorage.getItem('pa_comms') !== '0'; },
        setComms: function (v) {
            if (win.localStorage) win.localStorage.setItem('pa_comms', v ? '1' : '0');
            var cl = el('commsLbl'); if (cl) cl.textContent = 'Comms: ' + (v ? 'ON' : 'OFF');
            PA.setDot('commsDot', v ? 'green' : 'amber');
            var sl = el('statusLeft'); if (!v && sl) sl.textContent = 'Interaction locked (comms off)';
        },
        isLocked: function () { return !!(win.localStorage && win.localStorage.getItem('pa_locked') === '1'); },
        setLocked: function (v) {
            if (win.localStorage) win.localStorage.setItem('pa_locked', v ? '1' : '0');
            var ll = el('lockLbl'); if (ll) ll.textContent = v ? 'Locked' : 'Unlocked';
            PA.setDot('lockDot', v ? 'amber' : 'green');
        },

        _authHeaders: function () {
            var h = {}; if (PA.tok && PA.tok.trim()) h.Authorization = 'Bearer ' + PA.tok.trim(); return h;
        },
        GET: function (path, opt) {
            var init = opt || {};
            if (!init.headers) init.headers = {};
            var h = PA._authHeaders(); for (var k in h) { init.headers[k] = h[k]; }
            init.cache = init.cache || 'no-store';
            return win.fetch(PA.uiBase + path, init);
        },
        POST: function (path, body) {
            if (doc.hidden) { var hint = el('hint'); if (hint) hint.textContent = 'Page hidden — blocked'; return Promise.reject(new Error('hidden')); }
            if (PA.isLocked()) { var hint2 = el('hint'); if (hint2) hint2.textContent = 'Locked — hold Unlock in Settings'; return Promise.reject(new Error('locked')); }
            if (!PA.commsEnabled()) { var hint3 = el('hint'); if (hint3) hint3.textContent = 'Comms OFF — enable in Settings'; return Promise.reject(new Error('comms_off')); }
            var init = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : '{}' };
            var h = PA._authHeaders(); for (var k in h) { init.headers[k] = h[k]; }
            return win.fetch(PA.uiBase + path, init);
        },
        hasRoute: function (p) { return !!PA.routes[p]; },
        discoverRoutes: function () {
            return PA.GET('/__routes__').then(function (r) { return r.json(); }).then(function (j) {
                var list = j && j.routes || [];
                for (var i = 0; i < list.length; i++) { if (list[i] && list[i].rule) { PA.routes[list[i].rule] = true; } }
            }).catch(function () { });
        },

        pollDaily: function () {
            return PA.GET('/agent/daily_status').then(function (r) { return r.json(); }).then(function (j) {
                PA.setDot('dailyDot', j && j.ok === true ? 'green' : (j && j.ok === false ? 'red' : 'amber'));
                var dl = el('dailyLbl'); if (dl) dl.textContent = (j && j.last_run) || '—';
            }).catch(function () { PA.setDot('dailyDot', 'red'); var dl = el('dailyLbl'); if (dl) dl.textContent = 'error'; });
        },
        pollWorker: function () {
            return PA.GET('/agent/worker_status').then(function (r) { return r.json(); }).then(function (j) {
                var w = (j && j.worker) || {};
                PA.workerStr = 'calls ' + (w.calls || 0) + ' · tok ' + (w.tokens || 0) + ' · $' + (Number(w.cost_usd || 0).toFixed(4));
                var sr = el('statusRight'); if (sr && !PA.busy) sr.textContent = PA.workerStr;
            }).catch(function () { });
        },
        pollApprovals: function () {
            return PA.GET('/agent/approvals_count').then(function (r) { return r.json(); }).then(function (j) {
                if (j && j.count != null) { var hdr = doc.querySelector('.app-header .badge'); if (hdr) hdr.title = 'Approvals queued: ' + j.count; }
            }).catch(function () { });
        },

        wireBasics: function () {
            try {
                var ub = el('uiBaseBadge'); if (ub) ub.textContent = PA.uiBase;

                var tokIn = el('tok'); if (tokIn) tokIn.value = PA.tok;
                var save = el('saveTok'); if (save) { save.addEventListener('click', function () { PA.tok = (tokIn ? tokIn.value : PA.tok).trim(); if (win.localStorage) win.localStorage.setItem('pa_token', PA.tok); var sr = el('statusRight'); if (sr) sr.textContent = 'Token saved @ ' + PA.ts(); }); }

                PA.setComms(PA.commsEnabled()); var ct = el('commsToggle'); if (ct) { ct.addEventListener('click', function () { PA.setComms(!PA.commsEnabled()); }); }
                PA.setLocked(PA.isLocked()); var lb = el('lockBtn'); if (lb) { lb.addEventListener('click', function () { PA.setLocked(true); }); }
                var uh = el('unlockHold'); if (uh) { uh.addEventListener('pointerdown', function () { uh._t = setTimeout(function () { PA.setLocked(false); }, 1200); }); uh.addEventListener('pointerup', function () { clearTimeout(uh._t); }); uh.addEventListener('pointerleave', function () { clearTimeout(uh._t); }); }

                var panes = qa('[data-pane]');
                qa('.tab').forEach(function (t) {
                    t.addEventListener('click', function () {
                        qa('.tab').forEach(function (x) { x.classList.remove('active'); });
                        t.classList.add('active');
                        var name = t.getAttribute('data-tab');
                        panes.forEach(function (p) { p.classList.toggle('hidden', p.getAttribute('data-pane') !== name); });
                        var sl = el('statusLeft'); if (sl) sl.textContent = 'Viewing ' + name;
                        if (name === 'summary' && win.PA_APP && win.PA_APP.refreshSummaryOnce) win.PA_APP.refreshSummaryOnce();
                        if (name === 'plan' && win.PA_APP && win.PA_APP.refreshPlanOnce) win.PA_APP.refreshPlanOnce();
                        if (name === 'recent' && win.PA_APP && win.PA_APP.refreshRecentOnce) win.PA_APP.refreshRecentOnce();
                    }, { passive: true });
                });

                // help toggles
                qa('.help').forEach(function (btn) {
                    var id = 'help-' + btn.getAttribute('data-help');
                    btn.addEventListener('click', function () { var p = el(id); if (p) p.classList.toggle('hidden'); }, { passive: true });
                });
            } catch (e) { throw e; }
        }
    };

    // expose
    win.PA = PA;
})(window, document);
