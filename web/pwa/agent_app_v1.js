(function (win, doc) {
    const { PA } = win;
    const el = PA.el;

    // SUMMARY
    let sumBusy = false;
    async function refreshSummary() {
        if (sumBusy) return; sumBusy = true; PA.setBusy(true, 'Loading summary…'); PA.setBadge('sumState', 'wait', 'loading');
        try { const r = await PA.GET('/agent/summary'); const j = await r.json(); PA.logJson('summary', j); PA.setBadge('sumState', 'ok', 'ok'); }
        catch { PA.setBadge('sumState', 'err', 'error'); }
        finally { PA.setBusy(false); sumBusy = false; }
    }
    const refreshSummaryOnce = () => refreshSummary();
    doc.addEventListener('DOMContentLoaded', () => { el('refresh')?.addEventListener('click', refreshSummaryOnce, { passive: true }); });

    // RECENT
    let recentBusy = false;
    async function refreshRecent() {
        if (recentBusy) return; recentBusy = true;
        try {
            const r = await PA.GET('/agent/recent'); const j = await r.json();
            const box = el('recentBox'); box.innerHTML = '';
            const rec = j.recent || {}; const a = rec.approvals || [];
            const ul = doc.createElement('ul'); a.forEach(n => { const li = doc.createElement('li'); li.textContent = n; ul.appendChild(li); });
            const notes = doc.createElement('pre'); notes.className = 'codebox'; notes.textContent = (rec.notes_tail || '').trim() || '[no notes]';
            box.appendChild(doc.createTextNode('Approvals (latest):')); box.appendChild(ul);
            box.appendChild(doc.createTextNode('Notes tail:')); box.appendChild(notes);
        } catch (e) { el('recentBox').textContent = 'ERR ' + e.message; }
        finally { recentBusy = false; }
    }
    const refreshRecentOnce = () => refreshRecent();
    doc.addEventListener('DOMContentLoaded', () => { el('rrefresh')?.addEventListener('click', refreshRecentOnce, { passive: true }); });

    // NEXT
    doc.addEventListener('DOMContentLoaded', () => {
        const nb = el('nextBtn');
        nb?.addEventListener('click', async () => {
            PA.setBusy(true, 'Requesting NEXT…'); PA.setBadge('nextState', 'wait', 'waiting');
            try {
                const b = { action: 'APPROVE_NEXT', data: null, timestamp: Math.floor(Date.now() / 1000), nonce: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) };
                const r = await PA.POST('/agent/next2', b); const t = await r.text();
                try { const j = JSON.parse(t); const pre = doc.createElement('pre'); pre.className = 'codebox'; pre.textContent = PA.pretty(j.summary || j); el('nextBox').innerHTML = ''; el('nextBox').appendChild(pre); PA.setBadge('nextState', 'ok', 'ok'); }
                catch { PA.setBadge('nextState', 'err', 'bad json'); }
            } catch (e) { PA.setBadge('nextState', 'err', 'error'); }
            finally { PA.setBusy(false); }
        }, { passive: true });
    });

    // NOTES
    async function notes(mode) { return PA.POST('/agent/notes', { mode, text: el('notesText').value }); }
    doc.addEventListener('DOMContentLoaded', () => {
        el('notesLoad')?.addEventListener('click', async () => {
            PA.setBusy(true, 'Loading notes…');
            try { const r = await PA.GET('/agent/notes'); const j = await r.json(); el('notesText').value = j.text || ''; PA.setBadge('notesState', 'ok', 'loaded'); }
            catch { PA.setBadge('notesState', 'err', 'error'); }
            finally { PA.setBusy(false); }
        });
        el('notesSave')?.addEventListener('click', async () => {
            if (!PA.commsEnabled()) return; PA.setBusy(true, 'Saving notes…');
            try { const r = await notes('set'); const t = await r.text(); PA.logPre('notesOut', t); PA.setBadge('notesState', 'ok', 'saved'); }
            catch { PA.setBadge('notesState', 'err', 'error'); }
            finally { PA.setBusy(false); }
        });
        el('notesAppend')?.addEventListener('click', async () => {
            if (!PA.commsEnabled()) return; PA.setBusy(true, 'Appending…');
            try { const r = await notes('append'); const t = await r.text(); PA.logPre('notesOut', t); PA.setBadge('notesState', 'ok', 'appended'); }
            catch { PA.setBadge('notesState', 'err', 'error'); }
            finally { PA.setBusy(false); }
        });
        el('makeBrief')?.addEventListener('click', async () => {
            if (!PA.commsEnabled()) return; PA.setBusy(true, 'Assembling brief…');
            try { const r = await PA.POST('/agent/brief'); const t = await r.text(); PA.logPre('notesOut', t); }
            catch (e) { PA.logPre('notesOut', 'ERR ' + e.message); }
            finally { PA.setBusy(false); }
        });
    });

    // ACTIONS
    doc.addEventListener('DOMContentLoaded', () => {
        el('askBtn')?.addEventListener('click', async () => {
            if (!PA.commsEnabled()) return;
            const text = (el('askText').value || '').trim(); if (!text) { PA.logPre('askOut', 'Enter a prompt'); return; }
            PA.setBusy(true, 'Sending ASK…');
            try { const r = await PA.POST('/agent/ask', { text, nonce: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), timestamp: Math.floor(Date.now() / 1000) }); const t = await r.text(); try { PA.logJson('askOut', JSON.parse(t)); } catch { PA.logPre('askOut', t); } PA.setBadge('actState', 'ok', 'queued'); }
            catch { PA.setBadge('actState', 'err', 'error'); }
            finally { PA.setBusy(false); }
        });
        el('chooseBtn')?.addEventListener('click', async () => {
            if (!PA.commsEnabled()) return;
            const step = (el('chooseStep').value || '').trim(); if (!step) { PA.logPre('chooseOut', 'Enter a step id'); return; }
            PA.setBusy(true, 'Choosing ' + step + '…');
            try { const r = await PA.POST('/agent/choose', { step_id: step, nonce: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), timestamp: Math.floor(Date.now() / 1000) }); const t = await r.text(); try { PA.logJson('chooseOut', JSON.parse(t)); } catch { PA.logPre('chooseOut', t); } }
            catch (e) { PA.logPre('chooseOut', 'ERR ' + e.message); }
            finally { PA.setBusy(false); }
        });
        el('proc')?.addEventListener('click', async () => { if (!PA.commsEnabled()) return; PA.setBusy(true, 'Processing approvals…'); try { await PA.POST('/agent/process2'); } catch { } finally { PA.setBusy(false); } });
    });

    // COMPOSE (gated)
    async function setupCompose() {
        const panel = el('paComposePanel');
        if (!PA.hasRoute('/agent/compose')) { panel.classList.add('hidden'); return; }
        panel.classList.remove('hidden');
        async function compose() {
            const hdr = PA.tok ? { 'Authorization': 'Bearer ' + PA.tok } : {};
            el('composeStatus').textContent = 'building...';
            try {
                const r = await fetch(PA.uiBase + '/agent/compose', { method: 'POST', headers: hdr });
                if (!r.ok) { el('composeStatus').textContent = 'HTTP ' + r.status; el('composeText').value = ''; return; }
                const j = await r.json();
                if (!j.ok) { el('composeStatus').textContent = j.err || 'failed'; el('composeText').value = ''; return; }
                el('composeText').value = j.prompt || ''; el('composeStatus').textContent = 'ok ' + (j.path || '');
            } catch { el('composeStatus').textContent = 'error'; }
        }
        function copy() { const ta = el('composeText'); ta.select(); try { document.execCommand('copy'); } catch { } }
        el('btnCompose').addEventListener('click', compose, { passive: true });
        el('btnComposeCopy').addEventListener('click', copy, { passive: true });
    }

    async function boot() {
        PA.wireBasics();
        await PA.discoverRoutes();
        await setupCompose();
        if (win.PA_PROJECTS) await win.PA_PROJECTS.load();

        // polls
        PA.pollDaily(); setInterval(PA.pollDaily, 30000);
        PA.pollWorker(); setInterval(PA.pollWorker, 5000);
        setInterval(PA.pollApprovals, 10000);

        // initial pulls
        refreshSummaryOnce();
        if (win.PA_PLAN) await win.PA_PLAN.refresh();
        refreshRecentOnce();

        // idle auto-off
        let lastUserTs = Date.now();
        ['pointerdown', 'keydown', 'touchstart', 'scroll'].forEach(ev => document.addEventListener(ev, () => { lastUserTs = Date.now(); }, { passive: true }));
        setInterval(() => { if (!PA.busy && Date.now() - lastUserTs > 300000 && PA.commsEnabled()) { PA.setComms(false); } }, 15000);

        // exports for desktop app
        win.PA_APP = {
            refreshPlanOnce: () => win.PA_PLAN && win.PA_PLAN.refresh(),
            refreshSummaryOnce,
            refreshRecentOnce,
            selectProject: (id) => { const s = el('projectSelect'); if (!s) return; s.value = id; s.dispatchEvent(new Event('change')); }
        };
    }

    document.addEventListener('DOMContentLoaded', boot);
})(window, document);
