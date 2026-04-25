import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_STATIONS,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_stations import generate_v1_stations
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import apply_alignment_ip_rows
from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import build_document_plan_profile_preview
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_stationing import (
    build_v1_stationing_shape,
    create_v1_stationing,
    find_v1_stationing,
    station_value_rows,
)


def _new_project_doc():
    doc = App.newDocument("CRV1StationingSourceContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_create_v1_stationing_samples_alignment_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=30.0)

        assert stationing.V1ObjectType == "V1Stationing"
        assert stationing.AlignmentId == alignment.AlignmentId
        assert stationing.Interval == 30.0
        assert stationing.Status == "ok"
        assert list(stationing.StationValues) == [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
        assert len(stationing.XValues) == len(stationing.StationValues)
        assert station_value_rows(stationing)[0] == (0.0, "STA 0.000")
        assert len(list(stationing.StationKinds)) == len(list(stationing.StationValues))
        assert "key" in list(stationing.StationKinds)
    finally:
        App.closeDocument(doc.Name)


def test_v1_stationing_builds_tick_shape_and_station_labels() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=20.0)
        stationing.MajorInterval = 40.0
        stationing.StationStartOffset = 1000.0
        stationing.StationLabelFormat = "STA_PLUS"
        from freecad.Corridor_Road.v1.objects.obj_alignment import to_alignment_model
        from freecad.Corridor_Road.v1.objects.obj_stationing import update_v1_stationing_from_alignment

        update_v1_stationing_from_alignment(stationing, to_alignment_model(alignment), interval=20.0)
        doc.recompute()

        assert list(stationing.StationLabels)[0] == "1+00.000"
        assert "major" in list(stationing.StationKinds)
        assert int(stationing.DisplayTickCount) == len(list(stationing.StationValues))
        assert str(stationing.DisplayStatus) == "ok"
        assert getattr(stationing, "Shape", None) is not None
        assert not stationing.Shape.isNull()
        assert build_v1_stationing_shape(stationing) is not None
    finally:
        App.closeDocument(doc.Name)


def test_generate_v1_stations_routes_to_v1_station_folder() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = generate_v1_stations(
            document=doc,
            project=project,
            alignment=alignment,
            interval=45.0,
        )
        tree = ensure_project_tree(project, include_references=False)

        assert find_v1_stationing(doc) == stationing
        assert stationing.Name in _group_names(tree[V1_TREE_STATIONS])
        assert stationing.AlignmentId == alignment.AlignmentId
        assert stationing.Interval == 45.0
    finally:
        App.closeDocument(doc.Name)


def test_generate_v1_stations_includes_transition_curve_samples_and_review_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 30.0, "transition_length": 20.0},
                {"x": 100.0, "y": 100.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=True,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )

        stationing = generate_v1_stations(
            document=doc,
            project=project,
            alignment=alignment,
            interval=10.0,
        )
        transition_indexes = [
            index
            for index, kind in enumerate(list(stationing.ActiveElementKinds))
            if str(kind) == "transition_curve"
        ]
        transition_tangents = [
            round(float(list(stationing.TangentDirections)[index]), 3)
            for index in transition_indexes
        ]

        assert int(stationing.SourceGeometryElementCount) == 3
        assert str(stationing.SourceGeometrySignature)
        assert int(stationing.TransitionStationCount) >= 1
        assert "transition_curve" in str(stationing.ActiveElementKindSummary)
        assert transition_indexes
        assert len(transition_indexes) >= 2
        assert len(set(transition_tangents)) > 1
        assert any("element=transition_curve" in row for row in list(stationing.ReviewRows))
    finally:
        App.closeDocument(doc.Name)


def test_generate_v1_stations_marks_previous_stationing_as_stale_when_alignment_changes() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        first = generate_v1_stations(
            document=doc,
            project=project,
            alignment=alignment,
            interval=30.0,
        )
        first_signature = str(first.SourceGeometrySignature)

        apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 80.0, "y": 0.0, "radius": 25.0, "transition_length": 10.0},
                {"x": 120.0, "y": 60.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=True,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )
        second = generate_v1_stations(
            document=doc,
            project=project,
            alignment=alignment,
            interval=30.0,
        )

        assert first_signature != str(second.SourceGeometrySignature)
        assert "previous_stationing_was_stale=true" in str(second.Notes)
    finally:
        App.closeDocument(doc.Name)


def test_plan_profile_preview_prefers_v1_stationing_rows_when_available() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=45.0)

        preview = build_document_plan_profile_preview(doc, station_interval=20.0)

        assert preview is not None
        assert preview["legacy_objects"]["stationing"] == stationing
        assert [row.station for row in preview["plan_output"].station_rows] == list(stationing.StationValues)
        stations = [row["station"] for row in preview["key_station_rows"]]
        assert 45.0 in stations
        assert 20.0 not in stations
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 stationing source object contract tests completed.")
