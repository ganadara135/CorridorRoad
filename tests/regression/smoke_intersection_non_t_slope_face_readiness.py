# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Cross and roundabout smoke test: the parametric intersection kernel's surfaces in a full Build
Parametric.

The same checks as the T smoke (smoke_intersection_t_slope_face_surface.py), on the starter Cross
and the starter roundabout; the roundabout's central island is a hole in its intersection surface.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_intersection_non_t_slope_face_readiness.py', 'r', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    _intersection_kernel_result,
    apply_v1_corridor_model,
    corridor_build_review_rows,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import create_intersection_preset_sources
from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set

NON_T_PRESETS = {
    "Cross Intersection - Basic": {"legs": 4, "holes": 0},
    "Roundabout - Single Lane": {"legs": 4, "holes": 1},
}


def _assert(condition, message):
    if not condition:
        raise Exception(message)


def _inside(point, polygon):
    x, y = point[0], point[1]
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if (a[1] > y) != (b[1] > y) and a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > x:
            inside = not inside
    return inside


def _run_one_preset(label, expected):
    doc = App.newDocument("CRV1KernelSmoke")
    try:
        create_intersection_preset_sources(doc, preset_label=label)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        apply_v1_corridor_model(document=doc, project=project)

        rows = {row["role"]: row for row in corridor_build_review_rows(doc)}
        for role in ("intersection", "intersection_slope", "design", "daylight"):
            _assert(rows.get(role, {}).get("status") == "ready", f"{label}: {role} row should be ready: {rows.get(role)}")
        for role in ("intersection", "intersection_slope"):
            _assert("skinny=0" in rows[role]["notes"], f"{label}: {role} should have no skinny triangle: {rows[role]['notes']}")

        result = _intersection_kernel_result(doc, to_applied_section_set(find_v1_applied_section_set(doc)))
        _assert(result is not None and result.status == "ready", f"{label}: kernel status {getattr(result, 'status', None)}")
        _assert(sum(1 for leg in result.legs if leg.enabled) == expected["legs"], f"{label}: legs {result.legs}")
        _assert(len(result.boundary_holes_xyz) == expected["holes"], f"{label}: holes {len(result.boundary_holes_xyz)}")
        quality = dict(result.quality_rows)
        _assert(quality.get("slope_vertex_without_daylight_count") == 0.0, f"{label}: side slope missing daylight points.")

        boundary = [(p[0], p[1]) for p in result.boundary_xyz]
        holes = [[(p[0], p[1]) for p in hole] for hole in result.boundary_holes_xyz]
        for name in ("V1CorridorDesignSurfacePreview", "V1CorridorDaylightSurfacePreview"):
            inside = 0
            for facet in doc.getObject(name).Mesh.Facets:
                c = [sum(p[k] for p in facet.Points) / 3.0 for k in (0, 1)]
                if _inside(c, boundary) and not any(_inside(c, hole) for hole in holes):
                    inside += 1
            _assert(inside == 0, f"{label}: {inside} {name} triangles lie inside the intersection.")

        design = {(round(p.x, 4), round(p.y, 4)) for p in doc.getObject("V1CorridorDesignSurfacePreview").Mesh.Points}
        for leg in result.legs:
            if leg.mouth_station is None:
                continue
            for point in (leg.mouth_left_xyz, leg.mouth_right_xyz):
                _assert((round(point[0], 4), round(point[1], 4)) in design, f"{label}: no shared mouth edge {point} for {leg.leg_id}.")
        return {"patch_triangles": int(quality.get("patch_triangle_count", 0)), "slope_triangles": int(quality.get("slope_triangle_count", 0))}
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


def run():
    outcomes = {label: _run_one_preset(label, expected) for label, expected in NON_T_PRESETS.items()}
    print("[PASS] Non-T intersection kernel surface smoke completed: " + str(outcomes))


if __name__ == "__main__":
    run()
