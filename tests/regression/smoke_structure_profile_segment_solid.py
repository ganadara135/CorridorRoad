# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Structure profile-segment solid smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_profile_segment_solid.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_structure_set import (
    StructureSet,
    _build_profile_pair_solid,
    _section_wire_for_profile_record,
    _usable_solid,
)


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def run():
    doc = App.newDocument("CRStructureProfileSegmentSolid")
    try:
        rec0 = {"Width": 4.0, "Height": 2.0}
        rec1 = {"Width": 6.0, "Height": 3.0}
        wire0 = _section_wire_for_profile_record(
            App.Vector(0.0, 0.0, 0.0),
            App.Vector(0.0, 1.0, 0.0),
            App.Vector(0.0, 0.0, 1.0),
            rec0,
        )
        wire1 = _section_wire_for_profile_record(
            App.Vector(10.0, 0.0, 0.0),
            App.Vector(0.0, 1.0, 0.0),
            App.Vector(0.0, 0.0, 1.0),
            rec1,
        )
        solid = _build_profile_pair_solid(wire0, wire1)
        _assert(_usable_solid(solid), "Profile-pair solid builder should return a usable solid")
        _assert(float(getattr(solid, "Volume", 0.0) or 0.0) > 0.0, "Profile-pair solid should have positive volume")

        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["CULV_VAR"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [20.0]
        ss.EndStations = [40.0]
        ss.CenterStations = [30.0]
        ss.Sides = ["both"]
        ss.Widths = [4.0]
        ss.Heights = [2.0]

        ss.ProfileStructureIds = ["CULV_VAR", "CULV_VAR", "CULV_VAR"]
        ss.ProfileStations = [20.0, 30.0, 40.0]
        ss.ProfileWidths = [4.0, 6.0, 5.0]
        ss.ProfileHeights = [2.0, 3.0, 2.5]
        ss.ProfileBottomElevations = [0.0, 0.2, 0.1]

        doc.recompute()

        _assert(_shape_ok(ss), "StructureSet should generate profile-driven display geometry")
        _assert(int(getattr(ss, "StructureProfileCount", 0) or 0) == 3, "StructureSet should report normalized profile rows")
        _assert(len(list(getattr(getattr(ss, "Shape", None), "Solids", []) or [])) > 0, "StructureSet should expose usable solids")
        _assert("profilePoints=3" in str(getattr(ss, "Status", "") or ""), "StructureSet status should report profile point count")

        print("[PASS] Structure profile-segment solid smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
