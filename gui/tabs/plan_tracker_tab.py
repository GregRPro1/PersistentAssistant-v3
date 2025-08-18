# plan_tracker_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Displays and updates the development plan from project/plans/project_plan_v3.yaml.
#   Read-only tree view plus controls to Advance/Rollback the current step.
#   Current step is the first with status 'in_progress' else 'next' else the first step.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtGui import QFont, QColor, QBrush
import os
import yaml

class PlanTrackerTab(QWidget):
    """
    Plan tracker with basic controls:
      - Tree view: Phases → Steps → Items
      - Summary: Phase a of X • Step b of Y (ID s) • Overall n of N • Items u of Z
      - Buttons: Refresh, Advance Step, Rollback Step
    """
    def __init__(self, parent=None, plan_path: str | None = None):
        super().__init__(parent)
        self.plan_path = plan_path or os.path.join("project", "plans", "project_plan_v3.yaml")
        self._init_ui()
        self.refresh_plan()

    def _init_ui(self):
        root = QVBoxLayout()

        self.info_label = QLabel("Plan: loading…")
        root.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Step ID", "Description / Item", "Status"])
        self.tree.setUniformRowHeights(True)
        root.addWidget(self.tree)

        # Controls
        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Plan")
        self.refresh_btn.clicked.connect(self.refresh_plan)
        btn_row.addWidget(self.refresh_btn)

        self.advance_btn = QPushButton("Advance Step")
        self.advance_btn.clicked.connect(self.advance_step)
        btn_row.addWidget(self.advance_btn)

        self.rollback_btn = QPushButton("Rollback Step")
        self.rollback_btn.clicked.connect(self.rollback_step)
        btn_row.addWidget(self.rollback_btn)

        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self.setLayout(root)

    # ---------- IO helpers ----------

    def _read_plan(self):
        if not os.path.exists(self.plan_path):
            raise FileNotFoundError(f"Plan file not found: {self.plan_path}")
        with open(self.plan_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data

    def _write_plan(self, data: dict):
        with open(self.plan_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    # ---------- UI refresh ----------

    def refresh_plan(self):
        try:
            data = self._read_plan()
        except Exception as e:
            self.tree.clear()
            self.info_label.setText(f"Failed to read plan: {e}")
            return
        self._populate_tree(data)

    def _populate_tree(self, data: dict):
        self.tree.clear()
        phases = data.get("phases", []) if isinstance(data, dict) else []
        if not isinstance(phases, list) or not phases:
            self.info_label.setText("Invalid plan YAML: missing 'phases' list.")
            return

        X = len(phases)  # number of phases
        N = 0            # total steps across all phases

        # Locate current step
        cur = self._find_current_step_indices(phases)

        # Populate tree & compute totals
        overall_index = 0
        current_summary = "Current step: (none)"
        highlighted = False

        for pi, phase in enumerate(phases):
            phase_name = phase.get("name", f"Phase {pi+1}")
            phase_item = QTreeWidgetItem([phase_name, "", ""])
            self.tree.addTopLevelItem(phase_item)
            phase_item.setFirstColumnSpanned(True)
            phase_item.setExpanded(True)

            steps = phase.get("steps", [])
            Y = len(steps)

            for si, step in enumerate(steps):
                overall_index += 1
                N += 0  # N computed below once per step loop; we do it after
                sid = str(step.get("id", ""))
                desc = str(step.get("description", ""))
                status = str(step.get("status", ""))

                item_node = QTreeWidgetItem([sid, desc, status])

                # Current step highlight + item subnodes
                if cur and pi == cur["phase_idx"] and si == cur["step_idx"] and not highlighted:
                    # Items math
                    items = step.get("items", []) if isinstance(step.get("items", []), list) else []
                    Z = len(items)
                    u = sum(1 for it in items if str(it.get("status", "")).lower() == "done")

                    # Phase/Step numbers (1-based)
                    a = pi + 1
                    b = si + 1

                    # Overall index n of N: compute N first properly
                    # We'll compute N separately below; for now, store n
                    n = None  # temp
                    # Add items as children
                    for it in items:
                        title = str(it.get("title", ""))
                        istatus = str(it.get("status", ""))
                        sub = QTreeWidgetItem(["", title, istatus])
                        item_node.addChild(sub)

                    bold = QFont(); bold.setBold(True)
                    blue = QBrush(QColor('#004aad'))
                    for col in range(3):
                        item_node.setFont(col, bold)
                        item_node.setForeground(col, blue)
                    highlighted = True

                    # We'll finalize summary after computing N
                    current_summary = (a, b, sid, u, Z, overall_index)
                else:
                    # Non-current step: still show items (collapsed)
                    items = step.get("items", []) if isinstance(step.get("items", []), list) else []
                    for it in items:
                        title = str(it.get("title", ""))
                        istatus = str(it.get("status", ""))
                        sub = QTreeWidgetItem(["", title, istatus])
                        item_node.addChild(sub)
                    item_node.setExpanded(False)

                phase_item.addChild(item_node)

        # Compute total steps N properly
        N = sum(len(phase.get("steps", []) or []) for phase in phases)

        # Finalize summary
        if isinstance(current_summary, tuple):
            a, b, sid, u, Z, n = current_summary
            self.info_label.setText(
                f"Phase {a} of {X} • Step {b} of {len(phases[a-1].get('steps', []))} (ID {sid}) "
                f"• Overall {n} of {N} • Items {u} of {Z}"
            )
        else:
            self.info_label.setText("Current step: (none)")

    # ---------- navigation helpers ----------

    @staticmethod
    def _flatten_steps(phases: list) -> list[tuple[int,int,dict]]:
        """
        Returns a flat list of (phase_index, step_index, step_dict).
        """
        flat = []
        for pi, phase in enumerate(phases):
            steps = phase.get("steps", []) or []
            for si, step in enumerate(steps):
                flat.append((pi, si, step))
        return flat

    @staticmethod
    def _find_current_step_indices(phases: list) -> dict | None:
        """
        Find current step: 'in_progress' → 'next' → first.
        Returns dict with phase_idx, step_idx; or None.
        """
        flat = PlanTrackerTab._flatten_steps(phases)
        for pi, si, step in flat:
            if str(step.get("status", "")) == "in_progress":
                return {"phase_idx": pi, "step_idx": si}
        for pi, si, step in flat:
            if str(step.get("status", "")) == "next":
                return {"phase_idx": pi, "step_idx": si}
        return {"phase_idx": 0, "step_idx": 0} if flat else None

    # ---------- actions ----------

    def advance_step(self):
        try:
            data = self._read_plan()
            phases = data.get("phases", []) or []
            flat = self._flatten_steps(phases)
            if not flat:
                QMessageBox.warning(self, "Advance Step", "No steps found.")
                return

            # find current
            cur = self._find_current_step_indices(phases)
            if not cur:
                QMessageBox.warning(self, "Advance Step", "No current step to advance.")
                return

            cur_idx = None
            for idx, (pi, si, step) in enumerate(flat):
                if pi == cur["phase_idx"] and si == cur["step_idx"]:
                    cur_idx = idx
                    break
            if cur_idx is None:
                QMessageBox.warning(self, "Advance Step", "Could not locate current step in flat list.")
                return

            # mark current done
            cpi, csi, cstep = flat[cur_idx]
            cstep["status"] = "done"

            # set next step in_progress if exists
            if cur_idx + 1 < len(flat):
                npi, nsi, nstep = flat[cur_idx + 1]
                # demote any other 'in_progress'/'next'
                for _pi, _si, st in flat:
                    if st is not nstep and str(st.get("status", "")) in ("in_progress", "next"):
                        st["status"] = "planned" if st is not cstep else st["status"]
                nstep["status"] = "in_progress"
            else:
                # last step: keep last as done; no next
                pass

            self._write_plan(data)
            self.refresh_plan()
        except Exception as e:
            QMessageBox.critical(self, "Advance Step", f"Error: {e}")

    def rollback_step(self):
        try:
            data = self._read_plan()
            phases = data.get("phases", []) or []
            flat = self._flatten_steps(phases)
            if not flat:
                QMessageBox.warning(self, "Rollback Step", "No steps found.")
                return

            # find current
            cur = self._find_current_step_indices(phases)
            if not cur:
                QMessageBox.warning(self, "Rollback Step", "No current step to rollback.")
                return

            cur_idx = None
            for idx, (pi, si, step) in enumerate(flat):
                if pi == cur["phase_idx"] and si == cur["step_idx"]:
                    cur_idx = idx
                    break
            if cur_idx is None:
                QMessageBox.warning(self, "Rollback Step", "Could not locate current step.")
                return

            # set current to planned
            cpi, csi, cstep = flat[cur_idx]
            cstep["status"] = "planned"

            # previous step becomes in_progress (if any), else keep first as next
            if cur_idx - 1 >= 0:
                ppi, psi, pstep = flat[cur_idx - 1]
                # demote any other in_progress to done (if needed)
                for _pi, _si, st in flat:
                    if st is not pstep and str(st.get("status", "")) == "in_progress":
                        st["status"] = "done"
                if str(pstep.get("status", "")) == "done":
                    pstep["status"] = "in_progress"
                elif str(pstep.get("status", "")) in ("planned", "next"):
                    pstep["status"] = "in_progress"
            else:
                # we rolled back from the first; set it to next
                cstep["status"] = "next"

            self._write_plan(data)
            self.refresh_plan()
        except Exception as e:
            QMessageBox.critical(self, "Rollback Step", f"Error: {e}")
    
    def set_plan_path(self, plan_path: str):
        """
        Updates the plan file path and reloads the tree.
        """
        self.plan_path = plan_path
        self.refresh_plan()

