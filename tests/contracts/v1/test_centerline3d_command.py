import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups, corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.objects.obj_project import V1_TREE_CENTERLINE3D, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import (
    CENTERLINE3D_COMMAND_ID,
    CmdV1Centerline3D,
    build_document_centerline3d_result,
    show_v1_centerline3d_preview_object,
    show_v1_centerline3d_station_markers,
)
from freecad.Corridor_Road.v1.models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.services.evaluation import Centerline3DFrameService


def _new_project_doc():
    doc = App.newDocument("V1Centerline3DCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


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
        assert preview.Label == "3D Centerline"
        assert preview.CRRecordKind == "v1_centerline3d_review"
        assert preview.V1ObjectType == "V1Centerline3DReview"
        assert preview.CurveKind == "bspline_interpolation"
        assert preview.PointCount == result.point_count
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Name in {str(getattr(obj, "Name", "") or "") for obj in list(tree[V1_TREE_CENTERLINE3D].Group)}
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

    assert frame.status == "ok"
    assert frame.x == 10.0
    assert frame.y == 5.0
    assert frame.z == 11.0
    assert abs(frame.grade - 0.02) <= 1.0e-9
    assert frame.source_mode == "centerline3d_result"


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
