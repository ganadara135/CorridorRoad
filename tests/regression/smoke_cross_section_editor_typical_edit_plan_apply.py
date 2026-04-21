# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-5 typical-width edit-plan apply smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_typical_edit_plan_apply.py', encoding='utf-8').read())"
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


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorTypicalEditPlanApply")

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
        panel.cmb_edit_parameter.setCurrentText("Width")
        panel.cmb_edit_scope.setCurrentText("Station Range")
        panel.spin_width.setValue(4.0)
        panel.spin_edit_start_station.setValue(panel._display_from_meters(40.0))
        panel.spin_edit_end_station.setValue(panel._display_from_meters(60.0))
        panel.spin_transition_in.setValue(panel._display_from_meters(0.0))
        panel.spin_transition_out.setValue(panel._display_from_meters(0.0))
        panel._apply_editor_edit()

        plan = getattr(sec, "CrossSectionEditPlan", None)
        _assert(plan is not None, "Editor apply should create CrossSectionEditPlan for typical-width edit")
        records = list(CrossSectionEditPlan.records(plan) or [])
        _assert(len(records) == 1, "Typical-width editor apply should create one record")
        rec = dict(records[0] or {})
        _assert(str(rec.get("TargetId", "") or "") == "LANE-L", "Typical-width record target id mismatch")
        _assert(str(rec.get("SourceScope", "") or "") == "typical", "Typical-width record source scope mismatch")
        _assert(str(rec.get("Parameter", "") or "") == "width", "Typical-width record parameter mismatch")
        _assert(abs(float(rec.get("Value", 0.0) or 0.0) - 4.0) < 1.0e-6, "Typical-width record value mismatch")

        doc.recompute()
        payload = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
        lane = {}
        for row in list(payload.get("component_rows", []) or []):
            if str(row.get("id", "") or "").strip().upper() == "LANE-L" and str(row.get("side", "") or "").strip().lower() == "left":
                lane = dict(row or {})
                break
        _assert(lane, "Viewer payload should expose edited LANE-L row")
        _assert(str(lane.get("source", "") or "") == "cross_section_edit", "Edited LANE-L row should report cross_section_edit source")
        _assert(abs(float(lane.get("width", 0.0) or 0.0) - 4.0) < 1.0e-6, "Edited LANE-L width should be 4.0 m")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-5 typical-width edit-plan apply smoke test completed.")
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
