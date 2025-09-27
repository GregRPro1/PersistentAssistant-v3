// static/js/new_project_widget.js
(function () {
    function el(tag, attrs, parent) {
        const e = document.createElement(tag);
        if (attrs) Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
        if (parent) parent.appendChild(e);
        return e;
    }

    function addButton() {
        // Try to attach into a known actions area if present; else float it.
        const host = document.getElementById("pa-actions") || document.body;
        const btn = el("button", { id: "pa-new-project-btn", style: "padding:8px 12px; border-radius:8px; cursor:pointer; margin:6px;" });
        btn.textContent = "New Project";
        if (host === document.body) {
            // float if no actions container
            btn.style.position = "fixed";
            btn.style.right = "16px";
            btn.style.bottom = "16px";
            btn.style.zIndex = "9999";
        }
        host.appendChild(btn);

        btn.addEventListener("click", async () => {
            const id = (prompt("New Project ID (lowercase, 3-40 chars)") || "").trim();
            if (!id) return;
            const title = (prompt("Project title") || "").trim();
            if (!title) return;
            const body = { id, title, template: "basic" };
            try {
                const res = await fetch("/agent/project/new", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body)
                });
                const j = await res.json();
                if (j.ok) {
                    alert(`Created: ${j.project.id}\nRoot: ${j.project.root}`);
                } else {
                    alert(`Error: ${j.error || "unknown"} (${res.status})`);
                }
            } catch (e) {
                alert("Network error creating project");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addButton);
    } else {
        addButton();
    }
})();
