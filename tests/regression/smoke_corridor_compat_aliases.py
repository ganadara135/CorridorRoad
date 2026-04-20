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
    LEGACY_COMMAND_MODULE,
    LEGACY_TASK_PANEL_CLASS,
    LEGACY_TASK_MODULE,
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
    task_legacy = importlib.import_module(LEGACY_TASK_MODULE)
    cmd_canonical = importlib.import_module(PREFERRED_COMMAND_MODULE)
    cmd_legacy = importlib.import_module(LEGACY_COMMAND_MODULE)

    _assert(legacy_a is canonical, "Legacy Corridor_Road module alias should resolve to canonical module")
    _assert(legacy_b is canonical, "Legacy objects module alias should resolve to canonical module")
    _assert(getattr(task_canonical, PREFERRED_TASK_PANEL_CLASS) is task_canonical.CorridorTaskPanel, "Canonical task-panel module should expose the preferred CorridorTaskPanel class")
    _assert(task_legacy.CorridorTaskPanel is task_canonical.CorridorTaskPanel, "Legacy task-panel module should expose the canonical CorridorTaskPanel")
    _assert(getattr(task_legacy, LEGACY_TASK_PANEL_CLASS) is task_canonical.CorridorTaskPanel, "Legacy task-panel alias should resolve to the canonical CorridorTaskPanel")
    _assert(cmd_legacy._CMD is cmd_canonical._CMD, "Legacy command module should reuse the canonical corridor command instance")
    _assert(cmd_legacy.CmdGenerateCorridor is cmd_canonical.CmdGenerateCorridor, "Legacy command module should re-export the canonical command class")
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
        _assert(hasattr(prj, CORRIDOR_PROJECT_PROPERTY), "Project should retain hidden CorridorLoft link property for compatibility")

        cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)

        assigned = assign_project_corridor(prj, cor)
        _assert(assigned is cor, "assign_project_corridor should return the corridor object")
        _assert(getattr(prj, CORRIDOR_PROJECT_PROPERTY, None) is cor, "Compatibility hidden property should store the assigned corridor")
        _assert(resolve_project_corridor(prj) is cor, "resolve_project_corridor should return the assigned corridor")
        _assert(ensure_corridor_object(cor) is cor, "ensure_corridor_object should accept CorridorLoft proxy objects")

        seg = doc.addObject("Part::Feature", CORRIDOR_SEGMENT_NAME)
        if not hasattr(seg, CORRIDOR_CHILD_LINK_PROPERTY):
            seg.addProperty("App::PropertyLink", CORRIDOR_CHILD_LINK_PROPERTY, "Smoke", "Corridor link")
        setattr(seg, CORRIDOR_CHILD_LINK_PROPERTY, cor)
        _assert(getattr(seg, CORRIDOR_CHILD_LINK_PROPERTY, None) is cor, "Compatibility child-link property should attach generated corridor children to the corridor")

        setattr(prj, CORRIDOR_PROJECT_PROPERTY, None)
        resolved_from_doc = resolve_project_corridor(doc)
        _assert(resolved_from_doc is cor, "resolve_project_corridor(doc) should rediscover corridor objects from the document")
        _assert(getattr(prj, CORRIDOR_PROJECT_PROPERTY, None) is cor, "resolve_project_corridor should resync the compatibility hidden property")

        print("[PASS] Corridor compatibility-alias smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
