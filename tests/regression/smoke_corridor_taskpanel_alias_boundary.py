# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor task-panel alias boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_taskpanel_alias_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import (
    LEGACY_TASK_MODULE,
    LEGACY_TASK_PANEL_CLASS,
    PREFERRED_TASK_MODULE,
    PREFERRED_TASK_PANEL_CLASS,
)


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")

    allowed_legacy_task_refs = {
        os.path.normpath(os.path.join(freecad_root, "corridor_compat.py")),
        os.path.normpath(os.path.join(freecad_root, "ui", "task_corridor.py")),
        os.path.normpath(os.path.join(freecad_root, "ui", "task_corridor_loft.py")),
    }
    found_legacy_task_refs = set()

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if LEGACY_TASK_MODULE in text or LEGACY_TASK_PANEL_CLASS in text:
                found_legacy_task_refs.add(path)

    unexpected = sorted(path for path in found_legacy_task_refs if path not in allowed_legacy_task_refs)
    _assert(not unexpected, f"Legacy task-panel aliases should stay isolated to compatibility boundary files only: {unexpected}")

    canonical_task_path = os.path.join(freecad_root, "ui", "task_corridor.py")
    canonical_text = _read_text(canonical_task_path)
    _assert(f"class {PREFERRED_TASK_PANEL_CLASS}" in canonical_text, "Canonical task-panel module should define CorridorTaskPanel")
    _assert(f"{LEGACY_TASK_PANEL_CLASS} = {PREFERRED_TASK_PANEL_CLASS}" in canonical_text, "Canonical task-panel module should retain the legacy class alias until retirement")

    legacy_task_path = os.path.join(freecad_root, "ui", "task_corridor_loft.py")
    legacy_text = _read_text(legacy_task_path)
    _assert("from freecad.Corridor_Road.ui.task_corridor import CorridorLoftTaskPanel, CorridorTaskPanel" in legacy_text, "Legacy wrapper should re-export the canonical task-panel classes")

    print("[PASS] Corridor task-panel alias boundary smoke test completed.")


if __name__ == "__main__":
    run()
