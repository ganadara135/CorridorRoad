# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor compatibility-alias smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_compat_aliases.py
"""

import importlib
import sys

import FreeCAD as App

from freecad.Corridor_Road import install_virtual_path_mappings
from freecad.Corridor_Road.corridor_compat import (
    CORRIDOR_CHILD_LINK_PROPERTY,
    CORRIDOR_PROJECT_PROPERTY,
    CORRIDOR_SEGMENT_NAME,
    PREFERRED_COMMAND_MODULE,
    PREFERRED_TASK_PANEL_CLASS,
    PREFERRED_TASK_MODULE,
)
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_project import (
    ensure_corridor_object,
    ensure_project_properties,
    assign_project_corridor,
    resolve_project_corridor,
)


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    install_virtual_path_mappings(eager=True)

    canonical = importlib.import_module("freecad.Corridor_Road.objects.obj_corridor_loft")
    legacy_a = importlib.import_module("Corridor_Road.objects.obj_corridor_loft")
    legacy_b = importlib.import_module("objects.obj_corridor_loft")
    task_canonical = importlib.import_module(PREFERRED_TASK_MODULE)
    cmd_canonical = importlib.import_module(PREFERRED_COMMAND_MODULE)

    _assert(legacy_a is canonical, "Legacy Corridor_Road module alias should resolve to canonical module")
    _assert(legacy_b is canonical, "Legacy objects module alias should resolve to canonical module")
    _assert(getattr(task_canonical, PREFERRED_TASK_PANEL_CLASS) is task_canonical.CorridorTaskPanel, "Canonical task-panel module should expose the preferred CorridorTaskPanel class")
    _assert(hasattr(cmd_canonical, "CmdGenerateCorridor"), "Canonical command module should expose the corridor command class")
    _assert(hasattr(cmd_canonical, "_CMD"), "Canonical command module should expose the shared corridor command instance")
    _assert(
        str(getattr(canonical.CorridorLoft, "__module__", "") or "") == "freecad.Corridor_Road.objects.obj_corridor_loft",
        "CorridorLoft class module path should stay canonical after alias install",
    )
    _assert(sys.modules.get("Corridor_Road.objects.obj_corridor_loft") is canonical, "Legacy module cache should point at canonical corridor module")
    _assert(sys.modules.get("objects.obj_corridor_loft") is canonical, "Short legacy module cache should point at canonical corridor module")

    doc = App.newDocument("CRCorridorCompatAliases")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        _assert(hasattr(prj, CORRIDOR_PROJECT_PROPERTY), "Project should expose the canonical hidden corridor link property")
        _assert(not hasattr(prj, "CorridorLoft"), "Project should no longer create the legacy hidden CorridorLoft property")

        cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)

        assigned = assign_project_corridor(prj, cor)
        _assert(assigned is cor, "assign_project_corridor should return the corridor object")
        _assert(getattr(prj, CORRIDOR_PROJECT_PROPERTY, None) is cor, "Canonical hidden project property should store the assigned corridor")
        _assert(resolve_project_corridor(prj) is cor, "resolve_project_corridor should return the assigned corridor")
        _assert(ensure_corridor_object(cor) is cor, "ensure_corridor_object should accept CorridorLoft proxy objects")

        seg = doc.addObject("Part::Feature", CORRIDOR_SEGMENT_NAME)
        if not hasattr(seg, CORRIDOR_CHILD_LINK_PROPERTY):
            seg.addProperty("App::PropertyLink", CORRIDOR_CHILD_LINK_PROPERTY, "Smoke", "Corridor link")
        setattr(seg, CORRIDOR_CHILD_LINK_PROPERTY, cor)
        _assert(not hasattr(seg, "ParentCorridorLoft"), "Generated corridor child should not create the legacy ParentCorridorLoft property")
        _assert(getattr(seg, CORRIDOR_CHILD_LINK_PROPERTY, None) is cor, "Canonical child-link property should attach generated corridor children to the corridor")

        setattr(prj, CORRIDOR_PROJECT_PROPERTY, None)
        resolved_from_doc = resolve_project_corridor(doc)
        _assert(resolved_from_doc is cor, "resolve_project_corridor(doc) should rediscover corridor objects from the document")
        _assert(getattr(prj, CORRIDOR_PROJECT_PROPERTY, None) is cor, "resolve_project_corridor should resync the canonical hidden project property")

        print("[PASS] Corridor compatibility-alias smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
