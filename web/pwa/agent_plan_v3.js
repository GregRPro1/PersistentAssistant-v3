// Agent Plan v3 — self-contained renderer + editor.
// - No external deps: uses window.PA {GET,POST,setBusy,badge} from agent.html inline core.
// - Reads /agent/plan, shows path, color-coded totals, tree with fold, details pane,
//   status apply (POST /agent/plan/update if available), jump-to-active, tree font size.

(function (win, doc) {
    const $ = (id) => doc.getElementById(id);
    const PA = win.PA || { GET: (p) => fetch(p), POST: (p, b) => fetch(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b || {}) }), setBusy: () => { }, badge: () => { } };

    // ---- status helpers ----
    const norm = (s) => String(s || "").toLowerCase()
        .replace(/completed?/, "done")
        .replace(/in-?progress|active|working|running/, "in_progress")
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
        const out = []; String(sid || "").split(".").forEach(p => {
            if (/^\d+$/.test(p)) out.push({ k: 0, v: parseInt(p, 10) });
            else out.push({ k: 1, v: String(p).toLowerCase() });
        }); return out;
    }
    function cmpId(a, b) {
        const A = natKey(a), B = natKey(b), n = Math.max(A.length, B.length);
        for (let i = 0; i < n; i++) {
            const ax = A[i] || { k: 0, v: -1 }, bx = B[i] || { k: 0, v: -1 };
            if (ax.k !== bx.k) return ax.k - bx.k;
            if (ax.v < bx.v) return -1; if (ax.v > bx.v) return 1;
        } return 0;
    }

    // ---- text helpers ----
    const firstSentence = (s) => String(s || "").split(/[\.\!\?\n]/, 1)[0].trim();
    const titleOf = (n) => (n.title && n.title.trim()) || firstSentence(n.description || n.desc) || String(n.id || "");
    const bodyOf = (n) => (n.description || n.desc || "").trim();

    // ---- collect model from either phases[*].steps[*] or server tree
    function fromPhases(doc) {
        const steps = [];
        (Array.isArray(doc.phases) ? doc.phases : []).forEach(ph => {
            const ptitle = ph.name || ph.title || ("Phase " + (ph.id || ""));
            const pid = String(ph.id != null ? ph.id : "").trim();
            if (pid) steps.push({ id: pid, title: ptitle, status: norm(ph.status || ""), description: "", children: [] });
            (ph.steps || []).forEach(s => {
                steps.push({
                    id: String(s.id || "").trim(),
                    title: s.title,
                    description: s.description || s.desc || "",
                    status: norm(s.status),
                    items: Array.isArray(s.items) ? s.items : [],
                    files: Array.isArray(s.files) ? s.files : [],
                    tags: Array.isArray(s.tags) ? s.tags : [],
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
                id: String(n.id),
                title: n.title, description: n.description || n.desc || "",
                status: norm(n.status),
                items: Array.isArray(n.items) ? n.items : [],
                files: Array.isArray(n.files) ? n.files : [],
                tags: Array.isArray(n.tags) ? n.tags : [],
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

        const map = Object.create(null);
        steps.forEach(s => { if (s.id) map[s.id] = Object.assign({ children: [] }, s); });

        const roots = [];
        Object.keys(map).sort(cmpId).forEach(id => {
            const pid = parentId(id);
            if (pid && map[pid]) map[pid].children.push(map[id]);
            else roots.push(map[id]);
        });
        (function sortRec(lst) { lst.sort((a, b) => cmpId(a.id, b.id)); lst.forEach(n => sortRec(n.children)); })(roots);

        const totals = { done: 0, in_progress: 0, blocked: 0, planned: 0 };
        Object.keys(map).forEach(k => { totals[norm(map[k].status)] = (totals[norm(map[k].status)] || 0) + 1; });

        return { tree: roots, totals: { done: totals.done || 0, in_progress: totals.in_progress || 0, blocked: totals.blocked || 0, todo: totals.planned || 0 }, source };
    }

    // ---- rendering ----
    let selected = null;
    function showCounts(t) {
        const el = $("planCounts"); if (!el) return;
        el.innerHTML =
            '<span class="dot green"></span>Done ' + (t.done || 0) + ' &nbsp; ' +
            '<span class="dot amber"></span>Working ' + (t.in_progress || 0) + ' &nbsp; ' +
            '<span class="dot red"></span>Blocked ' + (t.blocked || 0) + ' &nbsp; ' +
            '<span class="dot blue"></span>Todo ' + (t.todo || 0);
    }
    function showDetails(n) {
        const box = $("planDetails"); if (!box) return;
        box.innerHTML = "";
        const head = doc.createElement("div");
        head.innerHTML = "<b>" + n.id + (titleOf(n) ? (" — " + titleOf(n)) : "") + "</b> " +
            '<span class="badge ' + statusClass(n.status) + '">' + norm(n.status) + '</span>';
        box.appendChild(head);

        const body = bodyOf(n);
        if (body) { const pre = doc.createElement("pre"); pre.className = "codebox"; pre.textContent = body; box.appendChild(pre); }

        const addList = (label, arr, fmt) => {
            if (!arr || !arr.length) return;
            const t = doc.createElement("div"); t.className = "hint"; t.style.margin = "6px 0 2px 0"; t.textContent = label; box.appendChild(t);
            const ul = doc.createElement("ul"); ul.className = "plain";
            arr.forEach(x => { const li = doc.createElement("li"); li.textContent = fmt ? fmt(x) : (typeof x === "string" ? x : JSON.stringify(x)); ul.appendChild(li); });
            box.appendChild(ul);
        };
        addList("Files", n.files);
        addList("Success", n.success);
        addList("Tags", n.tags);
        addList("Subtasks", n.items, it => (statusIcon(it.status) + " " + (it.title || "")).trim());

        // sync status selector
        const sel = $("edStatusSel"); if (sel) sel.value = norm(n.status || "planned");
        // remember selected
        selected = n;
    }
    function makeNode(n) {
        const li = doc.createElement("li"); li.className = "tree-item";
        const kids = Array.isArray(n.children) ? n.children : [];
        const caret = doc.createElement("span"); caret.className = kids.length ? "caret down" : "caret";
        const ico = doc.createElement("span"); ico.className = "ico"; ico.textContent = statusIcon(n.status);
        const dot = doc.createElement("span"); dot.className = "dot " + statusClass(n.status);
        const lbl = doc.createElement("span"); lbl.className = "lbl"; lbl.textContent = " " + n.id + (titleOf(n) ? (" — " + titleOf(n)) : "");
        li.appendChild(caret); li.appendChild(ico); li.appendChild(dot); li.appendChild(lbl);

        const ul = doc.createElement("ul"); ul.className = "plain";
        kids.forEach(c => ul.appendChild(makeNode(c)));
        if (!kids.length) ul.classList.add("hidden");
        li.appendChild(ul);

        const select = () => { showDetails(n); };
        [lbl, ico, dot].forEach(el => el.addEventListener("click", select, { passive: true }));

        if (kids.length) {
            caret.addEventListener("click", () => {
                if (caret.classList.contains("down")) { caret.classList.remove("down"); ul.classList.add("hidden"); }
                else { caret.classList.add("down"); ul.classList.remove("hidden"); }
            }, { passive: true });
        }
        return li;
    }
    function render(model) {
        const tree = $("planTree"), det = $("planDetails");
        if (tree) tree.innerHTML = "";
        if (det) det.textContent = "[select a step to see details]";
        const root = doc.createElement("ul"); root.className = "plain";
        (model.tree || []).forEach(n => root.appendChild(makeNode(n)));
        tree.appendChild(root);
        showCounts(model.totals || {});
    }

    // ---- fetch + wire ----
    let lastModel = null;
    async function refresh() {
        PA.setBusy(true, "Loading plan…"); PA.badge("planState", "wait", "loading");
        try {
            const r = await PA.GET("/agent/plan");
            const j = await r.json();
            const plan = (j && j.plan) ? j.plan : j;
            lastModel = buildModel(plan);

            const src = plan.plan_path || plan.path || j.plan_path || j.path || "server/tree";
            const ps = $("planSource"); if (ps) ps.textContent = src;

            render(lastModel);
            PA.badge("planState", "ok", "ok");
        } catch (e) {
            console.error("plan refresh error", e);
            PA.badge("planState", "err", "error");
        } finally {
            PA.setBusy(false);
        }
    }

    function jumpToActive() {
        if (!lastModel) return;
        // pick first in_progress else first planned
        let pick = null;
        function scan(list) {
            for (const n of list) {
                if (!pick && norm(n.status) === "in_progress") { pick = n; return true; }
                if (scan(n.children || [])) return true;
            } return false;
        }
        if (!scan(lastModel.tree || [])) {
            function scan2(list) {
                for (const n of list) {
                    if (!pick && norm(n.status) === "planned") { pick = n; return true; }
                    if (scan2(n.children || [])) return true;
                } return false;
            }
            scan2(lastModel.tree || []);
        }
        if (pick) {
            showDetails(pick);
            // try to scroll into view: find the label text
            const want = pick.id + (titleOf(pick) ? (" — " + titleOf(pick)) : "");
            const labels = Array.from(doc.querySelectorAll("#planTree .lbl"));
            const found = labels.find(l => l.textContent && l.textContent.trim().startsWith(" " + want));
            if (found) { found.scrollIntoView({ block: "center" }); }
        }
    }

    async function applyStatus() {
        if (!selected) return;
        const s = $("edStatusSel").value || "planned";
        PA.setBusy(true, "Updating…");
        try {
            // try write endpoint
            const r = await PA.POST("/agent/plan/update", { id: selected.id, status: s });
            const j = await r.json().catch(() => ({ ok: false }));
            if (j && j.ok) {
                await refresh();
                $("planDetails").insertAdjacentHTML("beforeend", '<div class="hint" style="margin-top:6px">Updated via /agent/plan/update</div>');
            } else {
                // fallback: show CLI for manual run
                const cli = 'python tools\\py\\plan_step_add.py --id "' + selected.id + '" --status ' + s;
                const pre = doc.createElement("pre"); pre.className = "codebox"; pre.textContent = cli;
                $("planDetails").appendChild(pre);
            }
        } catch (e) {
            const pre = doc.createElement("pre"); pre.className = "codebox"; pre.textContent = String(e || "error");
            $("planDetails").appendChild(pre);
        } finally {
            PA.setBusy(false);
        }
    }

    // tree font-size controls
    (function () {
        const t = $("planTree");
        const minus = $("treeFsMinus"), plus = $("treeFsPlus"), reset = $("treeFsReset");
        function setSize(cls) { t.classList.remove("small", "base", "large"); t.classList.add(cls); }
        minus.addEventListener("click", () => setSize("small"), { passive: true });
        reset.addEventListener("click", () => setSize("base"), { passive: true });
        plus.addEventListener("click", () => setSize("large"), { passive: true });
    })();

    // resizable split (simple)
    (function () {
        const split = $("planSplit"), gut = $("planGutter");
        let drag = false, x0 = 0, leftW = 0, total = 0;
        gut.addEventListener("mousedown", (e) => {
            drag = true; x0 = e.clientX; const cs = getComputedStyle(split);
            const cols = (cs.gridTemplateColumns || "1fr 10px 1fr").split(" ");
            const left = $("planTree").getBoundingClientRect().width;
            leftW = left; total = split.getBoundingClientRect().width; doc.body.style.userSelect = "none";
        });
        doc.addEventListener("mousemove", (e) => {
            if (!drag) return;
            const dx = e.clientX - x0; const w = Math.max(180, Math.min(total - 240, leftW + dx));
            split.style.gridTemplateColumns = w + "px 10px 1fr";
        });
        doc.addEventListener("mouseup", () => { drag = false; doc.body.style.userSelect = ""; });
    })();

    // wire buttons
    doc.addEventListener("DOMContentLoaded", () => {
        const b = $("planRefresh"); if (b) b.addEventListener("click", refresh, { passive: true });
        const j = $("jumpActive"); if (j) j.addEventListener("click", jumpToActive, { passive: true });
        const a = $("applyStatus"); if (a) a.addEventListener("click", applyStatus, { passive: true });
        // auto-load when Plan is present
        setTimeout(refresh, 60);
    });

    // expose for diag
    win.PA_PLAN = { refresh, jumpToActive };
})(window, document);
