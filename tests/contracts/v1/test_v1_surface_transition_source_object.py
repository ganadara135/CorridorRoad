import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_REGIONS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.surface_transition_model import (
    SurfaceTransitionModel,
    SurfaceTransitionRange,
)
from freecad.Corridor_Road.v1.objects.obj_surface_transition import (
    create_or_update_v1_surface_transition_model_object,
    find_v1_surface_transition_model,
    to_surface_transition_model,
)


def _new_project_doc():
    doc = App.newDocument("V1SurfaceTransitionSourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_transition_model() -> SurfaceTransitionModel:
    return SurfaceTransitionModel(
        schema_version=1,
        project_id="proj-1",
        transition_model_id="surface-transitions:main",
        corridor_ref="corridor:main",
        transition_ranges=[
            SurfaceTransitionRange(
                "transition:region-a-b",
                95.0,
                105.0,
                from_region_ref="region:a",
                to_region_ref="region:b",
                target_surface_kinds=["design_surface", "subgrade_surface"],
                transition_mode="interpolate_matching_roles",
                sample_interval=2.5,
                approval_status="active",
                source_ref="user:station-range",
                notes="Apply transition surface around Region boundary.",
            ),
            SurfaceTransitionRange(
                "transition:region-b-c",
                195.0,
                205.0,
                from_region_ref="region:b",
                to_region_ref="region:c",
                target_surface_kinds=["daylight_surface"],
                transition_mode="interpolate_width",
                enabled=False,
                approval_status="draft",
            ),
        ],
    )


def test_create_or_update_v1_surface_transition_model_object_routes_to_regions_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_surface_transition_model_object(
            document=doc,
            project=project,
            transition_model=_sample_transition_model(),
        )

        assert obj.V1ObjectType == "V1SurfaceTransitionModel"
        assert obj.CRRecordKind == "v1_surface_transition_model"
        assert obj.TransitionModelId == "surface-transitions:main"
        assert obj.CorridorRef == "corridor:main"
        assert obj.TransitionRangeCount == 2
        assert list(obj.TargetSurfaceKindRows) == ["design_surface,subgrade_surface", "daylight_surface"]
        assert list(obj.EnabledRows) == ["true", "false"]
        assert obj.Name in _group_names(tree[V1_TREE_REGIONS])
    finally:
        App.closeDocument(doc.Name)


def test_v1_surface_transition_model_object_roundtrips_to_source_model() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_surface_transition_model_object(
            document=doc,
            project=project,
            transition_model=_sample_transition_model(),
        )

        model = to_surface_transition_model(obj)

        assert model is not None
        assert model.transition_model_id == "surface-transitions:main"
        assert model.corridor_ref == "corridor:main"
        assert model.transition_ranges[0].target_surface_kinds == ["design_surface", "subgrade_surface"]
        assert model.transition_ranges[0].approval_status == "active"
        assert model.transition_ranges[0].sample_interval == 2.5
        assert model.transition_ranges[1].enabled is False
        assert find_v1_surface_transition_model(doc) == obj
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_surface_transition_model_object_updates_existing_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first = create_or_update_v1_surface_transition_model_object(
            document=doc,
            project=project,
            transition_model=_sample_transition_model(),
        )
        updated_model = SurfaceTransitionModel(
            schema_version=1,
            project_id="proj-1",
            transition_model_id="surface-transitions:main",
            corridor_ref="corridor:main",
            transition_ranges=[
                SurfaceTransitionRange(
                    "transition:single",
                    145.0,
                    155.0,
                    from_region_ref="region:x",
                    to_region_ref="region:y",
                )
            ],
        )

        second = create_or_update_v1_surface_transition_model_object(
            document=doc,
            project=project,
            transition_model=updated_model,
        )

        assert first.Name == second.Name
        assert second.TransitionRangeCount == 1
        assert list(second.TransitionIds) == ["transition:single"]
        assert find_v1_surface_transition_model(doc) == second
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 surface transition source object contract tests completed.")
