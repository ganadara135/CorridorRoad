# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross-section viewer payload smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_cross_section_viewer_payload.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.ui.task_cross_section_viewer import CrossSectionViewerTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRCrossSectionViewerPayload")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(50.0, 0.0, 0.0)]
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
    asm.LeftSideSlopePct = -33.0
    asm.RightSideSlopePct = -33.0

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["CULV-1"]
    ss.StructureTypes = ["culvert"]
    ss.StartStations = [20.0]
    ss.EndStations = [30.0]
    ss.CenterStations = [25.0]
    ss.Sides = ["both"]
    ss.Widths = [4.0]
    ss.Heights = [2.0]
    ss.BehaviorModes = ["section_overlay"]
    ss.CorridorModes = ["skip_zone"]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 50.0
    sec.Interval = 25.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureCenters = True
    sec.IncludeStructureStartEnd = False
    sec.IncludeStructureTransitionStations = False
    sec.CreateChildSections = False

    doc.recompute()

    rows = SectionSet.resolve_viewer_station_rows(sec)
    _assert(len(rows) == 3, f"Expected 3 viewer station rows, got {len(rows)}")
    _assert(any(abs(float(row.get("station", 0.0)) - 25.0) <= 1e-6 for row in rows), "Viewer rows missing 25.0 station")

    payload = SectionSet.resolve_viewer_payload(sec, station=25.0, include_structure_overlay=True)
    _assert(payload, "Viewer payload should not be empty")
    _assert(abs(float(payload.get("station", 0.0)) - 25.0) <= 1e-6, "Viewer payload station mismatch")
    _assert(len(list(payload.get("section_polylines", []) or [])) >= 1, "Viewer payload missing section polylines")
    _assert(any(len(poly) >= 5 for poly in list(payload.get("section_polylines", []) or [])), "Viewer section polyline is too small")
    _assert(bool(payload.get("has_structure", False)), "Viewer payload should report structure presence")
    _assert(len(list(payload.get("overlay_polylines", []) or [])) >= 1, "Viewer payload missing structure overlay polylines")
    bounds = dict(payload.get("bounds", {}) or {})
    _assert(float(bounds.get("width", 0.0) or 0.0) > 1e-6, "Viewer payload width should be positive")
    _assert(float(bounds.get("height", 0.0) or 0.0) >= 0.0, "Viewer payload height should be non-negative")
    _assert("CULV-1" in list(payload.get("structure_ids", []) or []), "Viewer payload missing structure id")
    _assert(len(list(payload.get("diagnostic_tokens", []) or [])) >= 1, "Viewer payload missing diagnostic tokens")
    _assert(len(list(payload.get("label_rows", []) or [])) >= 1, "Viewer payload missing label rows")
    _assert(len(list(payload.get("dimension_rows", []) or [])) >= 1, "Viewer payload missing dimension rows")
    _assert(len(list(payload.get("component_rows", []) or [])) >= 1, "Viewer payload missing component rows")
    _assert(
        all(str(row.get("kind", "") or "") == "component_segment" for row in list(payload.get("component_rows", []) or [])),
        "Viewer payload component rows should use the section component-segment contract",
    )
    _assert(
        len(list(payload.get("component_rows", []) or [])) >= 4,
        "Viewer payload should provide the active station's component segments",
    )
    _assert(isinstance(payload.get("structure_rows", []), list), "Viewer payload structure rows should be a list")
    _assert(isinstance(payload.get("bench_rows", []), list), "Viewer payload bench rows should be a list")
    layout = CrossSectionViewerTaskPanel.build_layout_plan(payload)
    _assert(len(list(layout.get("planned_title_rows", []) or [])) >= 1, "Viewer layout plan should include a station title row")
    _assert(len(list(layout.get("planned_dimension_rows", []) or [])) >= 1, "Viewer layout plan missing dimension rows")
    _assert(isinstance(layout.get("planned_label_rows", []), list), "Viewer layout plan label rows should be a list")
    _assert(isinstance(layout.get("planned_component_marker_rows", []), list), "Viewer layout plan marker rows should be a list")
    _assert(isinstance(layout.get("planned_summary_rows", []), list), "Viewer layout plan summary rows should be a list")
    _assert(all("slot" in row for row in list(layout.get("planned_dimension_rows", []) or [])), "Planned dimension rows should include slot")
    svg = CrossSectionViewerTaskPanel.build_svg_markup(payload, show_structures=True, show_labels=True, show_dimensions=True)
    _assert("<svg" in svg and "</svg>" in svg, "Viewer SVG export markup is incomplete")
    _assert("Overall" in svg, "Viewer SVG export markup missing dimension label")
    _assert(
        ("CULV-1" in svg or "Structure" in svg)
        or any(str(row.get("role", "") or "") == "structure_summary" for row in list(layout.get("planned_summary_rows", []) or [])),
        "Viewer SVG/layout should preserve structure information either in drawing text or summary fallback",
    )
    sheet_svg = CrossSectionViewerTaskPanel.build_sheet_svg_markup(
        payload,
        section_set_label="SectionSet (SectionSet001)",
        show_structures=True,
        show_labels=True,
        show_dimensions=True,
        include_diagnostics=True,
    )
    _assert("Cross Section Sheet" in sheet_svg, "Viewer sheet SVG missing sheet title")
    _assert("Review Summary" in sheet_svg, "Viewer sheet SVG missing summary block")
    _assert("Section Set:" in sheet_svg, "Viewer sheet SVG missing section summary")

    crowded_payload = {
        "bounds": {"xmin": -2.0, "xmax": 2.0, "ymin": -1.0, "ymax": 1.0, "width": 4.0, "height": 2.0},
        "section_polylines": [[(-2.0, 0.0), (-1.0, 0.2), (0.0, 0.3), (1.0, 0.2), (2.0, 0.0)]],
        "label_rows": [
            {"text": "Left Shoulder", "x": -2.0, "y": 1.2, "role": "top_edge_left"},
            {"text": "Tags: STA / BENCH / DAYLIGHT", "x": -2.0, "y": 1.4, "role": "station_tags"},
            {"text": "Long Structure Summary", "x": 0.0, "y": 1.3, "role": "structure_summary"},
        ],
        "component_rows": [
            {"kind": "component", "id": "L1", "type": "lane", "side": "left", "width": "1.500", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "SHL", "type": "shoulder", "side": "left", "width": "1.000", "extraWidth": "0.000", "order": 2},
            {"kind": "component", "id": "D1", "type": "ditch", "side": "right", "width": "1.000", "extraWidth": "0.000", "order": 1},
        ],
        "dimension_rows": [
            {"kind": "component_left", "label": "LANE-LF 3.500 m", "x0": -1.8, "x1": -0.9, "y": -1.2, "value": 0.9, "role": "lane"},
            {"kind": "component_left", "label": "SHLDR-LF 1.500 m", "x0": -1.2, "x1": -0.6, "y": -1.2, "value": 0.6, "role": "shoulder"},
            {"kind": "component_right", "label": "DITCH-RT 1.250 m", "x0": 0.6, "x1": 1.1, "y": -1.2, "value": 0.5, "role": "ditch"},
            {"kind": "overall_width", "label": "Overall 4.000 m", "x0": -2.0, "x1": 2.0, "y": -1.4, "value": 4.0, "role": "overall_width"},
        ],
        "station_label": "STA 0.000",
    }
    crowded_layout = CrossSectionViewerTaskPanel.build_layout_plan(crowded_payload)
    _assert(
        any(int(row.get("slot", 0) or 0) > 0 for row in list(crowded_layout.get("planned_label_rows", []) or []))
        or any(str(row.get("orientation", "") or "") == "vertical" for row in list(crowded_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:"))
        or len(list(crowded_layout.get("planned_summary_rows", []) or [])) >= 1,
        "Crowded layout should either stack, rotate, or summary-fallback some labels",
    )
    crowded_labels = list(crowded_layout.get("planned_label_rows", []) or [])
    crowded_dims = list(crowded_layout.get("planned_dimension_rows", []) or [])
    raw_dims = list(crowded_payload.get("dimension_rows", []) or [])
    _assert(
        (len(crowded_dims) < len(raw_dims))
        or any(float(row.get("font_scale", 1.0) or 1.0) < 0.999 for row in crowded_dims if str(row.get("role", "") or "") not in ("overall_width", "left_reach", "right_reach"))
        or any(float(row.get("font_scale", 1.0) or 1.0) < 0.999 for row in crowded_labels if str(row.get("role", "") or "").startswith("component:"))
        or any(str(row.get("orientation", "") or "") == "vertical" for row in crowded_labels if str(row.get("role", "") or "").startswith("component:"))
        or len(list(crowded_layout.get("planned_summary_rows", []) or [])) >= 1,
        "Crowded layout should suppress, shrink, rotate, or summary-fallback some narrow planned annotations",
    )
    _assert(any(str(row.get("role", "") or "") == "overall_width" for row in list(crowded_layout.get("planned_dimension_rows", []) or [])), "Crowded layout should keep the overall width dimension")
    _assert(any(str(row.get("role", "") or "").startswith("component:") for row in list(crowded_layout.get("planned_label_rows", []) or [])), "Crowded layout should create component-aware labels")
    _assert(any(str(row.get("orientation", "") or "") == "vertical" for row in list(crowded_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")), "Crowded layout should allow vertical component labels")
    _assert(not any(str(row.get("text", "") or "").startswith("L ") or str(row.get("text", "") or "").startswith("R ") for row in list(crowded_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")), "Component labels inside the drawing should not include side prefixes")
    _assert(
        any(float(row.get("viewer_point_size", 0.0) or 0.0) < 1.30 for row in crowded_labels if str(row.get("role", "") or "").startswith("component:")),
        "Crowded component labels should reduce viewer font size to fit the segment span",
    )
    _assert(
        any(float(row.get("font_scale", 1.0) or 1.0) < 0.999 for row in list(crowded_layout.get("planned_label_rows", []) or []) + list(crowded_layout.get("planned_dimension_rows", []) or []))
        or any(str(row.get("orientation", "") or "") == "vertical" for row in list(crowded_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:"))
        or len(list(crowded_layout.get("planned_summary_rows", []) or [])) >= 1,
        "Crowded layout should shrink, rotate, or summary-fallback some planned text",
    )
    _assert(len(list(crowded_layout.get("planned_component_marker_rows", []) or [])) >= 2, "Crowded layout should produce component marker rows")
    _assert(all(float(row.get("tick_len", 0.0) or 0.0) > 0.0 for row in list(crowded_layout.get("planned_component_marker_rows", []) or [])), "Component marker rows should include positive tick length")
    _assert(all(float(row.get("stroke_width", 0.0) or 0.0) > 0.0 for row in list(crowded_layout.get("planned_component_marker_rows", []) or [])), "Component marker rows should include positive stroke width")
    _assert(any(str(row.get("marker_style", "") or "") == "dimension_guide" for row in list(crowded_layout.get("planned_component_marker_rows", []) or [])), "Component marker rows should describe the guide style")
    _assert(any(str(row.get("role", "") or "") in ("structure_summary", "station_tags", "top_edge_left", "top_edge_right") for row in list(crowded_layout.get("planned_summary_rows", []) or [])), "Crowded layout should move diagnostic/top labels into summary fallback when components are present")

    fallback_payload = {
        "bounds": {"xmin": -8.0, "xmax": 8.0, "ymin": -3.0, "ymax": 1.0, "width": 16.0, "height": 4.0},
        "section_polylines": [[(-8.0, 0.0), (-2.0, 0.5), (0.0, 0.6), (2.0, 0.5), (8.0, 0.0)]],
        "component_rows": [
            {"kind": "component", "id": "L1", "type": "carriageway", "side": "left", "width": "4.000", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "L10", "type": "side_slope", "side": "left", "width": "4.000", "extraWidth": "0.000", "order": 10},
            {"kind": "component", "id": "R1", "type": "carriageway", "side": "right", "width": "4.000", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "R10", "type": "side_slope", "side": "right", "width": "4.000", "extraWidth": "0.000", "order": 10},
        ],
        "dimension_rows": [
            {"kind": "overall_width", "label": "Overall 16.000 m", "x0": -8.0, "x1": 8.0, "y": -3.8, "value": 16.0, "role": "overall_width"},
        ],
        "station_label": "STA 10.000",
    }
    fallback_layout = CrossSectionViewerTaskPanel.build_layout_plan(fallback_payload)
    _assert(any(str(row.get("text", "") or "") == "STA 10.000" for row in list(fallback_layout.get("planned_title_rows", []) or [])), "Viewer layout should keep a single station title row")
    _assert(any(str(row.get("role", "") or "") == "component:carriageway" for row in list(fallback_layout.get("planned_component_marker_rows", []) or [])), "Fallback layout should include carriageway component guides")
    _assert(any(str(row.get("role", "") or "") == "component_value:carriageway" for row in list(fallback_layout.get("planned_label_rows", []) or [])), "Fallback layout should include vertical component value labels")

    App.closeDocument(doc.Name)
    print("[PASS] Cross-section viewer payload smoke test completed.")


if __name__ == "__main__":
    run()
