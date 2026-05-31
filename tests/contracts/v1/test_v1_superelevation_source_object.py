import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_SUPERELEVATION,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationConstraint,
    SuperelevationModel,
)
from freecad.Corridor_Road.v1.objects.obj_superelevation import (
    create_or_update_v1_superelevation_source_object,
    find_v1_superelevation_source,
    to_superelevation_model,
)


def _new_project_doc():
    doc = App.newDocument("CRV1SuperelevationSourceContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def _sample_model() -> SuperelevationModel:
    return SuperelevationModel(
        schema_version=1,
        project_id="project:test",
        label="Main Superelevation",
        superelevation_id="superelevation:main",
        alignment_id="alignment:main",
        profile_id="profile:fg",
        control_rows=[
            CrossfallControlRow(
                control_row_id="control:normal:0",
                station=0.0,
                side="both",
                crossfall_value=-2.0,
                kind="normal_crown",
            ),
            CrossfallControlRow(
                control_row_id="control:full:1",
                station=80.0,
                side="right",
                crossfall_value=6.0,
                kind="full_super",
            ),
        ],
        transition_rows=[
            RunoffTransitionRow(
                transition_id="transition:runoff:1",
                station_start=40.0,
                station_end=80.0,
                kind="runoff",
                transition_policy="linear",
            )
        ],
        constraint_rows=[
            SuperelevationConstraint(
                constraint_id="constraint:max-rate",
                kind="max_superelevation_rate",
                value=8.0,
                unit="percent",
                hard_or_soft="soft",
            )
        ],
        source_refs=["alignment:main", "profile:fg"],
    )


def test_create_or_update_v1_superelevation_source_round_trips_model() -> None:
    doc, project = _new_project_doc()
    try:
        obj = create_or_update_v1_superelevation_source_object(
            doc,
            _sample_model(),
            project=project,
        )
        model = to_superelevation_model(obj)

        assert obj.V1ObjectType == "V1SuperelevationSource"
        assert obj.CRRecordKind == "v1_superelevation_source"
        assert int(obj.ControlRowCount) == 2
        assert int(obj.TransitionRowCount) == 1
        assert int(obj.ConstraintRowCount) == 1
        assert model is not None
        assert model.superelevation_id == "superelevation:main"
        assert model.alignment_id == "alignment:main"
        assert model.profile_id == "profile:fg"
        assert len(model.control_rows) == 2
        assert model.control_rows[1].crossfall_value == 6.0
        assert model.transition_rows[0].station_start == 40.0
        assert model.constraint_rows[0].kind == "max_superelevation_rate"
        assert model.source_refs == ["alignment:main", "profile:fg"]
    finally:
        App.closeDocument(doc.Name)


def test_superelevation_source_routes_under_alignment_profile_superelevation_folder() -> None:
    doc, project = _new_project_doc()
    try:
        obj = create_or_update_v1_superelevation_source_object(
            doc,
            _sample_model(),
            project=project,
        )
        tree = ensure_project_tree(project, include_references=False)

        assert find_v1_superelevation_source(doc) == obj
        assert obj.Name in _group_names(tree[V1_TREE_SUPERELEVATION])
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 superelevation source object contract tests completed.")
