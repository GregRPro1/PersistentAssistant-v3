// Plan renderer — schema-first (phases) with safe fallback to server 'tree'.
// No duplication: we render from ONE source (phases OR tree), never both.
(function (win, doc) {
    var PA = win.PA || {};
    var $ = function (id) { return doc.getElementById(id); };
    var setBusy = (PA.setBusy || function () { });
    var badge = (PA.setBadge || function () { });
    var GET = PA.GET ? PA.GET.bind(PA) : (path => fetch((PA.uiBase || "") + path, { cache: "no-store" }));

    // ---------- status helpers ----------
    function normStatus(s) {
        s = String(s || "").toLowerCase();
        if (s === "done" || s === "complete" || s === "finished") return "done";
        if (s === "in_progress" || s === "active" || s === "working" || s === "running") return "in_progress";
        if (s === "blocked" || s === "fail" || s === "failed" || s === "error") return "blocked";
        return "planned";
    }
    function statusClass(s) {
        s = normStatus(s);
        if (s === "done") return "green";
        if (s === "in_progress") return "amber";
        if (s === "blocked") return "red";
        return "blue";
    }
    function statusIcon(s) {
        s = normStatus(s);
        if (s === "done") return "✓";
        if (s === "in_progress") return "▶";
        if (s === "blocked") return "✖";
        return "●";
    }

    // ---------- text helpers ----------
    function titleOf(step) {
        var t = (step.title || "").trim();
        if (t) return t;
        var d = (step.description || "").trim();
        if (!d) return (step.id || "");
        var m = d.split(/[\.\!\?\n]/, 1)[0] || d;
        return m.trim().slice(0, 80);
    }
    function bodyOf(step) {
        return (step.description || "").trim();
    }

    // ---------- id helpers ----------
    function naturalKey(stepId) {
        var out = [];
        String(stepId || "").split(".").forEach(function (p) {
            if (/^\d+$/.test(p)) out.push({ k: 0, v: parseInt(p, 10) });
            else out.push({ k: 1, v: String(p).toLowerCase() });
        });
        return out;
    }
    function cmpId(a, b) {
        var A = naturalKey(a), B = naturalKey(b), n = Math.max(A.length, B.length);
        for (var i = 0; i < n; i++) {
            var ax = A[i] || { k: 0, v: -1 }, bx = B[i] || { k: 0, v: -1 };
            if (ax.k !== bx.k) return ax.k - bx.k;
            if (ax.v < bx.v) return -1;
            if (ax.v > bx.v) return 1;
        }
        return 0;
    }
    function parentId(sid) {
        var parts = String(sid || "").split(".");
        if (parts.length <= 1) return null;
        if (parts.length === 2) return parts[0] + "." + parts[1];
        return parts.slice(0, -1).join(".");
    }

    // ---------- collectors ----------
    function collectFromPhases(planDoc) {
        var steps = [];
        var phases = Array.isArray(planDoc.phases) ? planDoc.phases : [];
        phases.forEach(function (ph) {
            (ph.steps || []).forEach(function (s) {
                steps.push({
                    id: String(s.id || "").trim(),
                    title: s.title,
                    description: s.description,
                    status: normStatus(s.status),
                    items: Array.isArray(s.items) ? s.items : [],
                    files: Array.isArray(s.files) ? s.files : [],
                    tags: Array.isArray(s.tags) ? s.tags : [],
                    success: Array.isArray(s.success) ? s.success : []
                });
            });
        });
        return steps;
    }

    function collectFromTree(planDoc) {
        var out = [];
        function walk(n) {
            if (!n || !n.id) return;
            out.push({
                id: String(n.id),
                title: n.title,
                description: n.description || n.desc || "",
                status: normStatus(n.status),
                items: Array.isArray(n.items) ? n.items : [],
                files: Array.isArray(n.files) ? n.files : [],
                tags: Array.isArray(n.tags) ? n.tags : [],
                success: Array.isArray(n.success) ? n.success : []
            });
            (n.children || []).forEach(walk);
        }
        (planDoc.tree || []).forEach(walk);
        return out;
    }

    function buildModel(planDoc) {
        var steps = collectFromPhases(planDoc);
        var source = "phases";
        if (!steps.length) {
            steps = collectFromTree(planDoc);
            source = "tree";
        }

        // map + link
        var map = Object.create(null);
        steps.forEach(function (s) { if (s.id) map[s.id] = Object.assign({ children: [] }, s); });

        var roots = [];
        Object.keys(map).sort(cmpId).forEach(function (sid) {
            var pid = parentId(sid);
            if (pid && map[pid]) map[pid].children.push(map[sid]);
            else roots.push(map[sid]);
        });

        (function sortRec(list) {
            list.sort(function (a, b) { return cmpId(a.id, b.id); });
            list.forEach(function (n) { sortRec(n.children); });
        })(roots);

        var totals = { done: 0, in_progress: 0, blocked: 0, planned: 0 };
        steps.forEach(function (s) { totals[s.status] = (totals[s.status] || 0) + 1; });

        return {
            tree: roots,
            totals: { done: totals.done || 0, in_progress: totals.in_progress || 0, blocked: totals.blocked || 0, todo: totals.planned || 0 },
            source: source
        };
    }

    // ---------- rendering ----------
    var selectedLi = null;

    function showDetails(node) {
        var box = $("planDetails"); if (!box) return;
        var head = '<div><b>' + node.id + (titleOf(node) ? ' — ' + titleOf(node) : '') + '</b></div>' +
            '<div class="muted">status: ' + node.status + '</div>';
        box.innerHTML = head;

        var body = bodyOf(node);
        if (body) {
            var pre = doc.createElement("pre");
            pre.className = "codebox";
            pre.textContent = body;
            box.appendChild(pre);
        }

        function renderList(label, arr, fmt) {
            if (!arr || !arr.length) return;
            var h = doc.createElement("div"); h.style.margin = "6px 0 4px 0"; h.innerHTML = "<b>" + label + "</b>";
            var ul = doc.createElement("ul");
            arr.forEach(function (x) {
                var li = doc.createElement("li");
                li.textContent = fmt ? fmt(x) : (typeof x === "string" ? x : JSON.stringify(x));
                ul.appendChild(li);
            });
            box.appendChild(h); box.appendChild(ul);
        }
        renderList("Files", node.files);
        renderList("Success criteria", node.success);
        renderList("Tags", node.tags);
        renderList("Subtasks", node.items, function (it) { return statusIcon(it.status) + " " + (it.title || ""); });
    }

    function makeNode(n) {
        var li = doc.createElement("li");
        var kids = Array.isArray(n.children) ? n.children : [];
        var caret = doc.createElement("span");
        caret.className = kids.length ? "caret down" : "caret leaf";
        var icon = doc.createElement("span"); icon.textContent = statusIcon(n.status); icon.style.marginRight = "6px";
        var dot = doc.createElement("span"); dot.className = "dot " + statusClass(n.status); dot.style.marginRight = "6px";
        var label = doc.createElement("span"); label.textContent = " " + n.id + (titleOf(n) ? (" — " + titleOf(n)) : "");

        li.appendChild(caret); li.appendChild(icon); li.appendChild(dot); li.appendChild(label);

        var ul = doc.createElement("ul");
        kids.forEach(function (c) { ul.appendChild(makeNode(c)); });
        if (!kids.length) ul.classList.add("hidden");
        li.appendChild(ul);

        function select() {
            if (selectedLi) selectedLi.classList.remove("selected");
            selectedLi = li; selectedLi.classList.add("selected");
            showDetails(n);
        }
        label.addEventListener("click", select, { passive: true });
        icon.addEventListener("click", select, { passive: true });
        dot.addEventListener("click", select, { passive: true });

        if (kids.length) {
            caret.addEventListener("click", function () {
                if (caret.classList.contains("down")) { caret.classList.remove("down"); ul.classList.add("hidden"); }
                else { caret.classList.add("down"); ul.classList.remove("hidden"); }
            }, { passive: true });
        }
        return li;
    }

    function render(model) {
        var box = $("planTree"); box.innerHTML = ""; selectedLi = null;
        var root = doc.createElement("ul");
        (model.tree || []).forEach(function (n) { root.appendChild(makeNode(n)); });
        box.appendChild(root);

        var t = model.totals || {};
        $("planCounts").textContent = "Done " + (t.done || 0) +
            " • Working " + (t.in_progress || 0) +
            " • Blocked " + (t.blocked || 0) +
            " • Todo " + (t.todo || 0);

        if (!model.tree || !model.tree.length) $("planDetails").textContent = "[select a step to see details]";
    }

    async function refreshPlan() {
        setBusy(true, "Loading plan…"); badge("planState", "wait", "loading");
        try {
            var r = await GET("/agent/plan");
            var j = await r.json();
            var planDoc = (j && j.plan) ? j.plan : (j || {});
            var model = buildModel(planDoc);

            // show plan path/source if the server exposes it
            var src = planDoc.plan_path || planDoc.path || j.plan_path || j.path || "";
            var label = src ? src : "(" + (model.source === "phases" ? "server/phases" : "server/tree") + ")";
            var ps = $("planSource"); if (ps) ps.textContent = label;

            render(model);
            badge("planState", "ok", "ok");
        } catch (e) {
            console.error("[plan] refresh error:", e);
            badge("planState", "err", "error");
        } finally {
            setBusy(false);
        }
    }

    win.PA_PLAN = { refresh: refreshPlan };

    doc.addEventListener("DOMContentLoaded", function () {
        var b = $("planRefresh");
        if (b) b.addEventListener("click", refreshPlan, { passive: true });
    });
})(window, document);
