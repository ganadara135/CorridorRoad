# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Sample v1 alignment command smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_sample_alignment_command_unit_policy.py
"""

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_ALIGNMENTS,
    ensure_project_properties,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import find_v1_alignment, to_alignment_model

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

        aln = find_v1_alignment(doc)
        _assert(aln is not None, "Sample alignment command should create a V1Alignment object")
        _assert(not hasattr(prj, "LengthScale"), "Sample alignment command should not create LengthScale on a new project")

        model = to_alignment_model(aln)
        _assert(model is not None, "Sample alignment should convert to an AlignmentModel")
        _assert(len(model.geometry_sequence) == 3, "Sample alignment should create three v1 geometry elements")
        _assert(abs(model.geometry_sequence[-1].station_end - 180.0) < 1.0e-6, "Sample alignment station end should be 180 m")
        tree = ensure_project_tree(prj, include_references=False)
        names = {str(getattr(obj, "Name", "") or "") for obj in list(getattr(tree[V1_TREE_ALIGNMENTS], "Group", []) or [])}
        _assert(aln.Name in names, "Sample alignment should be routed to v1 Alignments folder")

        print("[PASS] Sample v1 alignment command smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
