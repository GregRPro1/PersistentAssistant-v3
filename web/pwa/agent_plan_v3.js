// Agent Plan v3 — robust tree renderer with edit helper.
// - Prefers server `plan.phases[*].steps[*]`; falls back to `plan.tree[*]`.
// - Correct parent linking (handles 6.4.g etc.), natural id sort, coloured status.
// - Details pane + "Edit" helper that emits a CLI for tools\py\plan_step_add.py.
// - Counts are colour-coded; Go-Active button jumps to plan.active or first in_progress.

(function (win, doc) {
    const PA = win.PA || {};
    const $ = (id) => doc.getElementById(id);
    const GET = PA.GET ? PA.GET.bind(PA)
        : (path) => fetch((PA.uiBase || location.origin) + path, { cache: "no-store" });
    const setBusy = PA.setBusy || function (b, msg) { const s = $("statusLeft"); if (s) s.textContent = msg || (b ? "Working…" : "Ready"); };
    const badge = PA.setBadge || function (id, cls, txt) { const b = $(id); if (b) { b.className = "badge " + (cls || ""); b.textContent = txt || ""; } };

    // ---- status helpers ----
    const norm = (s) => String(s || "").toLowerCase()
        .replace(/completed?/, "done").replace(/in-?progress|active|working|running/, "in_progress")
        .replace(/failed?|error/, "blocked") || "planned";
    const statusClass = (s) => ({ done: "green", in_progress: "amber", blocked: "red", planned: "blue" })[norm(s)] || "blue";
    const statusIcon = (s) => ({ done: "✓", in_progress: "▶", blocked: "✖", planned: "●" })[norm(s)] || "●";

    // ---- id + sort helpers ----
    function parentId(sid) {
        const parts = String(sid || "").split(".");
        if (parts.length <= 1) return null;
        return parts.slice(0, parts.length - 1).join(".");
    }
    function natKey(sid) {
        const out = [];
        String(sid || "").split(".").forEach(p => {
            if (/^\d+$/.test(p)) out.push({ k: 0, v: parseInt(p, 10) });
            else out.push({ k: 1, v: String(p).toLowerCase() });
        });
        return out;
    }
    function cmpId(a, b) {
        const A = natKey(a), B = natKey(b), n = Math.max(A.length, B.length);
        for (let i = 0; i < n; i++) {
            const ax = A[i] || { k: 0, v: -1 }, bx = B[i] || { k: 0, v: -1 };
            if (ax.k !== bx.k) return ax.k - bx.k;
            if (ax.v < bx.v) return -1; if (ax.v > bx.v) return 1;
        }
        return 0;
    }

    // ---- text helpers ----
    const firstSentence = (s) => String(s || "").split(/[\.\!\?\n]/, 1)[0].trim();
    function titleOf(n) {
        const t = (n.title && n.title.trim()) || firstSentence(n.description || n.desc);
        if (!t || t === String(n.id || "")) return "";
        return t;
    }
    const bodyOf = (n) => (n.description || n.desc || "").trim();

    // ---- collect model ----
    function fromPhases(doc) {
        const steps = [];
        (Array.isArray(doc.phases) ? doc.phases : []).forEach(ph => {
            (ph.steps || []).forEach(s => {
                steps.push({
                    id: String(s.id || "").trim(),
                    title: s.title, description: s.description || s.desc || "",
                    status: norm(s.status), items: Array.isArray(s.items) ? s.items : [],
                    files: Array.isArray(s.files) ? s.files : [], tags: Array.isArray(s.tags) ? s.tags : [],
                    success: Array.isArray(s.success) ? s.success : []
                });
            });
        });
        return steps;
    }
    function fromTree(doc) {
        const out = [];
        (doc.tree || []).forEach(function walk(n) {
            if (!n || !n.id) return;
            out.push({
                id: String(n.id), title: n.title, description: n.description || n.desc || "",
                status: norm(n.status), items: Array.isArray(n.items) ? n.items : [],
                files: Array.isArray(n.files) ? n.files : [], tags: Array.isArray(n.tags) ? n.tags : [],
                success: Array.isArray(n.success) ? n.success : []
            });
            (n.children || []).forEach(walk);
        });
        return out;
    }

    function buildModel(planDoc) {
        let steps = fromPhases(planDoc);
        let source = "phases";
        if (!steps.length) { steps = fromTree(planDoc); source = "server/tree"; }

        const node = Object.create(null);   // id -> node
        const parent = Object.create(null); // id -> parentId

        steps.forEach(s => { if (s.id) node[s.id] = Object.assign({ children: [] }, s); });

        const roots = [];
        Object.keys(node).sort(cmpId).forEach(sid => {
            const pid = parentId(sid);
            if (pid && node[pid]) { node[pid].children.push(node[sid]); parent[sid] = pid; }
            else roots.push(node[sid]);
        });
        (function sortRec(list) {
            list.sort((a, b) => cmpId(a.id, b.id));
            list.forEach(n => sortRec(n.children));
        })(roots);

        const totals = { done: 0, in_progress: 0, blocked: 0, planned: 0 };
        Object.keys(node).forEach(k => { totals[node[k].status] = (totals[node[k].status] || 0) + 1; });

        return { tree: roots, map: node, parent, totals: { done: totals.done || 0, in_progress: totals.in_progress || 0, blocked: totals.blocked || 0, todo: totals.planned || 0 }, source };
    }

    // ---- rendering ----
    let selectedLi = null;
    let liById = Object.create(null);
    let lastModel = null;
    let lastPlan = null;

    function showDetails(n) {
        const box = $("planDetails"); if (!box) return;
        box.innerHTML = "";
        const h = doc.createElement("div");
        const t = titleOf(n);
        h.innerHTML = `<b>${n.id}${t ? ' — ' + t : ''}</b> <span class="badge ${statusClass(n.status)}">${norm(n.status)}</span>`;
        box.appendChild(h);

        const body = bodyOf(n);
        if (body) { const pre = doc.createElement("pre"); pre.className = "codebox"; pre.textContent = body; box.appendChild(pre); }

        const addList = (label, arr, fmt) => {
            if (!arr || !arr.length) return;
            const t = doc.createElement("div"); t.className = "muted"; t.style.margin = "6px 0 2px 0"; t.textContent = label;
            box.appendChild(t);
            const ul = doc.createElement("ul"); ul.className = "plain";
            arr.forEach(x => { const li = doc.createElement("li"); li.textContent = fmt ? fmt(x) : (typeof x === "string" ? x : JSON.stringify(x)); ul.appendChild(li); });
            box.appendChild(ul);
        };
        addList("Files", n.files);
        addList("Success criteria", n.success);
        addList("Tags", n.tags);
        addList("Subtasks", n.items, (it) => `${statusIcon(it.status)} ${it.title || ""}`);

        // Edit helper (CLI)
        const ed = doc.createElement("div"); ed.style.marginTop = "10px";
        ed.innerHTML = `<button id="planEditBtn" class="btn">Edit…</button> <span class="hint">Generates a CLI for tools\\py\\plan_step_add.py.</span>`;
        box.appendChild(ed);

        const openEditor = () => {
            const modal = doc.createElement("div"); modal.className = "modal";
            modal.innerHTML = `
        <div class="modal-card">
          <div class="modal-head"><b>Edit step ${n.id}</b></div>
          <div class="row"><label>Title</label><input id="edTitle" type="text" value="${(n.title || "").replace(/"/g, '&quot;')}"></div>
          <div class="row"><label>Status</label>
            <select id="edStatus">
              <option value="planned">planned</option>
              <option value="in_progress">in_progress</option>
              <option value="done">done</option>
              <option value="blocked">blocked</option>
            </select>
          </div>
          <div class="row"><label>Description</label><textarea id="edDesc" rows="6">${(body || "")}</textarea></div>
          <div class="row">
            <button id="edCopy" class="btn">Copy CLI</button>
            <button id="edClose" class="btn">Close</button>
            <span id="edMsg" class="hint"></span>
          </div>
          <pre id="edCli" class="codebox"></pre>
        </div>`;
            doc.body.appendChild(modal);
            modal.querySelector("#edStatus").value = norm(n.status);
            const gen = () => {
                const t = modal.querySelector("#edTitle").value.trim();
                const s = modal.querySelector("#edStatus").value.trim();
                const d = modal.querySelector("#edDesc").value.trim().replace(/\r\n/g, "\n");
                const cli = `python tools\\py\\plan_step_add.py --id "${n.id}" --title "${t}" --status ${s}${d ? ` --desc "${d.replace(/"/g, '\\"')}"` : ""}`;
                modal.querySelector("#edCli").textContent = cli;
                return cli;
            };
            gen();
            modal.querySelector("#edCopy").onclick = () => { const cli = gen(); navigator.clipboard.writeText(cli).then(() => { modal.querySelector("#edMsg").textContent = "Copied"; }); };
            modal.querySelector("#edClose").onclick = () => { modal.remove(); };
        };
        ed.querySelector("#planEditBtn").onclick = openEditor;
    }

    function makeNode(n) {
        const li = doc.createElement("li"); li.className = "tree-item";
        liById[n.id] = li;
        const kids = Array.isArray(n.children) ? n.children : [];
        const caret = doc.createElement("span"); caret.className = kids.length ? "caret down" : "caret leaf";
        const dot = doc.createElement("span"); dot.className = "dot " + statusClass(n.status);
        const label = doc.createElement("span"); label.className = "lbl";
        const t = titleOf(n);
        label.textContent = t ? ` ${n.id} — ${t}` : ` ${n.id}`;
        li.appendChild(caret); li.appendChild(dot); li.appendChild(label);

        const ul = doc.createElement("ul"); ul.className = "plain";
        kids.forEach(c => ul.appendChild(makeNode(c)));
        if (!kids.length) ul.classList.add("hidden");
        li.appendChild(ul);

        const select = () => {
            if (selectedLi) selectedLi.classList.remove("selected");
            selectedLi = li; selectedLi.classList.add("selected");
            showDetails(n);
        };
        [label, dot].forEach(el => el.addEventListener("click", select, { passive: true }));

        if (kids.length) {
            caret.addEventListener("click", () => {
                if (caret.classList.contains("down")) { caret.classList.remove("down"); ul.classList.add("hidden"); }
                else { caret.classList.add("down"); ul.classList.remove("hidden"); }
            }, { passive: true });
        }
        return li;
    }

    function expandAncestors(id, model) {
        const path = [];
        let cur = id;
        while (model.parent[cur]) { path.push(cur); cur = model.parent[cur]; }
        path.push(cur); // include root
        path.reverse();
        // open all nodes along the path
        for (const sid of path) {
            const li = liById[sid];
            if (!li) continue;
            const caret = li.querySelector('.caret');
            const ul = li.querySelector('ul');
            if (caret && ul) { caret.classList.add('down'); ul.classList.remove('hidden'); }
        }
    }

    function selectById(id) {
        const li = liById[id]; if (!li) return false;
        li.scrollIntoView({ block: 'center' });
        li.querySelector('.lbl')?.click(); // triggers selection + details
        return true;
    }

    function render(model) {
        liById = Object.create(null);
        const tree = $("planTree"); const det = $("planDetails");
        if (tree) tree.innerHTML = "";
        if (det) det.textContent = "[select a step to see details]";
        const root = doc.createElement("ul"); root.className = "plain";
        (model.tree || []).forEach(n => root.appendChild(makeNode(n)));
        tree.appendChild(root);

        const t = model.totals || {};
        $("planCounts").innerHTML =
            `<span class="fg-green">Done ${t.done || 0}</span> · ` +
            `<span class="fg-amber">Working ${t.in_progress || 0}</span> · ` +
            `<span class="fg-red">Blocked ${t.blocked || 0}</span> · ` +
            `<span class="fg-blue">Todo ${t.todo || 0}</span>`;
    }

    async function refreshPlan() {
        setBusy(true, "Loading plan…"); badge("planState", "wait", "loading");
        try {
            const r = await GET("/agent/plan");
            const j = await r.json();
            const plan = (j && j.plan) ? j.plan : j;
            lastPlan = plan;
            const model = buildModel(plan);
            lastModel = model;

            const src = plan.plan_path || plan.path || j.plan_path || j.path || `(${model.source})`;
            const ps = $("planSource"); if (ps) ps.textContent = src;

            render(model);
            badge("planState", "ok", "ok");
        } catch (e) {
            console.error("[plan] refresh error:", e);
            badge("planState", "err", "error");
        } finally {
            setBusy(false);
        }
    }

    function gotoActive() {
        if (!lastModel) return;
        const planActive = (lastPlan && (lastPlan.active || lastPlan.active_step)) ? (lastPlan.active || lastPlan.active_step) : null;

        let targetId = planActive;
        if (!targetId) {
            // pick first in_progress
            const ids = Object.keys(lastModel.map).sort(cmpId);
            targetId = ids.find(id => lastModel.map[id].status === 'in_progress') || ids[0];
        }
        if (!targetId) return;

        expandAncestors(targetId, lastModel);
        selectById(targetId);
    }

    win.PA_PLAN = { refresh: refreshPlan, gotoActive };

    doc.addEventListener("DOMContentLoaded", () => {
        const b = $("planRefresh"); if (b) b.addEventListener("click", refreshPlan, { passive: true });
        const g = $("planGoActive"); if (g) g.addEventListener("click", gotoActive, { passive: true });
        if (doc.querySelector('[data-pane="plan"]')) setTimeout(refreshPlan, 50);
    });
})(window, document);
