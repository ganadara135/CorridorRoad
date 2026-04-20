# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor structure diagnostics smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_corridor_diagnostics.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRStructureCorridorDiag")

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["CULV_CENTER", "BRIDGE_SWAP", "WALL_SPLIT"]
    ss.StructureTypes = ["culvert", "bridge_zone", "retaining_wall"]
    ss.StartStations = [0.0, 120.0, 160.0]
    ss.EndStations = [0.0, 110.0, 160.0]
    ss.CenterStations = [100.0, 130.0, 200.0]
    ss.Sides = ["both", "both", "left"]
    ss.Widths = [6.0, 14.0, 3.0]
    ss.Heights = [3.0, 4.0, 5.0]
    ss.CorridorModes = ["skip_zone", "skip_zone", "split_only"]
    ss.CorridorMargins = [0.0, 5.0, 0.0]

    rows = StructureSet.corridor_zone_records(ss, fallback_mode="split_only")
    _assert(len(rows) == 3, f"Expected 3 corridor rows, got {len(rows)}")

    by_id = {str(r.get("Id", "")): r for r in rows}

    culv = by_id["CULV_CENTER"]
    _assert(str(culv.get("ResolvedStationSource", "")) == "center_fallback", "Center fallback was not resolved")
    _assert(abs(float(culv.get("ResolvedStartStation", 0.0)) - 100.0) < 1e-9, "Center fallback start station mismatch")
    _assert(abs(float(culv.get("ResolvedEndStation", 0.0)) - 100.0) < 1e-9, "Center fallback end station mismatch")
    culv_warn = " | ".join(list(culv.get("ResolvedCorridorWarnings", []) or []))
    _assert("used CenterStation" in culv_warn, "Expected center fallback warning for culvert record")
    _assert("zero-length skip_zone" in culv_warn, "Expected zero-length skip_zone warning for culvert record")

    bridge = by_id["BRIDGE_SWAP"]
    _assert(abs(float(bridge.get("ResolvedStartStation", 0.0)) - 110.0) < 1e-9, "Swapped bridge start station mismatch")
    _assert(abs(float(bridge.get("ResolvedEndStation", 0.0)) - 120.0) < 1e-9, "Swapped bridge end station mismatch")
    bridge_warn = " | ".join(list(bridge.get("ResolvedCorridorWarnings", []) or []))
    _assert("swapped StartStation/EndStation order" in bridge_warn, "Expected swapped-station warning for bridge record")

    wall = by_id["WALL_SPLIT"]
    _assert(str(wall.get("ResolvedCorridorMode", "")) == "split_only", "Retaining wall should stay split_only")

    detail_rows, warning_rows, mode_summary, spans = Corridor._describe_structure_corridor_records(rows)
    _assert(len(detail_rows) == 3, f"Expected 3 detail rows, got {len(detail_rows)}")
    _assert("skip_zone=2" in str(mode_summary), f"Missing skip_zone summary: {mode_summary}")
    _assert("split_only=1" in str(mode_summary), f"Missing split_only summary: {mode_summary}")
    _assert(len(spans) == 2, f"Expected 2 non-split spans, got {len(spans)}")
    _assert(any("CULV_CENTER" in row for row in warning_rows), "Expected culvert diagnostics in warning rows")
    _assert(any("BRIDGE_SWAP" in row for row in warning_rows), "Expected bridge diagnostics in warning rows")

    issues = StructureSet.validate(ss)
    joined_issues = "\n".join(list(issues or []))
    _assert("CULV_CENTER: corridor mode 'skip_zone' is point-like" in joined_issues, "Expected point-like skip_zone validation warning")

    ss.GeometryModes = ["external_shape", "", ""]
    ss.ShapeSourcePaths = ["D:/missing/sample.step", "", ""]
    issues_ext = StructureSet.validate(ss)
    joined_ext = "\n".join(list(issues_ext or []))
    _assert("external_shape may drive an indirect bbox-based earthwork proxy" in joined_ext, "Expected external_shape proxy warning")
    _assert("external shape file not found" not in joined_ext, "StructureSet.validate should not perform filesystem existence checks")

    doc.recompute()
    _assert("externalShapeDisplayOnly=1" in str(getattr(ss, "Status", "") or ""), "Expected externalShapeDisplayOnly summary in status")

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    _assert(hasattr(cor, "ResolvedStructureCorridorRanges"), "Corridor missing ResolvedStructureCorridorRanges")
    _assert(hasattr(cor, "ResolvedStructureCorridorWarnings"), "Corridor missing ResolvedStructureCorridorWarnings")
    _assert(hasattr(cor, "ResolvedStructureCorridorModeSummary"), "Corridor missing ResolvedStructureCorridorModeSummary")

    App.closeDocument(doc.Name)


run()
