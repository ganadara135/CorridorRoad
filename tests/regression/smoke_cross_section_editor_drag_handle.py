# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-7 drag-handle smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_drag_handle.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
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
        return
    raise Exception(f"Target {target_id}/{side} not found")


def _debug_row(prefix, rows):
    for row in list(rows or []):
        text = str(row or "")
        if text.startswith(prefix):
            return text
    return ""


def _parse_field(row, key, default=""):
    token = f"{key}="
    for part in str(row or "").split("|"):
        if part.startswith(token):
            return part[len(token) :]
    return default


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorDragHandle")

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

    try:
        panel = CrossSectionEditorTaskPanel()
        panel._refresh_context(preserve_station=True)
        _assert(panel._current_section_set() == sec, "Editor should load the new SectionSet")

        _set_station(panel, 50.0)
        _select_target(panel, "L10", "left")
        panel.cmb_editor_mode.setCurrentText("Edit")
        panel.cmb_edit_parameter.setCurrentText("Width")
        panel.cmb_edit_scope.setCurrentText("Station Range")
        panel.spin_edit_start_station.setValue(panel._display_from_meters(40.0))
        panel.spin_edit_end_station.setValue(panel._display_from_meters(60.0))
        panel.spin_transition_in.setValue(panel._display_from_meters(5.0))
        panel.spin_transition_out.setValue(panel._display_from_meters(5.0))
        panel.spin_width.setValue(6.0)
        panel._refresh_editor_apply_state()

        rows = list(getattr(panel, "_editor_overlay_debug_rows", []) or [])
        handle = _debug_row("handle|", rows)
        _assert(handle, "Drag-handle overlay row should exist in Edit mode for width targets")

        hx = float(_parse_field(handle, "x", "0.0") or 0.0)
        hy = float(_parse_field(handle, "y", "0.0") or 0.0)
        started = panel._begin_editor_drag(QtCore.QPointF(hx, -hy))
        _assert(started, "Drag should start when clicking on the handle")
        _assert(getattr(panel, "_editor_drag_state", None), "Drag state should be populated after handle press")

        moved = panel._update_editor_drag(QtCore.QPointF(hx - 2.0, -hy))
        _assert(moved, "Drag update should be handled while a drag is active")
        _assert(abs(float(panel.spin_width.value()) - 8.0) < 1.0e-6, "Dragging left handle 2 m outward should increase width to 8 m")

        finished = panel._finish_editor_drag(QtCore.QPointF(hx - 2.0, -hy))
        _assert(finished, "Drag release should be handled while a drag is active")
        _assert(not getattr(panel, "_editor_drag_state", None), "Drag state should clear after release")

        rows = list(getattr(panel, "_editor_overlay_debug_rows", []) or [])
        preview = _debug_row("preview|", rows)
        _assert(preview, "Preview overlay should update after drag changes the width value")
        _assert("new=8.000" in preview, "Preview overlay should report the dragged width value")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-7 drag-handle smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
