# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor project-seed smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_project_seed.py
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
    doc = App.newDocument("CRRegionProjectSeed")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"
        ensure_project_tree(prj, include_references=False)

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.Label = "Seed Assembly"

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        typ.Label = "Seed Typical"
        _assign_component_rows(
            typ,
            [
                {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
                {"Id": "GUT-L", "Type": "gutter", "Side": "left", "Width": 0.80, "CrossSlopePct": 6.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 20, "Enabled": True},
                {"Id": "DITCH-L", "Type": "ditch", "Side": "left", "Width": 2.40, "CrossSlopePct": 2.0, "Height": 1.0, "ExtraWidth": 0.80, "BackSlopePct": -10.0, "Offset": 0.0, "Order": 30, "Enabled": True},
                {"Id": "BERM-L", "Type": "berm", "Side": "left", "Width": 1.20, "CrossSlopePct": 0.0, "Height": 0.0, "ExtraWidth": 0.80, "BackSlopePct": 6.0, "Offset": 0.0, "Order": 40, "Enabled": True},
                {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
                {"Id": "CURB-R", "Type": "curb", "Side": "right", "Width": 0.18, "CrossSlopePct": 0.0, "Height": 0.15, "ExtraWidth": 0.06, "BackSlopePct": 1.0, "Offset": 0.0, "Order": 20, "Enabled": True},
                {"Id": "WALK-R", "Type": "sidewalk", "Side": "right", "Width": 2.00, "CrossSlopePct": 1.5, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 30, "Enabled": True},
            ],
        )

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["CULV_A"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [20.0]
        ss.EndStations = [30.0]
        ss.CenterStations = [25.0]
        ss.Sides = ["both"]
        ss.Widths = [6.0]
        ss.Heights = [3.0]
        ss.CorridorModes = ["skip_zone"]
        ss.TemplateNames = ["box_culvert"]

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
        rows = panel._read_rows()
        _assert(len(rows) == 5, f"Expected 5 auto-seeded rows, got {len(rows)}")

        base = _find_row(rows, "BASE_01")
        left_ditch = _find_row(rows, "TYP_LEFT_DITCH")
        right_urban = _find_row(rows, "TYP_RIGHT_URBAN")
        struct_overlay = _find_row(rows, "AUTO_01_CULV_A")
        standard_hint = _find_row(rows, "STD_KDS_060")

        _assert(base is not None, "Missing BASE_01 project seed row")
        _assert(left_ditch is not None, "Missing left ditch roadside seed row")
        _assert(right_urban is not None, "Missing right urban roadside seed row")
        _assert(struct_overlay is not None, "Missing structure-derived overlay seed row")
        _assert(standard_hint is not None, "Missing standards-driven hint row")

        _assert(str(base.get("Layer", "") or "") == "base", "BASE_01 should be base layer")
        _assert(abs(float(base.get("StartStation", 0.0) or 0.0) - 10.0) < 1e-6, "BASE_01 start should pad from structure span")
        _assert(abs(float(base.get("EndStation", 0.0) or 0.0) - 40.0) < 1e-6, "BASE_01 end should pad from structure span")
        _assert(str(base.get("TemplateName", "") or "") == "Seed Typical", "BASE_01 should inherit typical section label")
        _assert(str(base.get("AssemblyName", "") or "") == "Seed Assembly", "BASE_01 should inherit assembly label")
        _assert("roadside=ditch_edge:left,urban_edge:right" in str(base.get("Notes", "") or ""), "BASE_01 notes missing roadside summary")

        _assert(str(left_ditch.get("RegionType", "") or "") == "ditch_override", "Left roadside row should map to ditch_override")
        _assert(str(left_ditch.get("SidePolicy", "") or "") == "left:berm", "Left roadside row should seed left berm policy")
        _assert(str(left_ditch.get("Enabled", "") or "").lower() == "false", "Left roadside row should start disabled")
        _assert(str(left_ditch.get("HintSource", "") or "").lower() == "typical", "Left roadside row should record hint source")
        _assert(str(left_ditch.get("HintStatus", "") or "").lower() == "pending", "Left roadside row should start as pending hint")
        _assert(float(left_ditch.get("HintConfidence", 0.0) or 0.0) >= 0.9, "Left roadside row should carry high confidence")

        _assert(str(right_urban.get("RegionType", "") or "") == "retaining_wall_zone", "Right roadside row should map to retaining_wall_zone")
        _assert(str(right_urban.get("DaylightPolicy", "") or "") == "right:off", "Right roadside row should suppress right daylight")
        _assert(str(right_urban.get("Enabled", "") or "").lower() == "false", "Right roadside row should start disabled")
        _assert(str(right_urban.get("HintReason", "") or "") != "", "Right roadside row should persist hint reason")
        _assert(float(right_urban.get("HintConfidence", 0.0) or 0.0) >= 0.9, "Right urban row should carry high confidence")

        _assert(str(struct_overlay.get("Layer", "") or "") == "overlay", "Structure seed row should be overlay")
        _assert(str(struct_overlay.get("RuleSet", "") or "") == "structure:culvert:CULV_A", "Structure seed row ruleset mismatch")
        _assert(str(struct_overlay.get("CorridorPolicy", "") or "") == "skip_zone", "Structure seed row corridor policy mismatch")
        _assert(str(struct_overlay.get("TemplateName", "") or "") == "box_culvert", "Structure seed row should inherit template name")
        _assert(str(struct_overlay.get("Enabled", "") or "").lower() == "false", "Structure seed row should start disabled")
        _assert(str(struct_overlay.get("HintSource", "") or "").lower() == "structure", "Structure seed row should record structure hint source")
        _assert(float(struct_overlay.get("HintConfidence", 0.0) or 0.0) >= 0.9, "Structure seed row should carry high confidence for explicit corridor mode")

        _assert(str(standard_hint.get("HintSource", "") or "").lower() == "standard", "Standard seed row should record standard hint source")
        _assert(str(standard_hint.get("RuleSet", "") or "") == "standard:KDS:60", "Standard seed row ruleset mismatch")
        _assert("transition lengths" in str(standard_hint.get("HintReason", "") or "").lower(), "Standard seed row should explain standards-driven transition review")

        helper_rows = panel._make_project_seed_rows()
        _assert(len(helper_rows) == 5, "Project helper should return the same seeded row count")
        _assert(any(str(row.get("Id", "") or "") == "TYP_LEFT_DITCH" for row in helper_rows), "Helper rows missing left ditch seed")
        _assert(any(str(row.get("Id", "") or "") == "TYP_RIGHT_URBAN" for row in helper_rows), "Helper rows missing right urban seed")

        panel._populate_table(
            [
                {"Id": "BASE_KEEP", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 120.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "manual_base", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Manual base"},
                {"Id": "OVR_KEEP", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 15.0, "EndStation": 18.0, "Priority": 5, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Manual override"},
            ]
        )
        panel._seed_from_project()
        merged_rows = panel._read_rows()
        _assert(_find_row(merged_rows, "BASE_KEEP") is not None, "Existing base row should be preserved when seeding hints")
        _assert(_find_row(merged_rows, "OVR_KEEP") is not None, "Existing override row should be preserved when seeding hints")
        _assert(_find_row(merged_rows, "BASE_01") is None, "Project seeding should not inject a new base when one already exists")
        _assert(_find_row(merged_rows, "TYP_LEFT_DITCH") is not None, "Project seeding should append left ditch hint")
        _assert(_find_row(merged_rows, "TYP_RIGHT_URBAN") is not None, "Project seeding should append right urban hint")
        _assert(_find_row(merged_rows, "AUTO_01_CULV_A") is not None, "Project seeding should append structure hint")
        _assert(_find_row(merged_rows, "STD_KDS_060") is not None, "Project seeding should append standards-driven hint")
        _assert(len(merged_rows) == 6, f"Expected 6 merged rows after seeding hints, got {len(merged_rows)}")

        print("[PASS] Region editor project-seed smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
