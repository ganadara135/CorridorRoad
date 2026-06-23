import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_REGIONS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.objects.obj_region import (
    create_or_update_v1_region_model_object,
    find_v1_region_model,
    to_region_model,
)


def _new_project_doc():
    doc = App.newDocument("V1RegionSourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_region_model() -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:normal",
                region_index=1,
                station_start=0.0,
                station_end=120.0,
                assembly_ref="assembly:road",
                template_ref="template:road",
                priority=10,
            ),
            RegionRow(
                region_id="region:bridge",
                region_index=2,
                station_start=120.0,
                station_end=180.0,
                assembly_ref="assembly:bridge-deck",
                template_ref="template:bridge",
                override_refs=["override:bridge-shoulder"],
                priority=80,
                notes="Bridge region. Structure and Drainage are assigned in their own panels.",
            ),
        ],
    )


def test_create_or_update_v1_region_model_object_routes_to_regions_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_region_model_object(
            document=doc,
            project=project,
            region_model=_sample_region_model(),
        )

        assert obj.V1ObjectType == "V1RegionModel"
        assert obj.CRRecordKind == "v1_region_model"
        assert obj.RegionModelId == "regions:main"
        assert obj.AlignmentId == "alignment:main"
        assert obj.RegionCount == 2
        assert not hasattr(obj, "PrimaryKinds") or list(getattr(obj, "PrimaryKinds", [])) == []
        assert not hasattr(obj, "AppliedLayerRows") or list(getattr(obj, "AppliedLayerRows", [])) == []
        assert not hasattr(obj, "StructureRefs")
        assert not hasattr(obj, "StructureRefRows")
        assert not hasattr(obj, "DrainageRefRows")
        assert obj.Name in _group_names(tree[V1_TREE_REGIONS])
    finally:
        App.closeDocument(doc.Name)


def test_v1_region_model_object_roundtrips_to_region_model() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_region_model_object(
            document=doc,
            project=project,
            region_model=_sample_region_model(),
        )

        model = to_region_model(obj)

        assert model is not None
        assert model.region_model_id == "regions:main"
        assert model.region_rows[1].override_refs == ["override:bridge-shoulder"]
        assert not hasattr(model.region_rows[1], "structure_ref")
        assert not hasattr(model.region_rows[1], "drainage_refs")
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_region_model_object_updates_existing_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first = create_or_update_v1_region_model_object(
            document=doc,
            project=project,
            region_model=_sample_region_model(),
        )
        updated_model = RegionModel(
            schema_version=1,
            project_id="proj-1",
            region_model_id="regions:main",
            alignment_id="alignment:main",
            region_rows=[
                RegionRow(
                    region_id="region:ramp",
                    station_start=180.0,
                    station_end=240.0,
                    assembly_ref="assembly:ramp",
                    priority=70,
                )
            ],
        )
        second = create_or_update_v1_region_model_object(
            document=doc,
            project=project,
            region_model=updated_model,
        )

        assert first.Name == second.Name
        assert second.RegionCount == 1
        assert list(second.RegionIds) == ["region:ramp"]
        assert find_v1_region_model(doc) == second
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 region source object contract tests completed.")
