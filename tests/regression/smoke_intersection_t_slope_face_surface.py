# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
T intersection smoke test: the parametric intersection kernel's surfaces in a full Build Parametric.

Since plan phase R7c (V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md) every intersection is built by
the kernel. This builds the starter T from its preset and checks, on the document objects:
the intersection surface and its side slope are ready and have no skinny triangle, every boundary
vertex but the mouths has a side slope, no corridor triangle lies inside the intersection, and at
every leg mouth the corridor surface and the intersection share their vertices.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_intersection_t_slope_face_surface.py', 'r', encoding='utf-8').read())"
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

PRESET = "T Intersection - Basic"
EXPECTED_MOUTHS = {"alignment:intersection-primary": (103.0, 137.0), "alignment:intersection-secondary": (83.0,)}


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


def check_kernel_intersection(doc, label):
    """The checks every intersection smoke runs on a built document; returns a summary."""

    rows = {row["role"]: row for row in corridor_build_review_rows(doc)}
    for role in ("intersection", "intersection_slope"):
        _assert(role in rows and rows[role]["status"] == "ready", f"{label}: {role} row should be ready: {rows.get(role)}")
        _assert("skinny=0" in rows[role]["notes"], f"{label}: {role} should have no skinny triangle: {rows[role]['notes']}")
    _assert("intersection_tie_slope" not in rows, f"{label}: the kernel builds no tie slope surface.")
    for role in ("design", "daylight"):
        _assert(rows.get(role, {}).get("status") == "ready", f"{label}: {role} surface should be ready.")

    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    result = _intersection_kernel_result(doc, applied)
    _assert(result is not None and result.status == "ready", f"{label}: kernel status {getattr(result, 'status', None)}")
    quality = dict(result.quality_rows)
    _assert(quality.get("slope_vertex_without_daylight_count") == 0.0, f"{label}: side slope missing daylight points.")

    boundary = [(p[0], p[1]) for p in result.boundary_xyz]
    holes = [[(p[0], p[1]) for p in hole] for hole in result.boundary_holes_xyz]
    for name in ("V1CorridorDesignSurfacePreview", "V1CorridorDaylightSurfacePreview"):
        obj = doc.getObject(name)
        inside = 0
        for facet in obj.Mesh.Facets:
            c = [sum(p[k] for p in facet.Points) / 3.0 for k in (0, 1)]
            if _inside(c, boundary) and not any(_inside(c, hole) for hole in holes):
                inside += 1
        _assert(inside == 0, f"{label}: {inside} {name} triangles lie inside the intersection.")

    design = {(round(p.x, 4), round(p.y, 4)) for p in doc.getObject("V1CorridorDesignSurfacePreview").Mesh.Points}
    mouths = {}
    for leg in result.legs:
        if leg.mouth_station is None:
            continue
        mouths.setdefault(leg.road_ref, []).append(round(leg.mouth_station, 3))
        for point in (leg.mouth_left_xyz, leg.mouth_right_xyz):
            _assert((round(point[0], 4), round(point[1], 4)) in design, f"{label}: corridor and intersection do not share {leg.leg_id}'s mouth edge {point}.")
    return {"mouths": {k: sorted(v) for k, v in mouths.items()}, "patch_triangles": int(quality.get("patch_triangle_count", 0)), "slope_triangles": int(quality.get("slope_triangle_count", 0))}


def build_preset(label):
    doc = App.newDocument("CRV1KernelSmoke")
    create_intersection_preset_sources(doc, preset_label=label)
    project = find_project(doc)
    applied = build_document_applied_section_set(doc, project=project)
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
    apply_v1_corridor_model(document=doc, project=project)
    return doc


def run():
    doc = build_preset(PRESET)
    try:
        summary = check_kernel_intersection(doc, PRESET)
        for road, stations in EXPECTED_MOUTHS.items():
            _assert(tuple(summary["mouths"].get(road, ())) == stations, f"{PRESET}: mouth stations {summary['mouths']}")
    finally:
        App.closeDocument(doc.Name)
    print("[PASS] T intersection kernel surface smoke completed: " + str(summary))


if __name__ == "__main__":
    run()
