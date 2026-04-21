# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-5 edit-plan apply smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_edit_plan_apply.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
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
    raise Exception(f"Station {station} not found in viewer rows")


def _select_target(panel, target_id, side):
    for idx in range(panel.cmb_component_target.count()):
        seg = dict(panel.cmb_component_target.itemData(idx) or {})
        if str(seg.get("id", "") or "").strip().upper() != str(target_id).upper():
            continue
        if str(seg.get("side", "") or "").strip().lower() != str(side).lower():
            continue
        panel.cmb_component_target.setCurrentIndex(idx)
        panel._refresh_editor_target()
        return dict(panel._current_editor_segment() or {})
    raise Exception(f"Target {target_id}/{side} not found")


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorEditPlanApply")

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
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 6.0
    asm.RightSideWidth = 6.0
    asm.LeftSideSlopePct = 30.0
    asm.RightSideSlopePct = 30.0
    asm.UseLeftBench = False
    asm.UseRightBench = False

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
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
        _assert(panel._current_section_set() == sec, "Editor should load the new SectionSet")

        _set_station(panel, 50.0)
        _select_target(panel, "L10", "left")
        panel.cmb_edit_parameter.setCurrentText("Width")
        panel.cmb_edit_scope.setCurrentText("Station Range")
        panel.spin_width.setValue(8.0)
        panel.spin_edit_start_station.setValue(panel._display_from_meters(40.0))
        panel.spin_edit_end_station.setValue(panel._display_from_meters(60.0))
        panel.spin_transition_in.setValue(panel._display_from_meters(5.0))
        panel.spin_transition_out.setValue(panel._display_from_meters(5.0))
        panel._apply_editor_edit()

        plan = getattr(sec, "CrossSectionEditPlan", None)
        _assert(plan is not None, "PH-5 apply should create and link CrossSectionEditPlan")
        _assert(bool(getattr(sec, "UseCrossSectionEditPlan", False)), "SectionSet should enable CrossSectionEditPlan usage after apply")

        records = list(CrossSectionEditPlan.records(plan) or [])
        _assert(len(records) == 1, "Station-range apply should create one edit-plan record")
        rec0 = dict(records[0] or {})
        _assert(str(rec0.get("Scope", "") or "") == "range", "First record should be a range edit")
        _assert(abs(float(rec0.get("StartStation", 0.0) or 0.0) - 40.0) < 1.0e-6, "Range edit start station mismatch")
        _assert(abs(float(rec0.get("EndStation", 0.0) or 0.0) - 60.0) < 1.0e-6, "Range edit end station mismatch")
        _assert(abs(float(rec0.get("TransitionIn", 0.0) or 0.0) - 5.0) < 1.0e-6, "Range edit transition-in mismatch")
        _assert(abs(float(rec0.get("TransitionOut", 0.0) or 0.0) - 5.0) < 1.0e-6, "Range edit transition-out mismatch")
        _assert(str(rec0.get("Parameter", "") or "") == "width", "Range edit parameter mismatch")
        _assert(abs(float(rec0.get("Value", 0.0) or 0.0) - 8.0) < 1.0e-6, "Range edit value mismatch")

        _set_station(panel, 80.0)
        _select_target(panel, "R10", "right")
        panel.cmb_edit_parameter.setCurrentText("Slope %")
        panel.cmb_edit_scope.setCurrentText("Current Station Only")
        panel.spin_slope.setValue(45.0)
        panel._apply_editor_edit()

        records = list(CrossSectionEditPlan.records(plan) or [])
        _assert(len(records) == 2, "Station-only apply should append a second edit-plan record")
        rec1 = next((dict(row or {}) for row in records if str(row.get("Parameter", "") or "") == "slope_pct"), {})
        _assert(rec1, "Station-only slope record missing")
        _assert(str(rec1.get("Scope", "") or "") == "station", "Second record should be a station edit")
        _assert(abs(float(rec1.get("StartStation", 0.0) or 0.0) - 80.0) < 1.0e-6, "Station-only edit station mismatch")
        _assert(abs(float(rec1.get("EndStation", 0.0) or 0.0) - 80.0) < 1.0e-6, "Station-only edit end station mismatch")
        _assert(abs(float(rec1.get("Value", 0.0) or 0.0) - 45.0) < 1.0e-6, "Station-only slope value mismatch")

        doc.recompute()
        payload = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
        comp_rows = list(payload.get("component_rows", []) or [])
        edited = [row for row in comp_rows if str(row.get("side", "") or "") == "left" and str(row.get("source", "") or "") == "cross_section_edit"]
        _assert(edited, "Viewer payload should expose PH-5 range override rows")
        _assert(any(str(rec0.get("Id", "") or "") in str(row.get("editId", "") or "") for row in edited), "Viewer payload missing PH-5 range edit id")

        status = str(getattr(sec, "Status", "") or "")
        _assert("editPlan=2" in status, "SectionSet status should report edit-plan count after editor apply")
        _assert("editPlanActive=" in status, "SectionSet status should report active edit-plan hits after editor apply")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-5 edit-plan apply smoke test completed.")
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
