import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    apply_v1_corridor_model,
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_build_review_rows,
    document_has_v1_applied_sections,
    preferred_corridor_build_review_row_index,
    show_corridor_build_review_object,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_corridor import find_v1_corridor_model
from freecad.Corridor_Road.v1.objects.obj_surface import find_v1_surface_model


def _new_project_doc():
    doc = App.newDocument("V1BuildCorridorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _sample_sections() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_sections_with_centerline_curve() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:curved",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
            AppliedSectionStationRow("station:40", 40.0, "section:40"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=4.0, z=11.0, tangent_direction_deg=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:40",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=40.0,
                frame=AppliedSectionFrame(station=40.0, x=40.0, y=0.0, z=12.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_sections_with_ditch_points() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:ditch",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 0.0, -5.2, 9.8, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 0.0, -4.0, 10.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 0.0, 5.0, 10.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 0.0, 6.2, 9.8, "ditch_surface", 6.2),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 20.0, -5.2, 10.8, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 20.0, -4.0, 11.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 20.0, 5.0, 11.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 20.0, 6.2, 10.8, "ditch_surface", 6.2),
                ],
            ),
        ],
    )


def test_build_document_corridor_model_uses_applied_sections() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        result = build_document_corridor_model(doc, project=project)

        assert document_has_v1_applied_sections(doc) is True
        assert result.corridor_id == "corridor:main"
        assert result.applied_section_set_ref == "sections:main"
        assert [row.station for row in result.station_rows] == [0.0, 20.0]
    finally:
        App.closeDocument(doc.Name)


def test_build_document_corridor_surface_model_uses_corridor_and_applied_sections() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        corridor = build_document_corridor_model(doc, project=project)

        result = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor)

        assert result.corridor_id == "corridor:main"
        assert result.surface_model_id == "surface:main"
        assert [row.surface_kind for row in result.surface_rows] == [
            "design_surface",
            "subgrade_surface",
            "daylight_surface",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_creates_result_object() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        obj = apply_v1_corridor_model(document=doc, project=project)

        assert obj == find_v1_corridor_model(doc)
        assert obj.V1ObjectType == "V1CorridorModel"
        assert obj.StationCount == 2
        assert list(obj.SurfaceBuildRefs) == ["surface:main"]
        surface_obj = find_v1_surface_model(doc)
        assert surface_obj is not None
        assert surface_obj.V1ObjectType == "V1SurfaceModel"
        assert surface_obj.SurfaceCount == 3
        preview = doc.getObject("V1CorridorDesignSurfacePreview")
        assert preview is not None
        assert preview.CRRecordKind == "v1_corridor_surface_preview"
        assert int(preview.VertexCount) == 4
        assert int(preview.TriangleCount) == 2
        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is not None
        assert centerline.CRRecordKind == "v1_corridor_centerline_preview"
        assert centerline.V1ObjectType == "V1CorridorCenterlinePreview"
        assert centerline.DisplayCurveKind == "line"
        assert int(centerline.PointCount) == 2
        subgrade_preview = doc.getObject("V1CorridorSubgradeSurfacePreview")
        assert subgrade_preview is not None
        assert subgrade_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert int(subgrade_preview.VertexCount) == 4
        assert int(subgrade_preview.TriangleCount) == 2
        daylight_preview = doc.getObject("V1CorridorDaylightSurfacePreview")
        assert daylight_preview is not None
        assert daylight_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert int(daylight_preview.VertexCount) == 8
        assert int(daylight_preview.TriangleCount) == 4
        assert int(daylight_preview.EGIntersectionCount) == 0
        assert int(daylight_preview.EGTieInHitCount) == 0
        assert int(daylight_preview.SlopeFaceFallbackCount) == 4
        assert int(daylight_preview.SlopeFaceNoExistingGroundCount) == 4
        assert int(daylight_preview.SlopeFaceNoEGHitCount) == 0
        assert "fallbacks: 4" in daylight_preview.SlopeFaceDiagnosticSummary
        assert "no EG TIN: 4" in daylight_preview.SlopeFaceDiagnosticSummary
        fallback_markers = doc.getObject("ReviewIssueSlopeFaceFallbackMarkers")
        assert fallback_markers is not None
        assert fallback_markers.V1ObjectType == "ReviewIssue"
        assert fallback_markers.IssueKind == "slope_face_tie_in"
        assert int(fallback_markers.MarkerCount) == 4
    finally:
        App.closeDocument(doc.Name)


def test_corridor_build_review_rows_summarize_preview_outputs() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        missing_rows = corridor_build_review_rows(doc)
        assert [row["status"] for row in missing_rows] == ["missing", "missing", "missing", "missing", "missing"]

        apply_v1_corridor_model(document=doc, project=project)
        rows = corridor_build_review_rows(doc)

        assert [row["role"] for row in rows] == ["centerline", "design", "subgrade", "daylight", "drainage"]
        assert [row["status"] for row in rows] == ["ready", "ready", "ready", "ready", "missing"]
        assert rows[0]["triangle_or_point_count"] == 2
        assert rows[1]["vertex_count"] == 4
        assert rows[1]["triangle_or_point_count"] == 2
        assert "fallbacks: 4" in str(rows[3]["notes"])
        assert "no EG TIN: 4" in str(rows[3]["notes"])
        assert preferred_corridor_build_review_row_index(rows) == 1

        shown = show_corridor_build_review_object(doc, 1)
        assert shown.Name == "V1CorridorDesignSurfacePreview"
    finally:
        App.closeDocument(doc.Name)


def test_preferred_corridor_build_review_row_index_prefers_ready_design_surface() -> None:
    rows = [
        {"role": "centerline", "status": "ready"},
        {"role": "design", "status": "ready"},
        {"role": "subgrade", "status": "ready"},
    ]

    assert preferred_corridor_build_review_row_index(rows) == 1
    assert preferred_corridor_build_review_row_index(rows, preferred_role="subgrade") == 2
    assert preferred_corridor_build_review_row_index([{"role": "design", "status": "missing"}]) is None


def test_apply_v1_corridor_model_creates_drainage_surface_when_ditch_points_exist() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        apply_v1_corridor_model(document=doc, project=project)

        surface_obj = find_v1_surface_model(doc)
        assert surface_obj is not None
        assert list(surface_obj.SurfaceKinds) == [
            "design_surface",
            "subgrade_surface",
            "daylight_surface",
            "drainage_surface",
        ]
        drainage_preview = doc.getObject("V1CorridorDrainageSurfacePreview")
        assert drainage_preview is not None
        assert drainage_preview.CRRecordKind == "v1_corridor_surface_preview"
        assert drainage_preview.SurfaceRole == "drainage"
        assert drainage_preview.SurfaceKind == "drainage_surface"
        assert int(drainage_preview.VertexCount) == 8
        assert int(drainage_preview.TriangleCount) == 6
        rows = corridor_build_review_rows(doc)
        assert rows[4]["status"] == "ready"
        assert rows[4]["vertex_count"] == 8
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_corridor_model_creates_spline_centerline_preview() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_centerline_curve())

        apply_v1_corridor_model(document=doc, project=project)

        centerline = doc.getObject("V1CorridorCenterline3DPreview")
        assert centerline is not None
        assert centerline.DisplayCurveKind == "spline"
        assert int(centerline.PointCount) == 3
        shape = centerline.Shape
        assert len(shape.Edges) == 1
        assert "BSpline" in type(shape.Edges[0].Curve).__name__
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 build corridor command contract tests completed.")
