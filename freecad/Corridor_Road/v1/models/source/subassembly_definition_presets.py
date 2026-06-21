"""Reusable Subassembly definition preset data for Parametric Road v1."""

from __future__ import annotations

from .subassembly_definition_model import (
    SubassemblyDefinition,
    SubassemblyLibrary,
    SubassemblyLinkRow,
    SubassemblyParameterRow,
    SubassemblyPointRow,
    SubassemblyShapeRow,
    SubassemblyTargetRow,
)


SUBASSEMBLY_DEFINITION_PRESETS = {
    "Starter Road Primitives": {
        "library_id": "subassembly-library:starter-road-primitives",
        "note": "Reusable lane, shoulder, sidewalk, side-slope, ditch, curb, and gutter definitions for starter road assemblies.",
        "definitions": [
            {
                "definition_id": "subassembly-definition:lane-basic",
                "name": "Basic Lane",
                "kind": "lane",
                "category": "pavement",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Width", 3.5, "m", True),
                    ("slope", "Crossfall", -2.0, "%", True),
                    ("thickness", "Pavement thickness", 0.25, "m", False),
                    ("material", "Material", "asphalt", "", False),
                ],
                "points": [
                    ("origin", "0", "0", "CROWN", "hinge", True),
                    ("edge", "width", "width*slope/100", "ETW", "edge_of_travel_way", True),
                    ("subgrade_origin", "0", "-thickness", "SUBGRADE", "subgrade", False),
                    ("subgrade_edge", "width", "width*slope/100-thickness", "SUBGRADE", "subgrade", False),
                ],
                "links": [
                    ("fg", "origin", "edge", "design", "lane_fg", "lane_width"),
                    ("subgrade", "subgrade_origin", "subgrade_edge", "subgrade_surface", "lane_subgrade", "subgrade_width"),
                ],
                "shapes": [
                    ("shape:pavement", ("origin", "edge", "subgrade_edge", "subgrade_origin"), "pavement", "pavement_layer"),
                ],
            },
            {
                "definition_id": "subassembly-definition:shoulder-basic",
                "name": "Basic Shoulder",
                "kind": "shoulder",
                "category": "pavement",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Width", 1.8, "m", True),
                    ("slope", "Crossfall", -4.0, "%", True),
                    ("thickness", "Shoulder thickness", 0.20, "m", False),
                    ("material", "Material", "aggregate", "", False),
                ],
                "points": [
                    ("inner", "0", "0", "SHLD_IN", "hinge", True),
                    ("outer", "width", "width*slope/100", "SHLD_OUT", "shoulder_break", True),
                    ("subgrade_inner", "0", "-thickness", "SUBGRADE", "subgrade", False),
                    ("subgrade_outer", "width", "width*slope/100-thickness", "SUBGRADE", "subgrade", False),
                ],
                "links": [
                    ("fg", "inner", "outer", "design", "shoulder_fg", "shoulder_width"),
                    ("subgrade", "subgrade_inner", "subgrade_outer", "subgrade_surface", "shoulder_subgrade", "subgrade_width"),
                ],
                "shapes": [
                    ("shape:shoulder", ("inner", "outer", "subgrade_outer", "subgrade_inner"), "shoulder", "shoulder_body"),
                ],
            },
            {
                "definition_id": "subassembly-definition:side-slope-daylight",
                "name": "Daylight Side Slope",
                "kind": "side_slope",
                "category": "grading",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Search width", 6.0, "m", True),
                    ("slope", "Slope", -33.0, "%", True),
                    ("daylight_mode", "Daylight mode", "terrain", "", False),
                    ("bench_mode", "Bench mode", "none", "", False),
                ],
                "points": [
                    ("hinge", "0", "0", "HINGE", "slope_hinge", True),
                    ("daylight", "width", "width*slope/100", "DAYLIGHT", "daylight", True),
                ],
                "links": [
                    ("slope_face", "hinge", "daylight", "slope_face_surface", "slope_face", "slope_face_area"),
                ],
                "targets": [
                    ("target:terrain-daylight", "terrain_daylight", False, "terrain"),
                ],
            },
            {
                "definition_id": "subassembly-definition:side-slope-bench-daylight",
                "name": "Benched Daylight Side Slope",
                "kind": "side_slope",
                "category": "grading",
                "side_behavior": "both",
                "parameters": [
                    ("side_slope_width", "Side slope width", 12.0, "m", True),
                    ("default_slope", "Default slope", -0.50, "m/m", True),
                    ("cut_slope", "Cut slope", -0.50, "m/m", False),
                    ("fill_slope", "Fill slope", -0.33, "m/m", False),
                    ("bench_mode", "Bench mode", "single", "", False),
                    ("bench_rows", "Bench rows", "3.0,1.5,-0.02,-0.50", "", False),
                    ("pre_bench_width", "Preview pre-bench width", 6.0, "m", False),
                    ("bench_width", "Preview bench width", 1.5, "m", False),
                    ("bench_slope", "Preview bench slope", -0.02, "m/m", False),
                    ("post_slope_width", "Preview post-bench width", 4.5, "m", False),
                    ("post_slope", "Preview post-bench slope", -0.50, "m/m", False),
                    ("repeat_first_bench_to_daylight", "Repeat first bench to daylight", "true", "", False),
                    ("daylight_mode", "Daylight mode", "terrain", "", False),
                    ("daylight_search_step", "Daylight search step", 0.5, "m", False),
                    ("daylight_max_width", "Daylight max width", 160.0, "m", False),
                    ("daylight_max_width_delta", "Daylight max width delta", 0.25, "m", False),
                    ("daylight_max_triangles", "Daylight max triangles", 128, "", False),
                ],
                "points": [
                    ("hinge", "0", "0", "HINGE", "slope_hinge", True),
                    ("bench_start", "pre_bench_width", "pre_bench_width*default_slope", "BENCH_IN", "bench_break", True),
                    (
                        "bench_end",
                        "pre_bench_width+bench_width",
                        "pre_bench_width*default_slope+bench_width*bench_slope",
                        "BENCH_OUT",
                        "bench_break",
                        True,
                    ),
                    (
                        "daylight",
                        "pre_bench_width+bench_width+post_slope_width",
                        "pre_bench_width*default_slope+bench_width*bench_slope+post_slope_width*post_slope",
                        "DAYLIGHT",
                        "daylight",
                        True,
                    ),
                ],
                "links": [
                    ("slope_to_bench", "hinge", "bench_start", "slope_face_surface", "slope_face", "slope_face_area"),
                    ("bench", "bench_start", "bench_end", "slope_face_surface", "bench", "slope_face_area"),
                    ("bench_to_daylight", "bench_end", "daylight", "slope_face_surface", "slope_face", "slope_face_area"),
                ],
                "targets": [
                    ("target:terrain-daylight", "terrain_daylight", False, "terrain"),
                ],
                "note": "Designer-owned side-slope bench preset. Compact bench_rows is the durable source; preview helper parameters keep the current Live Preview editable until typed bench-row evaluation is added.",
            },
            {
                "definition_id": "subassembly-definition:ditch-trapezoid",
                "name": "Trapezoid Roadside Ditch",
                "kind": "ditch",
                "category": "drainage",
                "side_behavior": "both",
                "parameters": [
                    ("top_width", "Top width", 1.8, "m", True),
                    ("bottom_width", "Bottom width", 0.6, "m", True),
                    ("depth", "Depth", 0.45, "m", True),
                    ("inner_slope", "Inner slope", 1.5, "H:V", False),
                    ("outer_slope", "Outer slope", 2.0, "H:V", False),
                    ("lining_thickness", "Lining thickness", 0.0, "m", False),
                    ("material", "Material", "earth", "", False),
                ],
                "points": [
                    ("inner_edge", "0", "0", "DITCH_IN", "ditch_inner", True),
                    ("invert_left", "(top_width-bottom_width)/2", "-depth", "DITCH_INV", "ditch_invert", True),
                    ("invert_right", "(top_width+bottom_width)/2", "-depth", "DITCH_INV", "ditch_invert", True),
                    ("outer_edge", "top_width", "0", "DITCH_OUT", "ditch_outer", True),
                ],
                "links": [
                    ("inner_slope", "inner_edge", "invert_left", "drainage_surface", "ditch_side", "ditch_area"),
                    ("bottom", "invert_left", "invert_right", "drainage_surface", "ditch_bottom", "ditch_area"),
                    ("outer_slope", "invert_right", "outer_edge", "drainage_surface", "ditch_side", "ditch_area"),
                ],
                "shapes": [
                    ("shape:ditch-lining", ("inner_edge", "invert_left", "invert_right", "outer_edge"), "ditch_lining", "lined_ditch_body"),
                ],
                "targets": [
                    ("target:ditch-flowline", "ditch_flowline", False, "use_invert"),
                ],
            },
            {
                "definition_id": "subassembly-definition:gutter-pan",
                "name": "Gutter Pan",
                "kind": "gutter",
                "category": "drainage",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Width", 0.45, "m", True),
                    ("slope", "Pan slope", -3.0, "%", True),
                    ("thickness", "Concrete thickness", 0.18, "m", False),
                    ("material", "Material", "concrete", "", False),
                ],
                "points": [
                    ("inner", "0", "0", "GUTTER_IN", "gutter_inner", True),
                    ("flowline", "width", "width*slope/100", "FLOWLINE", "gutter_flowline", True),
                    ("bottom_inner", "0", "-thickness", "SUBGRADE", "subgrade", False),
                    ("bottom_outer", "width", "width*slope/100-thickness", "SUBGRADE", "subgrade", False),
                ],
                "links": [
                    ("pan", "inner", "flowline", "design", "gutter_pan", "gutter_width"),
                    ("drainage", "inner", "flowline", "drainage_surface", "gutter_flow", "drainage_width"),
                ],
                "shapes": [
                    ("shape:gutter", ("inner", "flowline", "bottom_outer", "bottom_inner"), "gutter", "gutter_body"),
                ],
            },
            {
                "definition_id": "subassembly-definition:curb-basic",
                "name": "Basic Curb",
                "kind": "curb",
                "category": "roadside",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Width", 0.20, "m", True),
                    ("height", "Height", 0.15, "m", True),
                    ("thickness", "Concrete thickness", 0.30, "m", False),
                    ("material", "Material", "concrete", "", False),
                ],
                "points": [
                    ("toe", "0", "0", "CURB_TOE", "curb_toe", True),
                    ("face_top", "0", "height", "CURB_FACE", "curb_face", True),
                    ("back_top", "width", "height", "CURB_BACK", "curb_back", True),
                    ("back_bottom", "width", "-thickness", "CURB_BOTTOM", "curb_bottom", False),
                    ("toe_bottom", "0", "-thickness", "CURB_BOTTOM", "curb_bottom", False),
                ],
                "links": [
                    ("face", "toe", "face_top", "design", "curb_face", "curb_face"),
                    ("top", "face_top", "back_top", "design", "curb_top", "curb_top"),
                ],
                "shapes": [
                    ("shape:curb", ("toe", "face_top", "back_top", "back_bottom", "toe_bottom"), "curb", "curb_body"),
                ],
            },
            {
                "definition_id": "subassembly-definition:sidewalk-basic",
                "name": "Basic Sidewalk",
                "kind": "sidewalk",
                "category": "pedestrian",
                "side_behavior": "both",
                "parameters": [
                    ("width", "Width", 1.8, "m", True),
                    ("slope", "Crossfall", -1.5, "%", True),
                    ("thickness", "Concrete thickness", 0.12, "m", False),
                    ("material", "Material", "concrete", "", False),
                ],
                "points": [
                    ("inner", "0", "0", "SW_IN", "sidewalk_inner", True),
                    ("outer", "width", "width*slope/100", "SW_OUT", "sidewalk_outer", True),
                    ("subgrade_inner", "0", "-thickness", "SUBGRADE", "subgrade", False),
                    ("subgrade_outer", "width", "width*slope/100-thickness", "SUBGRADE", "subgrade", False),
                ],
                "links": [
                    ("walk", "inner", "outer", "design", "sidewalk_fg", "sidewalk_width"),
                    ("subgrade", "subgrade_inner", "subgrade_outer", "subgrade_surface", "sidewalk_subgrade", "subgrade_width"),
                ],
                "shapes": [
                    ("shape:sidewalk", ("inner", "outer", "subgrade_outer", "subgrade_inner"), "sidewalk", "sidewalk_body"),
                ],
            },
        ],
    },
}


def subassembly_definition_preset_names() -> list[str]:
    """Return available reusable Subassembly definition library presets."""

    return list(SUBASSEMBLY_DEFINITION_PRESETS.keys())


def subassembly_definition_library_from_preset(
    preset_name: str,
    *,
    project_id: str = "corridorroad-v1",
) -> SubassemblyLibrary:
    """Build a SubassemblyLibrary source model from a named preset."""

    preset = SUBASSEMBLY_DEFINITION_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Subassembly definition preset: {preset_name}")
    return SubassemblyLibrary(
        schema_version=1,
        project_id=str(project_id or "corridorroad-v1"),
        library_id=str(preset.get("library_id", "") or "subassembly-library:main"),
        preset_name=str(preset_name or ""),
        definition_rows=[_definition_from_spec(spec) for spec in list(preset.get("definitions", []) or [])],
    )


def _definition_from_spec(spec: dict[str, object]) -> SubassemblyDefinition:
    return SubassemblyDefinition(
        definition_id=str(spec.get("definition_id", "") or ""),
        name=str(spec.get("name", "") or ""),
        kind=str(spec.get("kind", "") or "lane"),
        category=str(spec.get("category", "") or ""),
        side_behavior=str(spec.get("side_behavior", "") or "agnostic"),
        parameter_rows=[
            SubassemblyParameterRow(
                parameter_id=str(row[0]),
                label=str(row[1]),
                value=row[2],
                unit=str(row[3]),
                required=bool(row[4]) if len(row) > 4 else False,
            )
            for row in list(spec.get("parameters", []) or [])
        ],
        point_rows=[
            SubassemblyPointRow(
                point_id=str(row[0]),
                x_expr=str(row[1]),
                z_expr=str(row[2]),
                code=str(row[3]) if len(row) > 3 else "",
                role=str(row[4]) if len(row) > 4 else "",
                connectable=bool(row[5]) if len(row) > 5 else False,
            )
            for row in list(spec.get("points", []) or [])
        ],
        link_rows=[
            SubassemblyLinkRow(
                link_id=str(row[0]),
                start_point_ref=str(row[1]),
                end_point_ref=str(row[2]),
                surface_role=str(row[3]) if len(row) > 3 else "",
                code=str(row[4]) if len(row) > 4 else "",
                quantity_role=str(row[5]) if len(row) > 5 else "",
            )
            for row in list(spec.get("links", []) or [])
        ],
        shape_rows=[
            SubassemblyShapeRow(
                shape_id=str(row[0]),
                point_refs=tuple(row[1]) if len(row) > 1 else (),
                shape_code=str(row[2]) if len(row) > 2 else "",
                solid_role=str(row[3]) if len(row) > 3 else "",
            )
            for row in list(spec.get("shapes", []) or [])
        ],
        target_rows=[
            SubassemblyTargetRow(
                target_id=str(row[0]),
                target_kind=str(row[1]) if len(row) > 1 else "",
                required=bool(row[2]) if len(row) > 2 else False,
                fallback_policy=str(row[3]) if len(row) > 3 else "",
            )
            for row in list(spec.get("targets", []) or [])
        ],
        notes=str(spec.get("note", "") or ""),
    )
