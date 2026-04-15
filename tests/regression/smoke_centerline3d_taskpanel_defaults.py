# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
3D centerline task panel default-source selection smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_centerline3d_taskpanel_defaults.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, assign_project_region_plan, ensure_project_tree
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_stationing import Stationing
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment
from freecad.Corridor_Road.ui.task_centerline3d import Centerline3DTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    doc = App.newDocument("CRCenterlinePanelDefaults")

    prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(prj)
    ensure_project_tree(prj, include_references=False)

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    st = doc.addObject("Part::FeaturePython", "Stationing")
    Stationing(st)
    st.Alignment = aln

    va = doc.addObject("Part::FeaturePython", "VerticalAlignment")
    VerticalAlignment(va)
    va.PVIStations = [0.0, 100.0]
    va.PVIElevations = [0.0, 5.0]
    va.CurveLengths = [0.0, 0.0]

    pb = doc.addObject("Part::FeaturePython", "ProfileBundle")
    ProfileBundle(pb)
    pb.Stationing = st
    pb.VerticalAlignment = va

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    assign_project_region_plan(prj, reg)

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    if hasattr(prj, "StructureSet"):
        prj.StructureSet = ss

    doc.recompute()

    panel = Centerline3DTaskPanel()

    _assert(panel._current_obj(panel.cmb_target) is None, "New target should remain selected by default")
    _assert(panel._current_obj(panel.cmb_alignment) == aln, "Alignment should default to the available alignment")
    _assert(panel._current_obj(panel.cmb_stationing) == st, "Stationing should default to the matching object")
    _assert(panel._current_obj(panel.cmb_vertical) == va, "Vertical alignment should default to the matching object")
    _assert(panel._current_obj(panel.cmb_profile) == pb, "Profile bundle should default to the matching object")
    _assert(panel._current_obj(panel.cmb_region) == reg, "Region plan should default to the available/project object")
    _assert(panel._current_obj(panel.cmb_structure) == ss, "Structure set should default to the available/project object")
    _assert(panel.chk_use_stationing.isChecked(), "Use Stationing should default on when stationing exists")

    try:
        panel.form.close()
    except Exception:
        pass
    App.closeDocument(doc.Name)
    print("[PASS] 3D centerline task panel default-source smoke test completed.")


if __name__ == "__main__":
    run()
