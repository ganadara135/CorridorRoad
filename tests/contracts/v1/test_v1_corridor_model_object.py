import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_CORRIDOR_MODEL,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel, CorridorSamplingPolicy, CorridorStationRow
from freecad.Corridor_Road.v1.objects.obj_corridor import (
    create_or_update_v1_corridor_model_object,
    find_v1_corridor_model,
    to_corridor_model,
)


def _new_project_doc():
    doc = App.newDocument("V1CorridorModelObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_corridor() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        region_model_ref="regions:main",
        applied_section_set_ref="sections:main",
        surface_build_refs=["surface:main"],
        sampling_policy=CorridorSamplingPolicy("corridor:main:sampling", 20.0),
        station_rows=[
            CorridorStationRow("station:0", 0.0, source_reason="section:0"),
            CorridorStationRow("station:20", 20.0, source_reason="section:20"),
        ],
    )


def test_create_or_update_v1_corridor_model_routes_to_corridor_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_corridor_model_object(
            document=doc,
            project=project,
            corridor_model=_sample_corridor(),
        )

        assert obj.V1ObjectType == "V1CorridorModel"
        assert obj.CRRecordKind == "v1_corridor_model"
        assert obj.CorridorId == "corridor:main"
        assert obj.StationCount == 2
        assert list(obj.SurfaceBuildRefs) == ["surface:main"]
        assert list(obj.StationValues) == [0.0, 20.0]
        assert obj.Name in _group_names(tree[V1_TREE_CORRIDOR_MODEL])
    finally:
        App.closeDocument(doc.Name)


def test_v1_corridor_model_roundtrips_summary_rows() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_corridor_model_object(
            document=doc,
            project=project,
            corridor_model=_sample_corridor(),
        )

        model = to_corridor_model(obj)

        assert model is not None
        assert model.corridor_id == "corridor:main"
        assert model.applied_section_set_ref == "sections:main"
        assert model.surface_build_refs == ["surface:main"]
        assert [row.source_reason for row in model.station_rows] == ["section:0", "section:20"]
        assert find_v1_corridor_model(doc) == obj
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 corridor model object contract tests completed.")
