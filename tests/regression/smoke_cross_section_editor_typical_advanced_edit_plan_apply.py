# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-5 typical advanced-parameter edit-plan apply smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_typical_advanced_edit_plan_apply.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_cross_section_editor import CrossSectionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _set_station(panel, station):
    for idx, row in enumerate(list(getattr(panel, "_station_rows", []) or [])):
        if abs(float(row.get("station", 0.0) or 0.0) - float(station)) <= 1.0e-6:
            panel.cmb_station.setCurrentIndex(idx)
            panel._render_current_payload()
            return
    raise Exception(f"Station {station} not found")


def _select_target(panel, target_id, side):
    target_id = str(target_id or "").strip().upper()
    side = str(side or "").strip().lower()
    for idx in range(panel.cmb_component_target.count()):
        seg = dict(panel.cmb_component_target.itemData(idx) or {})
        if str(seg.get("id", "") or "").strip().upper() != target_id:
            continue
        if str(seg.get("side", "") or "").strip().lower() != side:
            continue
        panel.cmb_component_target.setCurrentIndex(idx)
        panel._refresh_editor_target()
        return dict(panel._current_editor_segment() or {})
    raise Exception(f"Target {target_id}/{side} not found")


def _find_component(rows, target_id, side):
    target_id = str(target_id or "").strip().upper()
    side = str(side or "").strip().lower()
    for row in list(rows or []):
        if str(row.get("id", "") or "").strip().upper() != target_id:
            continue
        if str(row.get("side", "") or "").strip().lower() != side:
            continue
        return dict(row or {})
    return {}


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorTypicalAdvancedEditPlanApply")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False

    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)
    typ.ComponentIds = ["LANE-L", "LANE-R", "BERM-R"]
    typ.ComponentTypes = ["lane", "lane", "berm"]
    typ.ComponentShapes = ["", "", ""]
    typ.ComponentSides = ["left", "right", "right"]
    typ.ComponentWidths = [3.5, 3.5, 1.5]
    typ.ComponentCrossSlopes = [2.0, 2.0, 0.0]
    typ.ComponentHeights = [0.0, 0.0, 0.0]
    typ.ComponentExtraWidths = [0.0, 0.0, 0.8]
    typ.ComponentBackSlopes = [0.0, 0.0, 6.0]
    typ.ComponentOffsets = [0.0, 0.0, 0.0]
    typ.ComponentOrders = [10, 10, 20]
    typ.ComponentEnabled = [1, 1, 1]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.TypicalSectionTemplate = typ
    sec.UseTypicalSectionTemplate = True
    sec.Mode = "Manual"
    sec.StationText = "20, 50, 80"
    sec.DaylightAuto = False
    sec.CreateChildSections = False

    doc.recompute()

    original_info = QtWidgets.QMessageBox.information
    original_warn = QtWidgets.QMessageBox.warning
    original_question = QtWidgets.QMessageBox.question
    try:
        QtWidgets.QMessageBox.information = staticmethod(lambda *args, **kwargs: 0)
        QtWidgets.QMessageBox.warning = staticmethod(lambda *args, **kwargs: 0)
        QtWidgets.QMessageBox.question = staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)

        panel = CrossSectionEditorTaskPanel()
        panel._refresh_context(preserve_station=True)
        _assert(panel._current_section_set() == sec, "Editor should target the typical-based SectionSet")

        _set_station(panel, 50.0)
        _select_target(panel, "LANE-L", "left")
        panel.cmb_edit_parameter.setCurrentText("Height")
        panel.cmb_edit_scope.setCurrentText("Station Range")
        panel.spin_width.setValue(0.2)
        panel.spin_edit_start_station.setValue(panel._display_from_meters(40.0))
        panel.spin_edit_end_station.setValue(panel._display_from_meters(60.0))
        panel.spin_transition_in.setValue(panel._display_from_meters(0.0))
        panel.spin_transition_out.setValue(panel._display_from_meters(0.0))
        panel._apply_editor_edit()

        _select_target(panel, "BERM-R", "right")
        panel.cmb_edit_parameter.setCurrentText("Extra Width")
        panel.spin_width.setValue(1.5)
        panel._apply_editor_edit()

        _select_target(panel, "BERM-R", "right")
        panel.cmb_edit_parameter.setCurrentText("Back Slope %")
        panel.spin_slope.setValue(12.0)
        panel._apply_editor_edit()

        plan = getattr(sec, "CrossSectionEditPlan", None)
        _assert(plan is not None, "Editor apply should create CrossSectionEditPlan for advanced typical edits")
        records = list(CrossSectionEditPlan.records(plan) or [])
        _assert(len(records) == 3, f"Advanced typical editor apply should create three records, got {len(records)}")
        params = {str(rec.get("Parameter", "") or ""): dict(rec or {}) for rec in records}
        _assert("height" in params, "Height edit-plan record missing")
        _assert("extra_width" in params, "Extra-width edit-plan record missing")
        _assert("back_slope_pct" in params, "Back-slope edit-plan record missing")
        _assert(abs(float(params["height"].get("Value", 0.0) or 0.0) - 0.2) < 1.0e-6, "Height record value mismatch")
        _assert(abs(float(params["extra_width"].get("Value", 0.0) or 0.0) - 1.5) < 1.0e-6, "Extra-width record value mismatch")
        _assert(abs(float(params["back_slope_pct"].get("Value", 0.0) or 0.0) - 12.0) < 1.0e-6, "Back-slope record value mismatch")

        doc.recompute()
        payload = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
        lane = _find_component(payload.get("component_rows", []), "LANE-L", "left")
        berm = _find_component(payload.get("component_rows", []), "BERM-R", "right")
        _assert(lane and berm, "Viewer payload should expose edited LANE-L and BERM-R rows")
        _assert(str(lane.get("source", "") or "") == "cross_section_edit", "Edited LANE-L row should report cross_section_edit source")
        _assert(str(berm.get("source", "") or "") == "cross_section_edit", "Edited BERM-R row should report cross_section_edit source")
        _assert(abs(float(lane.get("height", 0.0) or 0.0) - 0.2) < 1.0e-6, "Edited LANE-L height should be 0.2 m")
        _assert(abs(float(berm.get("extraWidth", 0.0) or 0.0) - 1.5) < 1.0e-6, "Edited BERM-R extra width should be 1.5 m")
        _assert(abs(float(berm.get("backSlopePct", 0.0) or 0.0) - 12.0) < 1.0e-6, "Edited BERM-R back slope should be 12.0%")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-5 typical advanced-parameter edit-plan apply smoke test completed.")
    finally:
        QtWidgets.QMessageBox.information = original_info
        QtWidgets.QMessageBox.warning = original_warn
        QtWidgets.QMessageBox.question = original_question
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
