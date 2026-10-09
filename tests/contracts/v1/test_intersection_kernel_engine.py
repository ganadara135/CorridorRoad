"""Build Parametric builds every intersection with the parametric kernel (plan phases R7a, R7c).

Applied Sections gain a section at each leg mouth, the corridor's design and slope surfaces lose
each road's triangles between its mouths, and the kernel's patch and side slope take their place.
Checked on the starter T, Cross and roundabout: the corridor and the kernel neither overlap nor
leave a gap; at every mouth they share their vertices.
"""

import math

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands import cmd_build_corridor as build
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set

from test_intersection_policy_family_review import _reviewed_model, _store

LABELS = ["T Intersection - Basic", "Cross Intersection - Basic", "Roundabout - Single Lane"]


def _kernel_build(label):
    doc = App.newDocument("CRV1KernelEngine")
    _store(doc, _reviewed_model(doc, label))
    project = find_project(doc)
    applied = build_document_applied_section_set(doc, project=project)
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
    corridor = build.build_document_corridor_model(doc, project=project)
    surfaces = build.build_document_corridor_surface_model(doc, project=project, corridor_model=corridor)
    kwargs = dict(document=doc, project=project, corridor_model=corridor, surface_model=surfaces)
    build.create_corridor_design_surface_preview(**kwargs)
    build.create_corridor_intersection_surface_preview(**kwargs)
    build.create_corridor_daylight_surface_preview(**kwargs)
    result = build._intersection_kernel_result(doc, to_applied_section_set(find_v1_applied_section_set(doc)))
    return doc, result


def _mesh_points_m(obj):
    # the TIN preview meshes carry the TIN's own coordinates, metres (TINMeshPreviewMapper)
    return [(p.x, p.y, p.z) for p in obj.Mesh.Points]


def _facet_centroids_m(obj):
    return [tuple(sum(c) / 3.0 for c in zip(*[(p[0], p[1], p[2]) for p in facet.Points])) for facet in obj.Mesh.Facets]


def _inside(point, polygon):
    x, y = point[0], point[1]
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if (a[1] > y) != (b[1] > y) and a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > x:
            inside = not inside
    return inside


@pytest.fixture(params=LABELS)
def kernel_doc(request):
    doc, result = _kernel_build(request.param)
    try:
        yield doc, result
    finally:
        App.closeDocument(doc.Name)


def test_the_applied_sections_have_a_section_at_every_mouth(kernel_doc) -> None:
    doc, result = kernel_doc
    assert result.status == "ready", result.diagnostics
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    for road, station in result.supplemental_stations:
        assert any(s.alignment_id == road and abs(s.station - station) < 1.0e-6 for s in applied.sections), (road, station)
    kinds = {row.kind for row in applied.station_rows}
    assert "intersection_supplemental" in kinds


def test_the_kernel_surfaces_replace_the_legacy_ones(kernel_doc) -> None:
    doc, result = kernel_doc
    patch = doc.getObject("V1CorridorIntersectionSurfacePreview")
    slope = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
    assert patch.IntersectionKernelStatus == "ready"
    assert patch.Mesh.CountFacets == len(result.patch_triangles)
    assert slope.Mesh.CountFacets == len(result.slope_triangles)
    assert doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview") is None
    assert doc.getObject("V1CorridorIntersectionExclusionZonePreview") is None
    # both surfaces go to the project tree's Intersections folder
    folder = doc.getObject("CRV1_Intersections")
    assert folder is not None and patch in folder.Group and slope in folder.Group


def test_no_corridor_triangle_lies_inside_the_patch(kernel_doc) -> None:
    doc, result = kernel_doc
    boundary = [(p[0], p[1]) for p in result.boundary_xyz]
    holes = [[(p[0], p[1]) for p in hole] for hole in result.boundary_holes_xyz]
    for name in ("V1CorridorDesignSurfacePreview", "V1CorridorDaylightSurfacePreview"):
        inside = [
            c for c in _facet_centroids_m(doc.getObject(name))
            if _inside(c, boundary) and not any(_inside(c, hole) for hole in holes)
        ]
        assert not inside, (name, inside[:3])


def test_at_every_mouth_the_corridor_and_the_kernel_share_their_vertices(kernel_doc) -> None:
    doc, result = kernel_doc
    design = {(round(x, 4), round(y, 4)): z for x, y, z in _mesh_points_m(doc.getObject("V1CorridorDesignSurfacePreview"))}
    daylight = {(round(x, 4), round(y, 4)): z for x, y, z in _mesh_points_m(doc.getObject("V1CorridorDaylightSurfacePreview"))}
    for leg in result.legs:
        if leg.mouth_station is None:
            continue
        for point in (leg.mouth_left_xyz, leg.mouth_right_xyz):
            key = (round(point[0], 4), round(point[1], 4))
            assert key in design, (leg.leg_id, point)
            assert design[key] == pytest.approx(point[2], abs=1.0e-4)
    # the slope strip's outer corners at the mouths are the corridor slope surface's daylight points
    slope = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
    slope_points = {(round(x, 4), round(y, 4)) for x, y, _z in _mesh_points_m(slope)}
    shared = slope_points & set(daylight)
    assert len(shared) >= 2 * sum(1 for leg in result.legs if leg.mouth_station is not None)


def test_a_kernel_document_survives_save_and_reopen(tmp_path) -> None:
    doc, _result = _kernel_build("T Intersection - Basic")
    path = str(tmp_path / "kernel_t.FCStd")
    try:
        doc.saveAs(path)
    finally:
        App.closeDocument(doc.Name)
    reopened = App.openDocument(path)
    try:
        patch = reopened.getObject("V1CorridorIntersectionSurfacePreview")
        assert patch is not None and patch.IntersectionKernelStatus == "ready" and patch.Mesh.CountFacets > 0
        assert not math.isnan(patch.Mesh.BoundBox.XLength)
    finally:
        App.closeDocument(reopened.Name)


@pytest.mark.parametrize("label", LABELS)
def test_the_full_build_reports_the_kernel_surfaces_and_no_warning(label) -> None:
    doc = App.newDocument("CRV1KernelEngineFull")
    try:
        _store(doc, _reviewed_model(doc, label))
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        build.apply_v1_corridor_model(document=doc, project=project)
        rows = {row["role"]: row for row in build.corridor_build_review_rows(doc)}
        assert "intersection_tie_slope" not in rows
        for role in ("intersection", "intersection_slope"):
            assert rows[role]["status"] == "ready" and rows[role]["notes"].startswith("Built by the intersection kernel"), rows[role]
            assert "skinny=0" in rows[role]["notes"]
        for role in ("design", "subgrade", "daylight"):
            assert rows[role]["status"] == "ready", (role, rows[role]["notes"][-400:])
    finally:
        App.closeDocument(doc.Name)
