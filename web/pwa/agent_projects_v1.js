(function (win) {
    const { PA } = win;
    const el = PA.el;

    async function loadProjects() {
        const listRoute = PA.hasRoute('/agent/projects') ? '/agent/projects'
            : PA.hasRoute('/agent/project/list') ? '/agent/project/list'
                : null;
        const chip = el('projChip');
        if (!listRoute) { if (chip) chip.style.display = 'none'; return; }

        try {
            const r = await PA.GET(listRoute); const j = await r.json();
            const sel = el('projectSelect'); sel.innerHTML = '';
            (j.projects || j.list || []).forEach(p => {
                const o = document.createElement('option');
                o.value = (p.slug || p.name || p.id || p.path || '');
                o.textContent = (p.title || p.name || p.slug || o.value || 'unnamed');
                sel.appendChild(o);
            });
            if (j.active) { sel.value = (j.active.slug || j.active.name || j.active.id || ''); }

            sel.onchange = async () => {
                const v = sel.value;
                const selRoute = PA.hasRoute('/agent/project/select') ? '/agent/project/select'
                    : PA.hasRoute('/agent/project/activate') ? '/agent/project/activate'
                        : null;
                if (!selRoute) return;
                try { await PA.POST(selRoute, { id: v }); } catch { }
                if (win.PA_APP) { win.PA_APP.refreshPlanOnce(); win.PA_APP.refreshSummaryOnce(); win.PA_APP.refreshRecentOnce(); }
            };

            el('newProjectBtn').onclick = async () => {
                const createRoute = PA.hasRoute('/agent/project/new') ? '/agent/project/new' : null;
                if (!createRoute) return;
                const name = prompt('New project slug (e.g. suspension_opt)'); if (!name) return;
                const desc = prompt('Short description', '') || ''; const owner = 'admin';
                try { const r = await PA.POST(createRoute, { name, owner, description: desc }); const j = await r.json().catch(() => ({})); el('statusRight').textContent = (j.ok ? 'Created ' : 'HTTP ' + (r.status || '')) + ' ' + (j.path || ''); } catch { }
                await loadProjects(); if (win.PA_APP) win.PA_APP.refreshPlanOnce();
            };
        } catch {
            if (chip) chip.style.display = 'none';
        }
    }

    win.PA_PROJECTS = { load: loadProjects };
})(window);
