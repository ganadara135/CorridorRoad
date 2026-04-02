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
    _assert(
        any(str(row.get("scope", "") or "") == "typical" for row in list(payload.get("component_rows", []) or [])),
        "Assembly-driven viewer payload should still expose roadway-standard segments as scope=typical",
    )
    _assert(
        any(str(row.get("scope", "") or "") == "side_slope" for row in list(payload.get("component_rows", []) or [])),
        "Assembly-driven viewer payload should expose slope/bench segments as scope=side_slope",
    )
    _assert(
        any(str(row.get("type", "") or "") in ("cut_slope", "fill_slope") for row in list(payload.get("component_rows", []) or [])),
        "Assembly-driven viewer payload should distinguish cut/fill slope component types",
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
    _assert(
        any(str(row.get("scope", "") or "") == "side_slope" for row in list(layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")),
        "Viewer layout should preserve side-slope scope on planned component labels",
    )
    _assert(
        any(str(row.get("scope", "") or "") == "typical" for row in list(layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")),
        "Viewer layout should preserve typical scope on planned component labels",
    )
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
    lane_label = next((row for row in crowded_labels if str(row.get("role", "") or "") == "component:lane"), None)
    _assert(lane_label is not None, "Crowded layout should keep a lane component callout")
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
    _assert(any(str(row.get("role", "") or "") == "component:carriageway" for row in list(fallback_layout.get("planned_label_rows", []) or [])), "Fallback layout should include carriageway component callouts")
    _assert(
        any(str(row.get("scope", "") or "") == "typical" for row in list(fallback_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:"))
        or any(str(row.get("scope", "") or "") == "typical" for row in list(fallback_layout.get("planned_summary_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")),
        "Fallback layout should keep at least one typical component annotation",
    )
    _assert(
        any(str(row.get("scope", "") or "") == "side_slope" for row in list(fallback_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "").startswith("component:"))
        or any(str(row.get("scope", "") or "") == "side_slope" for row in list(fallback_layout.get("planned_summary_rows", []) or []) if str(row.get("role", "") or "").startswith("component:")),
        "Fallback layout should keep at least one side-slope component annotation",
    )
    _assert(
        any(str(row.get("type", "") or "") in ("cut_slope", "fill_slope") for row in list(payload.get("component_rows", []) or [])),
        "Viewer payload should preserve cut/fill slope types into the station-local component contract",
    )
    grouped_summary = CrossSectionViewerTaskPanel._summary_rows_grouped(list(fallback_layout.get("planned_summary_rows", []) or []))
    _assert(isinstance(grouped_summary, dict), "Summary grouping helper should return a dict")

    crowded_scope_payload = {
        "bounds": {"xmin": -3.0, "xmax": 3.0, "ymin": -1.5, "ymax": 0.8, "width": 6.0, "height": 2.3},
        "section_polylines": [[(-3.0, 0.1), (-2.0, 0.2), (-1.0, 0.25), (0.0, 0.30), (1.0, 0.25), (2.0, 0.2), (3.0, 0.1)]],
        "component_rows": [
            {"kind": "component", "id": "L1", "type": "carriageway", "side": "left", "scope": "typical", "width": "1.200", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "L2", "type": "side_slope", "side": "left", "scope": "side_slope", "width": "0.900", "extraWidth": "0.000", "order": 2},
            {"kind": "component", "id": "L3", "type": "bench", "side": "left", "scope": "side_slope", "width": "0.700", "extraWidth": "0.000", "order": 3},
            {"kind": "component", "id": "R1", "type": "carriageway", "side": "right", "scope": "typical", "width": "1.200", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "R2", "type": "side_slope", "side": "right", "scope": "side_slope", "width": "0.900", "extraWidth": "0.000", "order": 2},
            {"kind": "component", "id": "R3", "type": "bench", "side": "right", "scope": "side_slope", "width": "0.700", "extraWidth": "0.000", "order": 3},
        ],
        "dimension_rows": [
            {"kind": "overall_width", "label": "Overall 6.000 m", "x0": -3.0, "x1": 3.0, "y": -1.9, "value": 6.0, "role": "overall_width"},
        ],
        "station_label": "STA 15.000",
    }
    crowded_scope_layout = CrossSectionViewerTaskPanel.build_layout_plan(crowded_scope_payload)
    _assert(
        any(str(row.get("role", "") or "").startswith("component:") and str(row.get("scope", "") or "") == "side_slope" for row in list(crowded_scope_layout.get("planned_label_rows", []) or [])),
        "Crowded scope-aware layout should keep side-slope component labels visible when scope is enabled",
    )
    _assert(
        any(str(row.get("role", "") or "") == "component:carriageway" and str(row.get("scope", "") or "") == "typical" for row in list(crowded_scope_layout.get("planned_label_rows", []) or [])),
        "Crowded scope-aware layout should keep at least one typical component label visible",
    )
    bench_label = next((row for row in list(crowded_scope_layout.get("planned_label_rows", []) or []) if str(row.get("role", "") or "") == "component:bench"), None)
    _assert(bench_label is not None, "Crowded scope-aware layout should keep a bench component callout")
    crowded_scope_sheet = CrossSectionViewerTaskPanel.build_sheet_svg_markup(
        dict(crowded_scope_payload, **crowded_scope_layout),
        section_set_label="SectionSet (ScopeCrowded)",
        show_structures=False,
        show_labels=True,
        show_dimensions=True,
        include_diagnostics=False,
    )
    _assert(
        "Visible Component Annotations:" in crowded_scope_sheet,
        "Sheet summary should report visible component annotations by scope",
    )
    crowded_scope_filtered = CrossSectionViewerTaskPanel._filter_layout_by_scope(
        dict(crowded_scope_payload, **crowded_scope_layout),
        show_typical=True,
        show_side_slope=False,
        show_daylight=False,
    )
    _assert(
        not any(str(row.get("scope", "") or "") == "side_slope" for row in list(crowded_scope_filtered.get("planned_label_rows", []) or [])),
        "Scope filtering should remove side-slope labels when that scope is hidden",
    )
    _assert(
        not any(str(row.get("scope", "") or "") == "side_slope" for row in list(crowded_scope_filtered.get("planned_component_marker_rows", []) or [])),
        "Scope filtering should remove side-slope markers when that scope is hidden",
    )

    terrain_daylight_payload = {
        "bounds": {"xmin": -5.0, "xmax": 5.0, "ymin": -2.0, "ymax": 1.0, "width": 10.0, "height": 3.0},
        "section_polylines": [[(-5.0, -1.2), (-2.0, -0.2), (0.0, 0.1), (2.0, -0.2), (5.0, -1.1)]],
        "component_rows": [
            {"kind": "component", "id": "L1", "type": "lane", "side": "left", "scope": "typical", "width": "3.000", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "L2", "type": "side_slope", "side": "left", "scope": "side_slope", "width": "2.000", "extraWidth": "0.000", "order": 2},
            {"kind": "component", "id": "R1", "type": "lane", "side": "right", "scope": "typical", "width": "3.000", "extraWidth": "0.000", "order": 1},
            {"kind": "component", "id": "R2", "type": "side_slope", "side": "right", "scope": "side_slope", "width": "2.000", "extraWidth": "0.000", "order": 2},
        ],
        "dimension_rows": [
            {"kind": "overall_width", "label": "Overall 10.000 m", "x0": -5.0, "x1": 5.0, "y": -2.4, "value": 10.0, "role": "overall_width"},
        ],
        "daylight_rows": [
            {"kind": "daylight", "side": "left", "x": -5.0, "y": -1.2, "label": "daylight L", "scope": "daylight", "source": "terrain", "mode": "terrain:local"},
            {"kind": "daylight", "side": "right", "x": 5.0, "y": -1.1, "label": "daylight R", "scope": "daylight", "source": "terrain", "mode": "terrain:local"},
        ],
        "daylight_note": "daylight=terrain:local",
        "daylight_mode": "terrain:local",
        "station_label": "STA 20.000",
    }
    terrain_daylight_layout = CrossSectionViewerTaskPanel.build_layout_plan(terrain_daylight_payload)
    _assert(
        any(str(row.get("role", "") or "") == "daylight_marker" for row in list(terrain_daylight_layout.get("planned_component_marker_rows", []) or [])),
        "Terrain daylight layout should add explicit daylight marker rows",
    )
    _assert(
        any(str(row.get("role", "") or "") == "daylight_label" for row in list(terrain_daylight_layout.get("planned_label_rows", []) or []))
        or any(str(row.get("role", "") or "") == "daylight_marker" for row in list(terrain_daylight_layout.get("planned_summary_rows", []) or [])),
        "Terrain daylight layout should keep a daylight label or summary fallback",
    )
    terrain_daylight_sheet = CrossSectionViewerTaskPanel.build_sheet_svg_markup(
        dict(terrain_daylight_payload, **terrain_daylight_layout),
        section_set_label="SectionSet (Daylight)",
        show_structures=False,
        show_labels=True,
        show_dimensions=True,
        include_diagnostics=False,
    )
    _assert("Daylight Markers: 2" in terrain_daylight_sheet, "Sheet summary should report daylight marker count")
    _assert("Daylight Mode: terrain:local" in terrain_daylight_sheet, "Sheet summary should report daylight mode")
    _assert("Daylight Sides: left, right" in terrain_daylight_sheet, "Sheet summary should report daylight sides")
    _assert("  Daylight:" in terrain_daylight_sheet or "daylight" in terrain_daylight_sheet, "Sheet summary should preserve daylight grouping or labels")
    terrain_daylight_filtered = CrossSectionViewerTaskPanel._filter_layout_by_scope(
        dict(terrain_daylight_payload, **terrain_daylight_layout),
        show_typical=True,
        show_side_slope=True,
        show_daylight=False,
    )
    _assert(
        not any(str(row.get("role", "") or "") == "daylight_marker" for row in list(terrain_daylight_filtered.get("planned_component_marker_rows", []) or [])),
        "Scope filtering should remove daylight markers when the daylight scope is hidden",
    )

    App.closeDocument(doc.Name)
    print("[PASS] Cross-section viewer payload smoke test completed.")


if __name__ == "__main__":
    run()
