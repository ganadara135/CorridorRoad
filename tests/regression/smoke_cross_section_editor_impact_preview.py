# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-6 impact-preview smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_impact_preview.py', encoding='utf-8').read())"
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
        return dict(panel._current_editor_segment() or {})
    raise Exception(f"Target {target_id}/{side} not found")


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionEditorImpactPreview")

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
        panel.btn_preview_impact.click()

        text = str(panel.txt_impact.toPlainText() or "")
        _assert("Station preview:" in text, "Impact preview should expose station preview rows")
        _assert("adjacent before:" in text, "Impact preview should show adjacent-before station")
        _assert("transition-in start:" in text, "Impact preview should show transition-in start station")
        _assert("range start:" in text, "Impact preview should show range-start station")
        _assert("current selection:" in text, "Impact preview should show current-selection station")
        _assert("range end:" in text, "Impact preview should show range-end station")
        _assert("transition-out end:" in text, "Impact preview should show transition-out end station")
        _assert("adjacent after:" in text, "Impact preview should show adjacent-after station")
        _assert("Boundary roles:" in text, "Impact preview should show boundary-role rows")
        _assert("Transition preview:" in text, "Impact preview should show transition-preview rows")
        _assert("Width:" in text and "->" in text, "Impact preview should summarize old/new width values")
        _assert("transition-in midpoint:" in text, "Impact preview should show transition-in midpoint interpolation")
        _assert("transition-out midpoint:" in text, "Impact preview should show transition-out midpoint interpolation")
        _assert("current station blend:" in text, "Impact preview should show current-station blend factor")
        _assert("Before / after samples:" in text, "Impact preview should show before/after sample rows")
        _assert("before 6.000 m" in text and "after 8.000 m" in text, "Before/after rows should compare old and new width values")
        _assert("| range-core" in text or "| transition-in" in text, "Before/after rows should label station roles")
        _assert("Boundary stations missing from current sampling will be injected:" in text, "Impact preview should warn about missing boundary stations")

        panel.cmb_edit_scope.setCurrentText("Current Station Only")
        panel.btn_preview_impact.click()
        text = str(panel.txt_impact.toPlainText() or "")
        _assert("Station-only geometry edits can create abrupt corridor geometry between" in text, "Station-only impact preview should show continuity warning")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-6 impact-preview smoke test completed.")
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
