(function (win, doc) {
    const d = doc.createElement('div');
    d.id = 'agent-hud';
    d.innerHTML = '<div><b>Agent HUD</b></div><div id="hud-plan">plan: –</div><div id="hud-approvals">approvals: –</div><div id="hud-worker">worker: –</div>';
    doc.body.appendChild(d);
    const origFetch = win.fetch.bind(win);
    function ts() { return new Date().toLocaleTimeString(); }
    win.fetch = async function (url, init) {
        const res = await origFetch(url, init);
        try {
            const u = (typeof url === 'string') ? url : ((url && url.url) || '');
            if (u.includes('/agent/plan')) { document.getElementById('hud-plan').textContent = 'plan: ' + res.status + ' @ ' + ts(); }
            else if (u.includes('/agent/approvals_count')) { document.getElementById('hud-approvals').textContent = 'approvals: ' + res.status + ' @ ' + ts(); }
            else if (u.includes('/agent/worker_status')) { document.getElementById('hud-worker').textContent = 'worker: ' + res.status + ' @ ' + ts(); }
        } catch { }
        return res;
    };
})(window, document);
