# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor task-panel alias boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_taskpanel_alias_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import PREFERRED_TASK_PANEL_CLASS


LEGACY_TASK_MODULE = "freecad.Corridor_Road.ui.task_corridor_loft"
LEGACY_TASK_PANEL_CLASS = "CorridorLoftTaskPanel"


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")
    found_legacy_task_refs = []

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if LEGACY_TASK_MODULE in text or LEGACY_TASK_PANEL_CLASS in text:
                found_legacy_task_refs.append(path)

    _assert(not found_legacy_task_refs, f"Legacy task-panel aliases should be fully removed from runtime code: {sorted(found_legacy_task_refs)}")

    canonical_task_path = os.path.join(freecad_root, "ui", "task_corridor.py")
    canonical_text = _read_text(canonical_task_path)
    _assert(f"class {PREFERRED_TASK_PANEL_CLASS}" in canonical_text, "Canonical task-panel module should define CorridorTaskPanel")

    legacy_task_path = os.path.join(freecad_root, "ui", "task_corridor_loft.py")
    _assert(not os.path.exists(legacy_task_path), "Legacy task-panel wrapper should be removed")

    print("[PASS] Corridor task-panel alias boundary smoke test completed.")


if __name__ == "__main__":
    run()
