# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-7 daylight/conflict overlay smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_conflict_overlay.py', encoding='utf-8').read())"
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


def _debug_row(prefix, rows):
    for row in list(rows or []):
        text = str(row or "")
        if text.startswith(prefix):
            return text
    return ""


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorConflictOverlay")

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

        original_overlap = panel._impact_structure_overlap
        original_class = panel._parameter_class
        try:
            panel._impact_structure_overlap = lambda payload, affected_rows: "CULV-1"
            panel._parameter_class = lambda seg: "daylight"
            panel.cmb_edit_scope.setCurrentText("Current Station Only")
            panel._refresh_editor_target()
            panel.btn_preview_impact.click()
            rows = list(getattr(panel, "_editor_overlay_debug_rows", []) or [])
            blocked = _debug_row("conflict|", rows)
            _assert("state=blocked" in blocked, "Daylight/structure conflict should render blocked overlay state")
            _assert("summary=CULV-1" in blocked, "Blocked conflict overlay should report structure summary")
            text = str(panel.txt_target.toPlainText() or "")
            _assert("Conflict: Blocked by CULV-1" in text, "Inspector should show blocked conflict label")
            _assert("Resolution Guide:" in text, "Inspector should show resolution guidance section")
            _assert(
                "Review the overlapping StructureSet span for CULV-1 before changing daylight behavior." in text,
                "Inspector should explain the daylight conflict resolution path",
            )
            _assert(
                "Switch to Active Region if you need a Region daylight-policy override for this span." in text,
                "Inspector should suggest switching to Active Region for blocked daylight conflicts",
            )
            _assert("Policy Handoff:" in text, "Inspector should show policy handoff guidance")
            _assert("'Use Active Region' switches scope to Active Region" in text, "Inspector should describe the Active Region handoff")
            _assert("'Prep Daylight Policy' prepares RegionPlan.DaylightPolicy = left:off" in text, "Inspector should describe the preferred daylight policy handoff")
            impact = str(panel.txt_impact.toPlainText() or "")
            _assert("Resolution:" in impact, "Impact preview should show resolution guidance")
            _assert("Policy handoff:" in impact, "Impact preview should show policy handoff guidance")
            _assert("RegionPlan.DaylightPolicy = left:off" in impact, "Impact preview should show the preferred policy value")
            apply_text = str(panel.lbl_apply_state.text() or "")
            _assert(
                "Review the overlapping StructureSet span for CULV-1 before changing daylight behavior." in apply_text,
                "Apply state should include the first resolution hint",
            )
            _assert("Next action: 'Use Active Region' switches scope to Active Region" in apply_text, "Apply state should include the first handoff hint")
            _assert(not panel.btn_resolution_primary.isHidden(), "Blocked conflict should expose a primary resolution action")
            _assert(panel.btn_resolution_primary.text() == "Use Active Region", "Blocked conflict primary action should switch to Active Region")
            _assert(not panel.btn_resolution_secondary.isHidden(), "Blocked conflict should expose a secondary resolution action")
            _assert(panel.btn_resolution_secondary.text() == "Prep Daylight Policy", "Blocked conflict secondary action should prepare a Region Daylight Policy edit")
            _assert("Available actions:" in impact, "Impact preview should list available conflict-resolution actions")
            _assert("Use Active Region" in impact, "Impact preview should include the Active Region shortcut")
            _assert("Prep Daylight Policy" in impact, "Impact preview should include the policy-prep shortcut")
            panel.btn_resolution_primary.click()
            _assert(panel.cmb_edit_scope.currentText() == "Active Region", "Primary resolution action should switch scope to Active Region")
            panel.cmb_edit_scope.setCurrentText("Current Station Only")
            panel._refresh_editor_target()
            panel.btn_resolution_secondary.click()
            _assert(panel.cmb_edit_scope.currentText() == "Active Region", "Secondary resolution action should also switch scope to Active Region")
            _assert(panel.cmb_edit_parameter.currentText() == "Region Daylight Policy", "Secondary resolution action should prepare Region Daylight Policy editing")
            _assert(panel.cmb_region_policy.currentData() == "left:off", "Secondary resolution action should prepare the preferred side-specific daylight policy value")

            panel._parameter_class = lambda seg: "geometry"
            panel.cmb_edit_scope.setCurrentText("Station Range")
            panel.cmb_edit_parameter.setCurrentText("Width")
            panel._refresh_editor_target()
            panel.btn_preview_impact.click()
            rows = list(getattr(panel, "_editor_overlay_debug_rows", []) or [])
            warning = _debug_row("conflict|", rows)
            _assert("state=warning" in warning, "Structure overlap on geometry edits should render warning overlay state")
            text = str(panel.txt_target.toPlainText() or "")
            _assert("Conflict: Review CULV-1" in text, "Inspector should show warning conflict label")
            _assert("Review the before/after overlay and impact preview before apply." in text, "Inspector should show warning resolution guidance")
            _assert("Policy Handoff:" in text, "Inspector should show handoff guidance for warning conflicts")
            impact = str(panel.txt_impact.toPlainText() or "")
            _assert("Prefer Active Region or structure-side policy changes when the conflict extends across multiple stations." in impact, "Impact preview should suggest broader-scope conflict resolution")
            _assert("'Narrow To Current' reduces the review span to STA 50.000 m only." in impact, "Impact preview should describe the scope-narrowing handoff")
            _assert(panel.btn_resolution_primary.text() == "Use Active Region", "Warning conflict primary action should prefer Active Region")
            _assert(panel.btn_resolution_secondary.text() == "Narrow To Current", "Warning conflict secondary action should offer local narrowing")
            panel.btn_resolution_secondary.click()
            _assert(panel.cmb_edit_scope.currentText() == "Current Station Only", "Warning conflict secondary action should narrow the scope")
        finally:
            panel._impact_structure_overlap = original_overlap
            panel._parameter_class = original_class

        panel._teardown()
        print("[PASS] Cross Section Editor PH-7 daylight/conflict overlay smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
