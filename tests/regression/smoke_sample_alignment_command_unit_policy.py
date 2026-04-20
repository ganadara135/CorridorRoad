# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Sample alignment command unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_sample_alignment_command_unit_policy.py
"""

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.doc_query import find_first
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties

if not hasattr(Gui, "addCommand"):
    Gui.addCommand = lambda *args, **kwargs: None

import freecad.Corridor_Road.commands.cmd_create_alignment as _cmd_create_alignment

_cmd_create_alignment.ViewProviderHorizontalAlignment = lambda _vobj: None
CmdCreateAlignment = _cmd_create_alignment.CmdCreateAlignment


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRSampleAlignmentCommandUnits")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)

        CmdCreateAlignment().Activated()
        doc.recompute()

        aln = find_first(doc, proxy_type="HorizontalAlignment", name_prefixes=("HorizontalAlignment",))
        _assert(aln is not None, "Sample alignment command should create a HorizontalAlignment")
        _assert(not hasattr(prj, "LengthScale"), "Sample alignment command should not create LengthScale on a new project")

        pts = list(getattr(aln, "IPPoints", []) or [])
        _assert(len(pts) == 4, "Sample alignment command should create four IP points")
        _assert(abs(float(pts[1].x) - (-12.0)) < 1.0e-6, "Sample alignment IP points should be created in meter-native model space")
        _assert(abs(float(pts[2].y) - 24.0) < 1.0e-6, "Sample alignment Y offset should be created in meter-native model space")
        _assert(abs(float(getattr(aln, "CurveRadii", [0.0, 0.0])[1]) - 18.0) < 1.0e-6, "Sample alignment radius should remain meter-native")
        _assert(abs(float(getattr(aln, "TransitionLengths", [0.0, 0.0])[1]) - 8.0) < 1.0e-6, "Sample alignment transition should remain meter-native")

        print("[PASS] Sample alignment command unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
