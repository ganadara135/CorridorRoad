# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross Section Editor PH-7 override migration smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_editor_override_migration.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
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
    doc = App.newDocument("CRCrossSectionEditorOverrideMigration")

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

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    RegionPlan.apply_records(
        reg,
        [
            {
                "Id": "BASE_A",
                "RegionType": "roadway",
                "Layer": "base",
                "StartStation": 0.0,
                "EndStation": 100.0,
                "Priority": 0,
                "TransitionIn": 0.0,
                "TransitionOut": 0.0,
                "TemplateName": "",
                "AssemblyName": "",
                "RuleSet": "",
                "SidePolicy": "",
                "DaylightPolicy": "",
                "CorridorPolicy": "",
                "Enabled": True,
                "Notes": "",
                "HintSource": "",
                "HintStatus": "",
                "HintReason": "",
            }
        ],
    )

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_MIG",
                "Enabled": True,
                "Scope": "station",
                "StartStation": 50.0,
                "EndStation": 50.0,
                "TransitionIn": 0.0,
                "TransitionOut": 0.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "width",
                "Value": 8.0,
                "Unit": "m",
                "SourceScope": "side_slope",
                "Notes": "Migration smoke",
            }
        ],
    )

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Manual"
    sec.StationText = "20, 50, 80"
    sec.DaylightAuto = False
    sec.CreateChildSections = False
    sec.RegionPlan = reg
    sec.UseRegionPlan = True
    sec.ApplyRegionOverrides = True
    sec.CrossSectionEditPlan = plan
    sec.UseCrossSectionEditPlan = True

    doc.recompute()

    try:
        panel = CrossSectionEditorTaskPanel()
        panel._refresh_context(preserve_station=True)
        _assert(panel._current_section_set() == sec, "Editor should load the new SectionSet")

        _set_station(panel, 50.0)
        _select_target(panel, "L10", "left")
        panel.btn_preview_impact.click()

        seg = dict(panel._current_editor_segment() or {})
        _assert(str(seg.get("source", "") or "").strip().lower() == "cross_section_edit", "Target should resolve from CrossSectionEditPlan override")
        _assert("EDIT_MIG" in str(seg.get("editId", "") or ""), "Target should expose the edit id for migration")

        text = str(panel.txt_target.toPlainText() or "")
        _assert("CrossSectionEditPlan override EDIT_MIG" in text, "Inspector should explain that the target is a local override")
        _assert("Policy Handoff:" in text, "Inspector should show policy handoff section")
        _assert("RegionPlan.SidePolicy review for BASE_A" in text, "Inspector should describe Region Side Policy handoff")
        impact = str(panel.txt_impact.toPlainText() or "")
        _assert("Available actions:" in impact, "Impact preview should list migration actions")
        _assert("Prep Side Policy" in impact, "Impact preview should include side-policy prep action")
        _assert("Disable Local Override" in impact, "Impact preview should include local-override disable action")
        _assert(panel.btn_resolution_primary.text() == "Prep Side Policy", "Primary migration action should prepare Region Side Policy")
        _assert(panel.btn_resolution_secondary.text() == "Disable Local Override", "Secondary migration action should disable the local override")

        panel.btn_resolution_primary.click()
        _assert(panel.cmb_edit_scope.currentText() == "Active Region", "Prep Side Policy should switch scope to Active Region")
        _assert(panel.cmb_edit_parameter.currentText() == "Region Side Policy", "Prep Side Policy should switch edit parameter to Region Side Policy")

        original_question = QtWidgets.QMessageBox.question
        original_information = QtWidgets.QMessageBox.information
        original_warning = QtWidgets.QMessageBox.warning
        try:
            QtWidgets.QMessageBox.question = lambda *args, **kwargs: QtWidgets.QMessageBox.Yes
            QtWidgets.QMessageBox.information = lambda *args, **kwargs: QtWidgets.QMessageBox.Ok
            QtWidgets.QMessageBox.warning = lambda *args, **kwargs: QtWidgets.QMessageBox.Ok
            panel.btn_resolution_secondary.click()
        finally:
            QtWidgets.QMessageBox.question = original_question
            QtWidgets.QMessageBox.information = original_information
            QtWidgets.QMessageBox.warning = original_warning

        records = list(CrossSectionEditPlan.records(plan) or [])
        migrated = next(rec for rec in records if str(rec.get("Id", "") or "") == "EDIT_MIG")
        _assert(not bool(migrated.get("Enabled", True)), "Disable Local Override should turn the edit-plan row off")

        _select_target(panel, "L10", "left")
        seg = dict(panel._current_editor_segment() or {})
        _assert(str(seg.get("source", "") or "").strip().lower() != "cross_section_edit", "Target should stop resolving from CrossSectionEditPlan after disable")

        panel._teardown()
        print("[PASS] Cross Section Editor PH-7 override-migration smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
