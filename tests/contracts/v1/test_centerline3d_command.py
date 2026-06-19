import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups, corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.objects.obj_project import V1_TREE_CENTERLINE3D, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import (
    CENTERLINE3D_COMMAND_ID,
    CmdV1Centerline3D,
    V1Centerline3DTaskPanel,
    build_document_centerline3d_result,
    _centerline3d_horizontal_source_point,
    _centerline3d_horizontal_interval_mode,
    _centerline3d_source_interval_stations,
    _centerline3d_source_shape_kind,
    _centerline3d_source_interval_row_text,
    _make_centerline3d_curve_shape,
    _make_source_interval_curve_shape,
    _normalized_display_mode,
    show_v1_centerline3d_preview_object,
    show_v1_centerline3d_station_markers,
)
from freecad.Corridor_Road.v1.models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from freecad.Corridor_Road.v1.models.source import AlignmentModel, ProfileModel
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, VerticalCurveRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.services.evaluation import Centerline3DEvaluationRequest, Centerline3DEvaluationService, Centerline3DFrameService


def _new_project_doc():
    doc = App.newDocument("V1Centerline3DCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _ensure_qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_centerline3d_display_mode_normalization_supports_three_modes() -> None:
    assert _normalized_display_mode("Source Geometry") == "source_geometry"
    assert _normalized_display_mode("B-spline") == "bspline"
    assert _normalized_display_mode("Smooth Curve") == "bspline"
    assert _normalized_display_mode("Polyline") == "polyline"
    assert _normalized_display_mode("") == "source_geometry"


def test_centerline3d_result_samples_alignment_profile_stationing() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        result = build_document_centerline3d_result(doc)

        assert result.status == "ready"
        assert result.point_count >= 2
        assert result.alignment_id == alignment.AlignmentId
        assert result.profile_id == profile.ProfileId
        assert result.stationing_id.startswith("stationing:")
        assert result.station_start == min(row.station for row in result.point_rows)
        assert result.elevation_max >= result.elevation_min
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_preview_object_routes_under_alignment_profile_centerline_group() -> None:
    doc, project, tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)

        result = build_document_centerline3d_result(doc)
        preview = show_v1_centerline3d_preview_object(doc, result=result, project=project)

        assert preview.Name == "V1Centerline3DPreview"
        assert str(preview.Label).startswith("3D Centerline")
        assert preview.CRRecordKind == "v1_centerline3d_review"
        assert preview.V1ObjectType == "V1Centerline3DReview"
        assert preview.CurveKind == "source_geometry"
        assert preview.CenterlineDisplayMode == "source_geometry"
        assert preview.SourceGeometryStatus == "ready"
        assert "Source Geometry built" in preview.SourceGeometryMessage
        assert preview.SourceGeometryIntervalCount >= 1
        assert preview.SourceGeometryLineIntervalCount >= 1
        assert preview.SourceGeometryArcFitIntervalCount >= 1
        assert preview.SourceGeometryPartArcIntervalCount + preview.SourceGeometryArcFit3DSampledIntervalCount == preview.SourceGeometryArcFitIntervalCount
        assert preview.SourceGeometryArcFitRejectedIntervalCount == 0
        assert preview.SourceGeometryArcFitAbsoluteTolerance > 0.0
        assert preview.SourceGeometryArcFitRelativeTolerance > 0.0
        assert preview.SourceGeometrySampleSpacing > 0.0
        assert len(list(preview.SourceGeometryIntervalRows)) == preview.SourceGeometryIntervalCount
        assert any(str(row).startswith("line|") for row in list(preview.SourceGeometryIntervalRows))
        assert any(str(row).startswith("arc_fit|") for row in list(preview.SourceGeometryIntervalRows))
        assert all("|horizontal=" in str(row) for row in list(preview.SourceGeometryIntervalRows))
        assert all("|vertical=" in str(row) for row in list(preview.SourceGeometryIntervalRows))
        assert all("|shape=" in str(row) for row in list(preview.SourceGeometryIntervalRows))
        assert all("|reason=" in str(row) for row in list(preview.SourceGeometryIntervalRows))
        arc_rows = [str(row) for row in list(preview.SourceGeometryIntervalRows) if str(row).startswith("arc_fit|")]
        assert arc_rows
        assert all("|arc_radius=" in row for row in arc_rows)
        assert all("|arc_sweep_deg=" in row for row in arc_rows)
        assert all("|arc_radial_error=" in row for row in arc_rows)
        assert all("|arc_tolerance=" in row for row in arc_rows)
        assert all("|arc_fit_status=accepted" in row for row in arc_rows)
        assert preview.PointCount == result.point_count
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Name in {str(getattr(obj, "Name", "") or "") for obj in list(tree[V1_TREE_CENTERLINE3D].Group)}
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_smooth_curve_uses_display_smoothed_bspline() -> None:
    points = [
        App.Vector(0.0, 0.0, 0.0),
        App.Vector(10.0, 0.0, 8.0),
        App.Vector(20.0, 0.0, 6.0),
        App.Vector(30.0, 0.0, 9.0),
        App.Vector(40.0, 0.0, 7.5),
        App.Vector(50.0, 0.0, 7.0),
    ]

    shape, curve_kind = _make_centerline3d_curve_shape(points, display_mode="Smooth Curve")

    assert curve_kind == "bspline_smoothed"
    assert shape.BoundBox.XLength > 0.0
    assert shape.BoundBox.ZLength > 0.0


def test_centerline3d_source_geometry_uses_arc_fit_for_curve_elements() -> None:
    radius = 100.0
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:curve",
                "circular_curve",
                0.0,
                100.0,
                length=100.0,
                geometry_payload={
                    "x_values": [radius, radius / (2.0**0.5), 0.0],
                    "y_values": [0.0, radius / (2.0**0.5), radius],
                },
            )
        ],
    )

    x, y = _centerline3d_horizontal_source_point(alignment, Centerline3DEvaluationService()._alignment_service, 25.0)

    assert abs(x - radius * 0.9238795325) <= 1.0e-6
    assert abs(y - radius * 0.3826834324) <= 1.0e-6


def test_centerline3d_source_geometry_rejects_poor_arc_fit() -> None:
    radius = 100.0
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:bad-curve",
                "circular_curve",
                0.0,
                100.0,
                length=100.0,
                geometry_payload={
                    "x_values": [radius, radius / (2.0**0.5), 40.0, 0.0],
                    "y_values": [0.0, 120.0, 20.0, radius],
                },
            )
        ],
    )

    x, y = _centerline3d_horizontal_source_point(alignment, Centerline3DEvaluationService()._alignment_service, 50.0)

    assert abs(x - radius / (2.0**0.5)) > 1.0
    assert abs(y - radius / (2.0**0.5)) > 1.0
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 10.0),
            ProfileControlPoint("pvi:100", 100.0, 10.0),
        ],
    )
    row_text = _centerline3d_source_interval_row_text(alignment, profile, 0.0, 100.0, "sampled_curve", 101, shape_kind="sampled_curve")

    assert _centerline3d_horizontal_interval_mode(alignment, 0.0, 100.0) == "arc_fit_rejected"
    assert "|horizontal=arc_fit_rejected" in row_text
    assert "|arc_fit_status=rejected" in row_text
    assert "|reason=arc_fit_rejected_radial_error" in row_text


def test_centerline3d_source_geometry_uses_part_arc_when_z_is_constant() -> None:
    points = [
        App.Vector(100.0, 0.0, 10.0),
        App.Vector(70.710678, 70.710678, 10.0),
        App.Vector(0.0, 100.0, 10.0),
    ]

    shape_kind = _centerline3d_source_shape_kind("arc_fit", points)
    shape = _make_source_interval_curve_shape(points, shape_kind=shape_kind)

    assert shape_kind == "part_arc"
    assert shape.BoundBox.XLength > 0.0
    assert shape.BoundBox.YLength > 0.0
    assert shape.BoundBox.ZLength <= 1.0e-6


def test_centerline3d_source_geometry_curve_sampling_is_dense_and_unsmoothed() -> None:
    stations = _centerline3d_source_interval_stations(0.0, 48.0)
    coarse_stations = _centerline3d_source_interval_stations(0.0, 48.0, sample_spacing=4.0)

    assert len(stations) >= 49
    assert len(coarse_stations) < len(stations)
    assert stations[0] == 0.0
    assert stations[-1] == 48.0


def test_centerline3d_preview_can_use_bspline_display_mode() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)

        result = build_document_centerline3d_result(doc)
        preview = show_v1_centerline3d_preview_object(
            doc,
            result=result,
            project=project,
            display_mode="B-spline",
        )

        assert preview.CurveKind in {"bspline_smoothed", "bspline_interpolation", "evaluated_polyline"}
        assert preview.CenterlineDisplayMode == "bspline"
        assert preview.SourceGeometryStatus == "not_applicable"
        assert preview.SourceGeometryIntervalCount == 0
        assert preview.SourceGeometryPartArcIntervalCount == 0
        assert preview.SourceGeometryArcFit3DSampledIntervalCount == 0
        assert preview.SourceGeometryArcFitRejectedIntervalCount == 0
        assert preview.SourceGeometryArcFitAbsoluteTolerance > 0.0
        assert preview.SourceGeometryArcFitRelativeTolerance > 0.0
        assert list(preview.SourceGeometryIntervalRows) == []
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_preview_can_use_polyline_display_mode() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)

        result = build_document_centerline3d_result(doc)
        preview = show_v1_centerline3d_preview_object(
            doc,
            result=result,
            project=project,
            display_mode="Polyline",
        )

        assert preview.CurveKind == "polyline"
        assert preview.CenterlineDisplayMode == "polyline"
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_station_markers_are_optional_review_objects() -> None:
    doc, project, tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)

        result = build_document_centerline3d_result(doc)
        preview = show_v1_centerline3d_preview_object(doc, result=result, project=project, show_station_markers=False)

        assert preview.Name == "V1Centerline3DPreview"
        assert doc.getObject("V1Centerline3DStationMarkers") is None

        markers = show_v1_centerline3d_station_markers(doc, result=result, project=project, visible=True)

        assert markers.Name == "V1Centerline3DStationMarkers"
        assert markers.CRRecordKind == "v1_centerline3d_station_markers"
        assert markers.V1ObjectType == "V1Centerline3DStationMarkers"
        assert markers.MarkerCount == result.point_count
        assert list(markers.StationLabels)[0].startswith("STA ")
        assert markers.Name in {str(getattr(obj, "Name", "") or "") for obj in list(tree[V1_TREE_CENTERLINE3D].Group)}
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_frame_service_resolves_station_offset() -> None:
    result = Centerline3DResult(
        status="ready",
        point_rows=(
            Centerline3DPointRow(0.0, 0.0, 0.0, 10.0, grade=0.01),
            Centerline3DPointRow(20.0, 20.0, 0.0, 12.0, grade=0.03),
        ),
    )

    frame = Centerline3DFrameService().resolve_station_offset(result, 10.0, 5.0)

    assert frame.status in {"ok", "warning"}
    assert frame.x == 10.0
    assert frame.y == 5.0
    assert frame.z == 11.0
    assert abs(frame.grade - 0.02) <= 1.0e-9
    assert frame.source_mode == "centerline3d_result"


def test_centerline3d_frame_service_prefers_source_geometry_when_sources_are_available() -> None:
    radius = 100.0
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:curve",
                "circular_curve",
                0.0,
                100.0,
                length=100.0,
                geometry_payload={
                    "x_values": [radius, radius / (2.0**0.5), 0.0],
                    "y_values": [0.0, radius / (2.0**0.5), radius],
                },
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 10.0),
            ProfileControlPoint("pvi:100", 100.0, 20.0),
        ],
    )

    frame = Centerline3DFrameService().resolve_station(None, 25.0, alignment=alignment, profile=profile)

    assert frame.status == "ok"
    assert frame.source_mode == "centerline3d_source_geometry"
    assert abs(frame.x - radius * 0.9238795325) <= 1.0e-6
    assert abs(frame.y - radius * 0.3826834324) <= 1.0e-6
    assert frame.z == 12.5
    assert any("centerline3d_source_geometry_frame" in row for row in frame.diagnostic_rows)


def test_centerline3d_result_expands_strong_vertical_curve_station_samples() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:tangent",
                "tangent",
                0.0,
                100.0,
                geometry_payload={"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 0.0),
            ProfileControlPoint("pvi:50", 50.0, -20.0),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("vertical-curve:sag", "parabolic_vertical_curve", 0.0, 100.0, curve_length=100.0),
        ],
    )

    result = Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            alignment_model=alignment,
            profile_model=profile,
            station_values=(0.0, 100.0),
            stationing_id="stationing:test",
        )
    )

    assert result.status == "ready"
    assert result.point_count >= 100
    assert any(abs(row.station - 50.0) <= 1.0e-9 for row in result.point_rows)
    assert any("centerline3d_curve_station_expansion" in row for row in result.diagnostic_rows)


def test_centerline3d_result_includes_vertical_curve_boundary_samples() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:tangent",
                "tangent",
                0.0,
                180.0,
                geometry_payload={"x_values": [0.0, 180.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 12.0),
            ProfileControlPoint("pvi:90", 90.0, 15.0),
            ProfileControlPoint("pvi:180", 180.0, 13.5),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("vertical-curve:1", "parabolic_vertical_curve", 75.0, 105.0, curve_length=30.0),
        ],
    )

    result = Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            alignment_model=alignment,
            profile_model=profile,
            station_values=(0.0, 90.0, 180.0),
            stationing_id="stationing:test",
        )
    )
    stations = [round(float(row.station), 6) for row in result.point_rows]

    assert result.status == "ready"
    assert 75.0 in stations
    assert 90.0 in stations
    assert 105.0 in stations
    assert result.point_count > 3


def test_centerline3d_result_uses_profile_curve_when_pvi_is_not_exact_curve_midpoint() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:tangent",
                "tangent",
                0.0,
                180.0,
                geometry_payload={"x_values": [0.0, 180.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 12.0),
            ProfileControlPoint("pvi:90", 90.0, 15.0, kind="pvi"),
            ProfileControlPoint("pvi:180", 180.0, 13.5),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("vertical-curve:asymmetric", "parabolic_vertical_curve", 75.0, 110.0, curve_length=35.0),
        ],
    )

    result = Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            alignment_model=alignment,
            profile_model=profile,
            station_values=(0.0, 90.0, 180.0),
            stationing_id="stationing:test",
        )
    )
    row_85 = min(result.point_rows, key=lambda row: abs(float(row.station) - 85.0))
    linear_elevation = 12.0 + (15.0 - 12.0) * (85.0 / 90.0)

    assert result.status == "ready"
    assert abs(float(row_85.station) - 85.0) <= 1.0e-9
    assert abs(float(row_85.z) - linear_elevation) > 0.01


def test_centerline3d_panel_buttons_use_apply_before_close_without_refresh() -> None:
    _ensure_qapp()
    doc, _project, _tree = _new_project_doc()
    try:
        panel = V1Centerline3DTaskPanel(document=doc)
        button_texts = [button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)]

        assert "Refresh" not in button_texts
        assert button_texts[-2:] == ["Apply", "Close"]
        assert panel._display_mode_combo.currentText() == "Source Geometry"
        assert [panel._display_mode_combo.itemText(index) for index in range(panel._display_mode_combo.count())] == [
            "Source Geometry",
            "B-spline",
            "Polyline",
        ]
        assert panel._arc_fit_abs_tol_spin.value() > 0.0
        assert panel._arc_fit_rel_tol_spin.value() > 0.0
        assert panel._source_geometry_sample_spacing_spin.value() == 1.0
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_panel_summary_reports_source_geometry_counts() -> None:
    _ensure_qapp()
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        panel = V1Centerline3DTaskPanel(document=doc)
        panel._arc_fit_abs_tol_spin.setValue(0.25)
        panel._arc_fit_rel_tol_spin.setValue(0.002)
        panel._source_geometry_sample_spacing_spin.setValue(0.5)
        result = build_document_centerline3d_result(doc)
        preview = show_v1_centerline3d_preview_object(
            doc,
            result=result,
            project=project,
            display_mode="Source Geometry",
            arc_fit_absolute_tolerance=panel._selected_arc_fit_absolute_tolerance(),
            arc_fit_relative_tolerance=panel._selected_arc_fit_relative_tolerance(),
            source_geometry_sample_spacing=panel._selected_source_geometry_sample_spacing(),
        )

        panel._result = result
        panel._preview_object = preview
        panel._refresh_ui(message="summary test")

        labels = [panel._summary_table.item(row, 0).text() for row in range(panel._summary_table.rowCount())]
        values = [panel._summary_table.item(row, 1).text() for row in range(panel._summary_table.rowCount())]
        assert "Source Geometry" in labels
        assert values[labels.index("Source Geometry")] == "ready"
        assert "Source Intervals" in labels
        assert int(values[labels.index("Source Intervals")]) >= 1
        assert "Line / Arc / Sampled" in labels
        assert " / " in values[labels.index("Line / Arc / Sampled")]
        assert "PartArc / 3D ArcSampled" in labels
        assert " / " in values[labels.index("PartArc / 3D ArcSampled")]
        assert "ArcFit Accepted / Rejected" in labels
        assert " / " in values[labels.index("ArcFit Accepted / Rejected")]
        assert "ArcFit Tol abs / rel" in labels
        assert " / " in values[labels.index("ArcFit Tol abs / rel")]
        assert values[labels.index("ArcFit Tol abs / rel")] == "0.250000 / 0.002000"
        assert "Source Sample Spacing" in labels
        assert values[labels.index("Source Sample Spacing")] == "0.50 m"
        assert abs(preview.SourceGeometryArcFitAbsoluteTolerance - 0.25) <= 1.0e-9
        assert abs(preview.SourceGeometryArcFitRelativeTolerance - 0.002) <= 1.0e-9
        assert abs(preview.SourceGeometrySampleSpacing - 0.5) <= 1.0e-9
        diagnostic_text = panel._diagnostics.toPlainText()
        assert "Source Geometry intervals:" in diagnostic_text
        assert "line|" in diagnostic_text
        assert "arc_fit|" in diagnostic_text
        assert "|horizontal=" in diagnostic_text
        assert "|vertical=" in diagnostic_text
        assert "|shape=" in diagnostic_text
        assert "|reason=" in diagnostic_text
        assert "|arc_fit_status=accepted" in diagnostic_text
        assert "|arc_radius=" in diagnostic_text
        assert "|arc_sweep_deg=" in diagnostic_text
        assert "|arc_radial_error=" in diagnostic_text
        assert "|arc_tolerance=" in diagnostic_text
    finally:
        App.closeDocument(doc.Name)


def test_centerline3d_toolbar_order_follows_plan_profile_review() -> None:
    groups = corridorroad_workflow_command_groups()
    station_profile = groups["station_profile"]
    toolbar = corridorroad_workflow_toolbar_commands()

    assert station_profile == [
        "CorridorRoad_V1GenerateStations",
        "CorridorRoad_V1EditProfile",
        "CorridorRoad_ReviewPlanProfile",
        CENTERLINE3D_COMMAND_ID,
    ]
    assert toolbar.index(CENTERLINE3D_COMMAND_ID) == toolbar.index("CorridorRoad_ReviewPlanProfile") + 1
    assert CmdV1Centerline3D().GetResources()["MenuText"] == "3D Centerline"
