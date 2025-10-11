#!/usr/bin/env python3
# Tracker tweak: bold in_progress
import sys, re, io, os, pathlib
p = pathlib.Path("pal/ui/desktop/pal_tracker.py")
if not p.exists():
    sys.exit(0)
s = p.read_text(encoding="utf-8")
if "def set_item_color" in s and "setForeground" in s and "font-weight" not in s:
    # inject a style change by setting bold via QFont on in_progress items
    s = s.replace(
        "def set_item_color(self,it,status): it.setForeground(0, self.color_for_status(status))",
        "def set_item_color(self,it,status):\n        it.setForeground(0, self.color_for_status(status))\n        try:\n            from PyQt6.QtGui import QFont\n            f = it.font(0)\n            f.setBold(True if status=='in_progress' else False)\n            it.setFont(0, f)\n        except Exception:\n            pass"
    )
    p.write_text(s, encoding="utf-8")
