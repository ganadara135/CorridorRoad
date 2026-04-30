import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    V1BuildCorridorTaskPanel,
    apply_v1_corridor_model,
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_applied_sections_review_summary,
    corridor_build_guided_review_steps,
    corridor_build_review_rows,
    corridor_build_review_row_color,
    corridor_centerline_preview_style,
    corridor_drainage_review_rows,
    corridor_drainage_review_summary,
    corridor_slope_face_issue_rows,
    document_has_v1_applied_sections,
    focus_adjacent_corridor_slope_face_issue,
    focus_corridor_build_guided_review_step,
    focus_corridor_drainage_review_row,
    focus_corridor_slope_face_issue,
    preferred_corridor_build_review_row_index,
    set_all_corridor_build_preview_visibility,
    set_corridor_build_preview_visibility,
    show_corridor_build_review_object,
    show_corridor_slope_face_issue_marker,
)
from freecad.Corridor_Road.v1.services.mapping.tin_mesh_preview_mapper import tin_mesh_preview_style
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_corridor import find_v1_corridor_model
from freecad.Corridor_Road.v1.objects.obj_surface import find_v1_surface_model

_QAPP = None


def _new_project_doc():
    doc = App.newDocument("V1BuildCorridorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


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
        progress_events = []

        obj = apply_v1_corridor_model(
            document=doc,
            project=project,
            progress_callback=lambda value, text: progress_events.append((value, text)),
        )

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
        assert "STA 0.000 L no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert "STA 20.000 R no EG TIN" in daylight_preview.SlopeFaceIssueStations
        assert len(list(daylight_preview.SlopeFaceIssueRows)) == 4
        issue_rows = corridor_slope_face_issue_rows(doc)
        assert issue_rows[0]["station_label"] == "STA 0.000"
        assert issue_rows[0]["side"] == "L"
        assert issue_rows[0]["reason"] == "no EG TIN"
        assert issue_rows[0]["marker_object"] == "ReviewIssueSlopeFaceIssue001L"
        assert issue_rows[-1]["station_label"] == "STA 20.000"
        assert issue_rows[-1]["side"] == "R"
        fallback_markers = doc.getObject("ReviewIssueSlopeFaceFallbackMarkers")
        assert fallback_markers is not None
        assert fallback_markers.V1ObjectType == "ReviewIssue"
        assert fallback_markers.IssueKind == "slope_face_tie_in"
        assert int(fallback_markers.MarkerCount) == 4
        first_issue_marker = doc.getObject("ReviewIssueSlopeFaceIssue001L")
        assert first_issue_marker is not None
        assert first_issue_marker.V1ObjectType == "ReviewIssue"
        assert first_issue_marker.IssueStation == "STA 0.000"
        assert first_issue_marker.IssueSide == "L"
        assert first_issue_marker.IssueReason == "no EG TIN"
        assert int(first_issue_marker.MarkerCount) == 1
        shown_marker = show_corridor_slope_face_issue_marker(doc, 0)
        assert shown_marker.Name == "ReviewIssueSlopeFaceIssue001L"
        assert progress_events[0] == (40, "Preparing project tree...")
        assert any(text == "Building corridor surfaces..." for _value, text in progress_events)
        assert progress_events[-1] == (94, "Recomputing document...")
    finally:
        App.closeDocument(doc.Name)


def test_build_corridor_panel_shows_progress_bar() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1BuildCorridorTaskPanel(document=doc)
        progress_bars = panel.form.findChildren(QtWidgets.QProgressBar)

        assert len(progress_bars) == 1
        assert progress_bars[0].value() == 0
        assert progress_bars[0].format() == "Ready"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_build_review_rows_summarize_preview_outputs() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        missing_rows = corridor_build_review_rows(doc)
        assert [row["status"] for row in missing_rows] == ["missing", "missing", "missing", "missing", "missing"]
        assert "2 STA" in str(missing_rows[0]["applied_section_summary"])
        assert missing_rows[0]["applied_section_diagnostics"] == "ok"

        apply_v1_corridor_model(document=doc, project=project)
        rows = corridor_build_review_rows(doc)

        assert [row["role"] for row in rows] == ["centerline", "design", "subgrade", "daylight", "drainage"]
        assert [row["status"] for row in rows] == ["ready", "ready", "ready", "ready", "missing"]
        assert rows[0]["triangle_or_point_count"] == 2
        assert rows[1]["vertex_count"] == 4
        assert rows[1]["triangle_or_point_count"] == 2
        assert "2 STA" in str(rows[1]["applied_section_summary"])
        assert rows[1]["applied_section_diagnostics"] == "ok"
        assert "fallbacks: 4" in str(rows[3]["notes"])
        assert "no EG TIN: 4" in str(rows[3]["notes"])
        assert "STA 0.000 L no EG TIN" in str(rows[3]["notes"])
        assert "STA 20.000 R no EG TIN" in str(rows[3]["notes"])
        assert preferred_corridor_build_review_row_index(rows) == 1

        shown = show_corridor_build_review_object(doc, 1)
        assert shown.Name == "V1CorridorDesignSurfacePreview"
    finally:
        App.closeDocument(doc.Name)


def test_corridor_applied_sections_review_summary_tracks_source_context() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        summary = corridor_applied_sections_review_summary(doc)

        assert summary["status"] == "ok"
        assert summary["station_count"] == 2
        assert summary["diagnostic_count"] == 0
        assert summary["ditch_point_count"] == 8
        assert summary["slope_face_count"] == 0
        assert summary["structure_count"] == 0
        assert "2 STA" in summary["summary"]
        assert "structures:0" in summary["summary"]
        assert "ditch_pts:8" in summary["summary"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_applied_sections_review_summary_tracks_singular_structure_owner() -> None:
    doc, project = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-1",
            applied_section_set_id="sections:structure",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
            station_rows=[AppliedSectionStationRow("station:10", 10.0, "section:10")],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="section:10",
                    corridor_id="corridor:main",
                    station=10.0,
                    active_structure_ids=["structure:bridge-01", "structure:wall-ignored"],
                    component_rows=[
                        AppliedSectionComponentRow(
                            component_id="lane-1",
                            kind="lane",
                            structure_ids=["structure:bridge-01"],
                        )
                    ],
                )
            ],
        )
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=applied)

        summary = corridor_applied_sections_review_summary(doc)

        assert summary["structure_count"] == 1
        assert summary["structure_refs"] == ["structure:bridge-01"]
        assert "structures:1" in summary["summary"]
    finally:
        App.closeDocument(doc.Name)


def test_corridor_drainage_review_rows_track_ditch_surface_points() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_ditch_points())

        rows = corridor_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)

        assert [row["status"] for row in rows] == ["ready", "ready"]
        assert rows[0]["station"] == 0.0
        assert rows[0]["ditch_point_count"] == 4
        assert rows[0]["left_count"] == 2
        assert rows[0]["right_count"] == 2
        assert rows[0]["marker_object"] == "ReviewIssueDrainageStation001"
        assert rows[0]["x"] == "0.000000"
        assert rows[0]["y"] == "0.500000"
        assert rows[0]["z"] == "9.900000"
        assert summary["status"] == "ready"
        assert summary["ditch_point_count"] == 8
        assert summary["missing_count"] == 0
        marker = focus_corridor_drainage_review_row(doc, 0)
        assert marker.Name == "ReviewIssueDrainageStation001"
        assert marker.V1ObjectType == "ReviewIssue"
        assert marker.IssueKind == "drainage_diagnostic"
        assert marker.IssueStation == "0.000"
        assert marker.IssueStatus == "ready"
        assert int(marker.MarkerCount) == 1
    finally:
        App.closeDocument(doc.Name)


def test_corridor_drainage_review_rows_explain_missing_ditch_points() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())

        rows = corridor_drainage_review_rows(doc)
        summary = corridor_drainage_review_summary(doc)
        steps = corridor_build_guided_review_steps(doc)

        assert [row["status"] for row in rows] == ["missing", "missing"]
        assert "No ditch_surface" in str(rows[0]["notes"])
        assert summary["status"] == "missing"
        assert summary["missing_count"] == 2
        assert steps[3]["step_id"] == "drainage"
        assert steps[3]["status"] == "missing"
        assert "without ditch_surface" in str(steps[3]["notes"])
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


def test_corridor_build_review_row_colors_are_dark_theme_readable() -> None:
    assert corridor_build_review_row_color("ready") == (220, 245, 224)
    assert corridor_build_review_row_color("missing") == (238, 238, 238)
    assert corridor_build_review_row_color("empty") == (255, 241, 205)
    assert corridor_build_review_row_color("unknown") is None


def test_corridor_preview_styles_are_role_specific() -> None:
    design = tin_mesh_preview_style("design")
    subgrade = tin_mesh_preview_style("subgrade")
    daylight = tin_mesh_preview_style("daylight")
    drainage = tin_mesh_preview_style("drainage")
    base = tin_mesh_preview_style("unknown")

    assert design["shape_color"] == (1.00, 0.56, 0.12)
    assert subgrade["transparency"] > design["transparency"]
    assert daylight["shape_color"] != design["shape_color"]
    assert drainage["line_width"] > daylight["line_width"]
    assert base == tin_mesh_preview_style("base")
    assert corridor_centerline_preview_style()["line_width"] == 5.0


def test_corridor_preview_visibility_helpers_target_roles_and_markers() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = True

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.Objects = [
                FakeObject("V1CorridorCenterline3DPreview"),
                FakeObject("V1CorridorDesignSurfacePreview"),
                FakeObject("V1CorridorSubgradeSurfacePreview"),
                FakeObject("V1CorridorDaylightSurfacePreview"),
                FakeObject("ReviewIssueSlopeFaceIssue001L"),
                FakeObject("ReviewIssueDrainageStation001"),
            ]

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    design = set_corridor_build_preview_visibility(doc, "design", False)
    assert design.Name == "V1CorridorDesignSurfacePreview"
    assert design.ViewObject.Visibility is False
    assert set_corridor_build_preview_visibility(doc, "drainage", False) is None

    changed = set_all_corridor_build_preview_visibility(doc, True, include_issue_markers=True)
    assert changed == 6
    assert all(obj.ViewObject.Visibility is True for obj in doc.Objects)


def test_corridor_guided_review_steps_and_focus_isolate_layers() -> None:
    class FakeView:
        def __init__(self):
            self.Visibility = True

    class FakeObject:
        def __init__(self, name):
            self.Name = name
            self.Label = name
            self.VertexCount = 4
            self.TriangleCount = 2
            self.PointCount = 2
            self.DisplayCurveKind = "line"
            self.ViewObject = FakeView()

    class FakeDocument:
        def __init__(self):
            self.Objects = [
                FakeObject("V1CorridorCenterline3DPreview"),
                FakeObject("V1CorridorDesignSurfacePreview"),
                FakeObject("V1CorridorSubgradeSurfacePreview"),
                FakeObject("V1CorridorDaylightSurfacePreview"),
                FakeObject("ReviewIssueSlopeFaceIssue001L"),
                FakeObject("ReviewIssueSlopeFaceIssue002R"),
            ]
            daylight = self.getObject("V1CorridorDaylightSurfacePreview")
            daylight.SlopeFaceIssueRows = [
                "station_label=STA 0.000;station_index=0;side=L;reason=no EG TIN;status=fallback:no_existing_ground_tin;marker_object=ReviewIssueSlopeFaceIssue001L",
                "station_label=STA 20.000;station_index=1;side=R;reason=no EG TIN;status=fallback:no_existing_ground_tin;marker_object=ReviewIssueSlopeFaceIssue002R",
            ]
            for obj in self.Objects:
                if obj.Name.startswith("V1Corridor"):
                    obj.CRRecordKind = "v1_corridor_surface_preview"
                if obj.Name == "V1CorridorCenterline3DPreview":
                    obj.CRRecordKind = "v1_corridor_centerline_preview"

        def getObject(self, name):
            for obj in self.Objects:
                if obj.Name == name:
                    return obj
            return None

    doc = FakeDocument()

    steps = corridor_build_guided_review_steps(doc)
    assert [step["step_id"] for step in steps] == ["centerline", "design", "slope_issues", "drainage"]
    assert steps[2]["status"] == "warn"
    assert steps[2]["focus"] == "First issue marker"

    focused = focus_corridor_build_guided_review_step(doc, "design")
    assert focused.Name == "V1CorridorDesignSurfacePreview"
    assert doc.getObject("V1CorridorCenterline3DPreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is False

    focused = focus_corridor_build_guided_review_step(doc, "slope_issues")
    assert focused.Name == "ReviewIssueSlopeFaceIssue001L"
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True
    assert doc.getObject("ReviewIssueSlopeFaceIssue001L").ViewObject.Visibility is True

    focused = focus_corridor_slope_face_issue(doc, 1)
    assert focused.Name == "ReviewIssueSlopeFaceIssue002R"
    assert doc.getObject("V1CorridorDesignSurfacePreview").ViewObject.Visibility is False
    assert doc.getObject("V1CorridorDaylightSurfacePreview").ViewObject.Visibility is True

    index, focused = focus_adjacent_corridor_slope_face_issue(doc, current_index=1, direction=1)
    assert index == 0
    assert focused.Name == "ReviewIssueSlopeFaceIssue001L"

    index, focused = focus_adjacent_corridor_slope_face_issue(doc, current_index=0, direction=-1)
    assert index == 1
    assert focused.Name == "ReviewIssueSlopeFaceIssue002R"


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
