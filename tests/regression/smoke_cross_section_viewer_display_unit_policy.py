# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross-section viewer display-unit policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_cross_section_viewer_display_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRCrossSectionViewerDisplayUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"

        panel = CrossSectionViewerTaskPanel()
        payload = {
            "station": 25.0,
            "station_label": "STA 25.000",
            "tag_summary": "PI",
            "top_profile_edge_summary": "road/road",
            "pavement_total_thickness": 0.25,
            "enabled_pavement_layer_count": 2,
            "pavement_layer_count": 2,
            "bench_summary": "-",
            "bounds": {"xmin": -3.5, "xmax": 3.5, "ymin": -1.0, "ymax": 1.0, "width": 7.0, "height": 2.0},
            "section_polylines": [[(-3.5, 0.0), (0.0, 0.2), (3.5, 0.0)]],
            "overlay_polylines": [],
            "component_rows": [
                {"kind": "component_segment", "role": "component:lane", "type": "lane", "side": "left", "span": 3.5, "x0": -3.5, "x1": 0.0, "mid": -1.75},
                {"kind": "component_segment", "role": "component:lane", "type": "lane", "side": "right", "span": 3.5, "x0": 0.0, "x1": 3.5, "mid": 1.75},
            ],
            "dimension_rows": [
                {"kind": "overall_width", "role": "overall_width", "label": "Overall 7.000 m", "value": 7.0, "x0": -3.5, "x1": 3.5, "y": -1.4},
            ],
            "label_rows": [],
        }

        prepared = panel._prepare_display_payload(payload)
        _assert(prepared["station_label"] == "STA 25000.000", "Prepared payload should rewrite station label in display unit")
        _assert(prepared["station_display_text"] == "25000.000", "Prepared payload should expose station display text")
        _assert(prepared["pavement_total_display_text"] == "250.000", "Prepared payload should expose pavement thickness display text")
        _assert(abs(float(prepared["component_rows"][0]["display_span"]) - 3500.0) < 1.0e-6, "Prepared payload should convert component span to display unit")
        _assert(abs(float(prepared["dimension_rows"][0]["display_value"]) - 7000.0) < 1.0e-6, "Prepared payload should convert dimension value to display unit")

        lines = panel._summary_lines(prepared, include_diagnostics=False)
        summary = "\n".join(lines)
        _assert("Station: 25000.000 mm" in summary, "Viewer summary should display station in active display unit")
        _assert("Pavement: 250.000 mm" in summary, "Viewer summary should display pavement thickness in active display unit")

        plan = CrossSectionViewerTaskPanel.build_layout_plan(prepared)
        _assert(
            any(str(row.get("text", "") or "").endswith(" mm") for row in list(plan.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component_value:")),
            "Viewer layout should emit component value labels in display unit",
        )
        _assert(
            any("mm" in str(row.get("text", "") or "") for row in list(plan.get("planned_dimension_rows", []) or [])),
            "Viewer layout should emit dimension labels in display unit",
        )
        _assert(
            any(str(row.get("text", "") or "") == "STA 25000.000" for row in list(plan.get("planned_title_rows", []) or [])),
            "Viewer layout title should reuse display-unit station text",
        )

        panel._current_payload = prepared
        export_summary = panel._export_success_text("PNG", "section.png")
        _assert("PNG exported." in export_summary, "Viewer export summary should report export kind")
        _assert("Display unit: mm" in export_summary, "Viewer export summary should report display unit")
        _assert("Station: STA 25000.000" in export_summary, "Viewer export summary should report station label")
        _assert("Path: section.png" in export_summary, "Viewer export summary should report output path")

        panel._teardown()
        print("[PASS] Cross-section viewer display-unit policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
