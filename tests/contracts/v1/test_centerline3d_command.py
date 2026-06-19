import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups, corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.objects.obj_project import V1_TREE_CENTERLINE3D, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import (
    CENTERLINE3D_COMMAND_ID,
    CmdV1Centerline3D,
    V1Centerline3DTaskPanel,
    build_document_centerline3d_result,
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
        assert preview.CurveKind == "bspline_interpolation"
        assert preview.CenterlineDisplayMode == "smooth_curve"
        assert preview.PointCount == result.point_count
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Name in {str(getattr(obj, "Name", "") or "") for obj in list(tree[V1_TREE_CENTERLINE3D].Group)}
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
    assert result.point_count > 2
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
        assert panel._display_mode_combo.currentText() == "Smooth Curve"
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
