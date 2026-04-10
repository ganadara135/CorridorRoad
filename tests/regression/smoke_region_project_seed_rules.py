# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor project-seed rule expansion smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_project_seed_rules.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _assign_component_rows(obj, rows):
    obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
    obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
    obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
    obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
    obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
    obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
    obj.ComponentExtraWidths = [float(r.get("ExtraWidth", 0.0) or 0.0) for r in rows]
    obj.ComponentBackSlopes = [float(r.get("BackSlopePct", 0.0) or 0.0) for r in rows]
    obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
    obj.ComponentOrders = [int(r.get("Order", idx + 1) or (idx + 1)) for idx, r in enumerate(rows)]
    obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]


def _find_row(rows, row_id: str):
    target = str(row_id or "").strip()
    for row in list(rows or []):
        if str(row.get("Id", "") or "").strip() == target:
            return row
    return None


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionProjectSeedRules")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        ensure_project_tree(prj, include_references=False)

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.Label = "Rule Seed Assembly"

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        typ.Label = "Rule Seed Typical"
        _assign_component_rows(
            typ,
            [
                {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
                {"Id": "SHL-L", "Type": "shoulder", "Side": "left", "Width": 1.50, "CrossSlopePct": 4.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 20, "Enabled": True},
                {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
                {"Id": "SHL-R", "Type": "shoulder", "Side": "right", "Width": 1.50, "CrossSlopePct": 4.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 20, "Enabled": True},
            ],
        )
        typ.PracticalSectionMode = "rural"

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["WALL_A", "BRIDGE_A"]
        ss.StructureTypes = ["retaining_wall", "bridge_zone"]
        ss.StartStations = [30.0, 80.0]
        ss.EndStations = [40.0, 90.0]
        ss.CenterStations = [35.0, 85.0]
        ss.Sides = ["left", "both"]
        ss.Widths = [4.0, 12.0]
        ss.Heights = [3.0, 5.0]
        ss.CorridorModes = ["", ""]
        ss.TemplateNames = ["retaining_wall", ""]

        link_project(
            prj,
            links={
                "AssemblyTemplate": asm,
                "TypicalSectionTemplate": typ,
                "StructureSet": ss,
            },
            adopt_extra=[asm, typ, ss],
        )

        doc.recompute()

        panel = RegionEditorTaskPanel()
        rows = panel._make_project_seed_rows()

        left_shoulder = _find_row(rows, "TYP_LEFT_SHOULDER")
        right_shoulder = _find_row(rows, "TYP_RIGHT_SHOULDER")
        mode_hint = _find_row(rows, "MODE_RURAL")
        standard_hint = _find_row(rows, "STD_KDS_060")
        wall_hint = _find_row(rows, "AUTO_01_WALL_A")
        bridge_hint = _find_row(rows, "AUTO_02_BRIDGE_A")

        _assert(left_shoulder is not None, "Missing left shoulder hint")
        _assert(right_shoulder is not None, "Missing right shoulder hint")
        _assert(mode_hint is not None, "Missing practical mode hint")
        _assert(standard_hint is not None, "Missing design standard hint")
        _assert(wall_hint is not None, "Missing retaining wall structure hint")
        _assert(bridge_hint is not None, "Missing bridge structure hint")

        _assert(str(left_shoulder.get("RegionType", "") or "") == "earthwork_zone", "Shoulder hints should map to earthwork_zone")
        _assert(str(left_shoulder.get("RuleSet", "") or "") == "typical:shoulder_edge:left", "Left shoulder rule set mismatch")
        _assert(float(left_shoulder.get("HintConfidence", 0.0) or 0.0) >= 0.75, "Left shoulder hint should have medium confidence or better")
        _assert(str(right_shoulder.get("RuleSet", "") or "") == "typical:shoulder_edge:right", "Right shoulder rule set mismatch")

        _assert(str(mode_hint.get("RuleSet", "") or "") == "project:practical_mode:rural", "Practical mode rule set mismatch")
        _assert(float(mode_hint.get("HintConfidence", 0.0) or 0.0) >= 0.8, "Practical mode hint should carry elevated confidence")

        _assert(str(standard_hint.get("RuleSet", "") or "") == "standard:KDS:60", "Design standard rule set mismatch")
        _assert(str(standard_hint.get("HintSource", "") or "").lower() == "standard", "Design standard hint source mismatch")
        _assert("transition lengths" in str(standard_hint.get("HintReason", "") or "").lower(), "Design standard hint should explain the review target")

        _assert(str(wall_hint.get("RuleSet", "") or "") == "structure:retaining_wall:WALL_A", "Retaining wall rule set mismatch")
        _assert(str(wall_hint.get("DaylightPolicy", "") or "") == "left:off", "Retaining wall should seed daylight suppression on its side")
        _assert(float(wall_hint.get("HintConfidence", 0.0) or 0.0) >= 0.9, "Retaining wall hint should carry high confidence")

        _assert(str(bridge_hint.get("RuleSet", "") or "") == "structure:bridge_zone:BRIDGE_A", "Bridge zone rule set mismatch")
        _assert(str(bridge_hint.get("CorridorPolicy", "") or "") == "split_only", "Bridge zone should default to split_only corridor hint")
        _assert(float(bridge_hint.get("HintConfidence", 0.0) or 0.0) >= 0.85, "Bridge zone hint should carry high confidence")

        print("[PASS] Region editor project-seed rule expansion smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
