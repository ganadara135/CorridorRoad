"""Shared Assembly/Subassembly preset data for Parametric Road v1."""

from __future__ import annotations

from ..models.source.assembly_model import ASSEMBLY_BENCH_MODES, ASSEMBLY_DAYLIGHT_MODES


DITCH_SHAPES = ("trapezoid", "u", "l", "rectangular", "v", "custom_polyline")
DITCH_PARAMETER_KEYS = (
    "shape",
    "top_width",
    "bottom_width",
    "depth",
    "inner_slope",
    "outer_slope",
    "invert_offset",
    "wall_thickness",
    "lining_thickness",
    "wall_side",
    "section_points",
)
DITCH_PARAMETER_FIELDS = (
    ("top_width", "Top width"),
    ("bottom_width", "Bottom width"),
    ("depth", "Depth"),
    ("inner_slope", "Inner slope"),
    ("outer_slope", "Outer slope"),
    ("invert_offset", "Invert offset"),
    ("wall_thickness", "Wall thickness"),
    ("lining_thickness", "Lining thickness"),
    ("wall_side", "Wall side"),
    ("section_points", "Section points"),
)
DITCH_SHAPE_FIELDS = {
    "trapezoid": ("top_width", "bottom_width", "depth", "inner_slope", "outer_slope"),
    "u": ("bottom_width", "depth", "wall_thickness", "lining_thickness"),
    "l": ("top_width", "bottom_width", "depth", "wall_thickness", "wall_side", "lining_thickness"),
    "rectangular": ("bottom_width", "depth", "wall_thickness", "lining_thickness"),
    "v": ("top_width", "depth", "invert_offset", "inner_slope", "outer_slope"),
    "custom_polyline": ("section_points",),
}
DITCH_SHAPE_DEFAULTS = {
    "trapezoid": {"top_width": "1.800", "bottom_width": "0.600", "depth": "0.450", "inner_slope": "1.500", "outer_slope": "2.000"},
    "u": {"bottom_width": "0.600", "depth": "0.500", "wall_thickness": "0.150", "lining_thickness": "0.120"},
    "l": {"top_width": "1.000", "bottom_width": "0.700", "depth": "0.450", "wall_thickness": "0.150", "wall_side": "inner"},
    "rectangular": {"bottom_width": "0.800", "depth": "0.500", "wall_thickness": "0.150", "lining_thickness": "0.120"},
    "v": {"top_width": "1.600", "depth": "0.400", "invert_offset": "0.800", "inner_slope": "2.000", "outer_slope": "2.000"},
    "custom_polyline": {"section_points": "0,0,inner_edge;0.5,-0.4,invert;1.0,0,outer_edge"},
}

SUBASSEMBLY_KIND_DEFINITION_REFS = {
    "sidewalk": "subassembly-definition:sidewalk-basic",
}


ASSEMBLY_PRESETS = {
    "Basic Road": {
        "assembly_id": "assembly:basic-road",
        "template_id": "template:basic-road",
        "label": "Basic Road Assembly",
        "template_label": "Basic Road",
        "note": "Two-lane rural starter with shoulders and earth side slopes.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.5, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.5, -0.04, 0.20, "aggregate", "Right shoulder"),
            ("side_slope:left", "side_slope", "left", 4.0, -0.5, 0.0, "earth", "Left slope face"),
            ("side_slope:right", "side_slope", "right", 4.0, -0.5, 0.0, "earth", "Right slope face"),
        ],
    },
    "Digital Twin Ready Road": {
        "assembly_id": "assembly:digital-twin-ready-road",
        "template_id": "template:digital-twin-ready-road",
        "label": "Digital Twin Ready Road Assembly",
        "template_label": "Digital Twin Ready Road",
        "note": "Ordinary road sample with explicit physical-body pavement, subbase, shoulder material, and thickness contracts for Watertight Solid readiness QA.",
        "subassemblies": [
            ("pavement_layer:main", "pavement_layer", "center", 7.0, -0.02, 0.18, "asphalt_surface", "Closed pavement layer body target across both travel lanes", {"solid_family": "pavement_layer", "shape_code": "pavement_body"}),
            ("subbase:main", "subbase", "center", 8.4, -0.02, 0.30, "crushed_stone", "Closed subbase body target under lanes and shoulders", {"solid_family": "subbase", "shape_code": "subbase_body"}),
            ("lane:left", "lane", "left", 3.5, -0.02, 0.18, "asphalt_surface", "Left travel lane surface"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.18, "asphalt_surface", "Right travel lane surface"),
            ("shoulder:left", "shoulder", "left", 1.2, -0.035, 0.16, "aggregate_shoulder", "Left shoulder body and surface contract"),
            ("shoulder:right", "shoulder", "right", 1.2, -0.035, 0.16, "aggregate_shoulder", "Right shoulder body and surface contract"),
            ("side_slope:left", "side_slope", "left", 4.5, -0.5, 0.0, "earth", "Left daylight grading surface"),
            ("side_slope:right", "side_slope", "right", 4.5, -0.5, 0.0, "earth", "Right daylight grading surface"),
        ],
    },
    "Urban Curb & Gutter": {
        "assembly_id": "assembly:urban-curb-gutter",
        "template_id": "template:urban-curb-gutter",
        "label": "Urban Curb & Gutter Assembly",
        "template_label": "Urban Curb & Gutter",
        "note": "Urban road with lanes, gutters, curbs, sidewalks, and shallow grading strips.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.25, -0.02, 0.28, "asphalt", "Left urban lane"),
            ("lane:right", "lane", "right", 3.25, -0.02, 0.28, "asphalt", "Right urban lane"),
            ("gutter:left", "gutter", "left", 0.45, -0.03, 0.18, "concrete", "Left gutter pan"),
            ("gutter:right", "gutter", "right", 0.45, -0.03, 0.18, "concrete", "Right gutter pan"),
            ("curb:left", "curb", "left", 0.20, 0.0, 0.30, "concrete", "Left curb"),
            ("curb:right", "curb", "right", 0.20, 0.0, 0.30, "concrete", "Right curb"),
            ("sidewalk:left", "sidewalk", "left", 1.8, -0.015, 0.12, "concrete", "Left sidewalk"),
            ("sidewalk:right", "sidewalk", "right", 1.8, -0.015, 0.12, "concrete", "Right sidewalk"),
            ("green_strip:left", "green_strip", "left", 1.0, -0.03, 0.0, "landscape", "Left verge"),
            ("green_strip:right", "green_strip", "right", 1.0, -0.03, 0.0, "landscape", "Right verge"),
        ],
    },
    "Divided Road": {
        "assembly_id": "assembly:divided-road",
        "template_id": "template:divided-road",
        "label": "Divided Road Assembly",
        "template_label": "Divided Road",
        "note": "Four-lane divided road with center median, shoulders, barriers, and side slopes.",
        "subassemblies": [
            ("median:center", "median", "center", 3.0, 0.0, 0.18, "landscape", "Raised or depressed median allowance"),
            ("lane:left-1", "lane", "left", 3.5, -0.02, 0.30, "asphalt", "Inner left lane"),
            ("lane:left-2", "lane", "left", 3.5, -0.02, 0.30, "asphalt", "Outer left lane"),
            ("lane:right-1", "lane", "right", 3.5, -0.02, 0.30, "asphalt", "Inner right lane"),
            ("lane:right-2", "lane", "right", 3.5, -0.02, 0.30, "asphalt", "Outer right lane"),
            ("shoulder:left", "shoulder", "left", 2.5, -0.04, 0.22, "aggregate", "Left outside shoulder"),
            ("shoulder:right", "shoulder", "right", 2.5, -0.04, 0.22, "aggregate", "Right outside shoulder"),
            ("barrier:left", "barrier", "left", 0.4, 0.0, 0.0, "concrete", "Left roadside barrier placeholder"),
            ("barrier:right", "barrier", "right", 0.4, 0.0, 0.0, "concrete", "Right roadside barrier placeholder"),
            ("side_slope:left", "side_slope", "left", 5.0, -0.4, 0.0, "earth", "Left slope face"),
            ("side_slope:right", "side_slope", "right", 5.0, -0.4, 0.0, "earth", "Right slope face"),
        ],
    },
    "Bridge Interface": {
        "assembly_id": "assembly:bridge-interface",
        "template_id": "template:bridge-interface",
        "label": "Bridge Interface Assembly",
        "template_label": "Bridge Interface",
        "note": "Road deck handoff with barriers and structure-interface placeholders; slope faces are intentionally omitted.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.22, "asphalt", "Left bridge lane wearing surface"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.22, "asphalt", "Right bridge lane wearing surface"),
            ("shoulder:left", "shoulder", "left", 1.2, -0.02, 0.18, "asphalt", "Left bridge shoulder"),
            ("shoulder:right", "shoulder", "right", 1.2, -0.02, 0.18, "asphalt", "Right bridge shoulder"),
            ("barrier:left", "barrier", "left", 0.45, 0.0, 0.0, "concrete", "Left bridge barrier placeholder"),
            ("barrier:right", "barrier", "right", 0.45, 0.0, 0.0, "concrete", "Right bridge barrier placeholder"),
            ("structure_interface:deck", "structure_interface", "center", 0.0, 0.0, 0.0, "structure", "Bridge deck structure handoff"),
        ],
    },
    "Drainage Ditch Road": {
        "assembly_id": "assembly:drainage-ditch-road",
        "template_id": "template:drainage-ditch-road",
        "label": "Drainage Ditch Road Assembly",
        "template_label": "Drainage Ditch Road",
        "note": "Rural road with shoulders, ditch Subassemblies, and wider side-slope grading.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.8, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.8, -0.04, 0.20, "aggregate", "Right shoulder"),
            ("ditch:left", "ditch", "left", 1.8, -0.02, 0.0, "earth", "Left trapezoid roadside ditch", {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0}),
            ("ditch:right", "ditch", "right", 1.8, -0.02, 0.0, "earth", "Right trapezoid roadside ditch", {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0}),
            ("side_slope:left", "side_slope", "left", 6.0, -0.33, 0.0, "earth", "Left slope face to terrain"),
            ("side_slope:right", "side_slope", "right", 6.0, -0.33, 0.0, "earth", "Right slope face to terrain"),
        ],
    },
    "Benched Slope Road": {
        "assembly_id": "assembly:benched-slope-road",
        "template_id": "template:benched-slope-road",
        "label": "Benched Slope Road Assembly",
        "template_label": "Benched Slope Road",
        "note": "Rural road with side-slope bench intent stored on side_slope Subassembly parameters.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.5, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.5, -0.04, 0.20, "aggregate", "Right shoulder"),
            (
                "side_slope:left",
                "side_slope",
                "left",
                12.0,
                -0.5,
                0.0,
                "earth",
                "Left side slope with repeatable bench intent",
                {
                    "bench_mode": "rows",
                    "bench_rows": [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
                    "repeat_first_bench_to_daylight": True,
                    "daylight_mode": "terrain",
                    "daylight_max_width": 80.0,
                },
            ),
            (
                "side_slope:right",
                "side_slope",
                "right",
                12.0,
                -0.5,
                0.0,
                "earth",
                "Right side slope with repeatable bench intent",
                {
                    "bench_mode": "rows",
                    "bench_rows": [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
                    "repeat_first_bench_to_daylight": True,
                    "daylight_mode": "terrain",
                    "daylight_max_width": 80.0,
                },
            ),
        ],
    },
    "Benched Ditch Road": {
        "assembly_id": "assembly:benched-ditch-road",
        "template_id": "template:benched-ditch-road",
        "label": "Benched Ditch Road Assembly",
        "template_label": "Benched Ditch Road",
        "note": "Rural road with roadside trapezoid ditches and repeatable bench intent on the outer side slopes.",
        "subassemblies": [
            ("lane:left", "lane", "left", 3.5, -0.02, 0.25, "asphalt", "Left travel lane"),
            ("lane:right", "lane", "right", 3.5, -0.02, 0.25, "asphalt", "Right travel lane"),
            ("shoulder:left", "shoulder", "left", 1.8, -0.04, 0.20, "aggregate", "Left shoulder"),
            ("shoulder:right", "shoulder", "right", 1.8, -0.04, 0.20, "aggregate", "Right shoulder"),
            (
                "ditch:left",
                "ditch",
                "left",
                1.8,
                -0.02,
                0.0,
                "earth",
                "Left trapezoid roadside ditch before benched slope",
                {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0},
            ),
            (
                "ditch:right",
                "ditch",
                "right",
                1.8,
                -0.02,
                0.0,
                "earth",
                "Right trapezoid roadside ditch before benched slope",
                {"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.45, "inner_slope": 1.5, "outer_slope": 2.0},
            ),
            (
                "side_slope:left",
                "side_slope",
                "left",
                14.0,
                -0.5,
                0.0,
                "earth",
                "Left outer side slope with repeatable bench intent",
                {
                    "bench_mode": "rows",
                    "bench_rows": [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
                    "repeat_first_bench_to_daylight": True,
                    "daylight_mode": "terrain",
                    "daylight_max_width": 80.0,
                },
            ),
            (
                "side_slope:right",
                "side_slope",
                "right",
                14.0,
                -0.5,
                0.0,
                "earth",
                "Right outer side slope with repeatable bench intent",
                {
                    "bench_mode": "rows",
                    "bench_rows": [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
                    "repeat_first_bench_to_daylight": True,
                    "daylight_mode": "terrain",
                    "daylight_max_width": 80.0,
                },
            ),
        ],
    },
}


NEW_ASSEMBLY_SOURCE_KEY = "__new_assembly_create__"
NEW_ASSEMBLY_SOURCE_LABEL = "New Assembly Create"


def assembly_preset_names() -> list[str]:
    """Return available Assembly/Subassembly preset names."""

    return list(ASSEMBLY_PRESETS.keys())
