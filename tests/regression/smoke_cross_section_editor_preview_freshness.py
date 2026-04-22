# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-8 preview-freshness smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_preview_freshness.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
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
        return
    raise Exception(f"Target {target_id}/{side} not found")


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorPreviewFreshness")

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
        panel.cmb_edit_parameter.setCurrentText("Width")
        panel.cmb_edit_scope.setCurrentText("Station Range")
        panel.spin_width.setValue(8.0)
        panel.spin_edit_start_station.setValue(panel._display_from_meters(40.0))
        panel.spin_edit_end_station.setValue(panel._display_from_meters(60.0))

        stale_text = str(panel.txt_impact.toPlainText() or "")
        _assert("Preview is stale. Run Preview Impact again before applying." in stale_text, "Editor should show stale-preview message before preview")
        _assert(not bool(panel.btn_apply_edit.isEnabled()), "Apply should remain disabled while preview is stale")
        _assert("Preview: stale." in str(panel.lbl_preview_state.text() or ""), "Preview status label should report stale state")
        _assert("Preview Impact (Stale)" == str(panel.btn_preview_impact.text() or ""), "Preview button should report stale state")

        panel.btn_preview_impact.click()
        fresh_text = str(panel.txt_impact.toPlainText() or "")
        _assert("Cross Section Editor impact analysis." in fresh_text, "Preview button should populate the impact analysis")
        _assert(bool(panel.btn_apply_edit.isEnabled()), "Apply should enable after a current preview")
        _assert("Preview: current." in str(panel.lbl_preview_state.text() or ""), "Preview status label should report current state")
        _assert("Preview Impact (Current)" == str(panel.btn_preview_impact.text() or ""), "Preview button should report current state")

        panel.spin_width.setValue(8.5)
        stale_text = str(panel.txt_impact.toPlainText() or "")
        _assert("Preview is stale. Run Preview Impact again before applying." in stale_text, "Changing a value should invalidate the preview")
        _assert(not bool(panel.btn_apply_edit.isEnabled()), "Apply should disable again after the preview becomes stale")
        _assert("Preview: stale." in str(panel.lbl_preview_state.text() or ""), "Preview status label should return to stale after edits")

        panel.btn_preview_impact.click()
        _assert(bool(panel.btn_apply_edit.isEnabled()), "Apply should re-enable after rerunning Preview Impact")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-8 preview-freshness smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
