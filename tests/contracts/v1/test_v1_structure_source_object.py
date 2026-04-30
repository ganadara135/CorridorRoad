import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_STRUCTURES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.objects.obj_structure import (
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
)


def _new_project_doc():
    doc = App.newDocument("V1StructureSourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="alignment:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:bridge-01",
                structure_kind="bridge",
                structure_role="interface",
                placement=StructurePlacement(
                    placement_id="placement:bridge-01",
                    alignment_id="alignment:main",
                    station_start=100.0,
                    station_end=180.0,
                    offset=0.0,
                ),
                geometry_ref="",
            )
        ],
        interaction_rule_rows=[
            StructureInteractionRule(
                interaction_rule_id="rule:bridge-section",
                structure_ref="structure:bridge-01",
                rule_kind="section_handoff",
                target_scope="section",
                priority=20,
            )
        ],
        influence_zone_rows=[
            StructureInfluenceZone(
                influence_zone_id="zone:bridge-01",
                structure_ref="structure:bridge-01",
                zone_kind="clearance",
                station_start=95.0,
                station_end=185.0,
                offset_min=-8.0,
                offset_max=8.0,
            )
        ],
    )


def test_create_or_update_v1_structure_model_object_routes_to_structures_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )

        assert obj.V1ObjectType == "V1StructureModel"
        assert obj.CRRecordKind == "v1_structure_model"
        assert obj.StructureModelId == "structures:main"
        assert obj.AlignmentId == "alignment:main"
        assert obj.StructureCount == 1
        assert list(obj.StructureIds) == ["structure:bridge-01"]
        assert list(obj.RuleIds) == ["rule:bridge-section"]
        assert list(obj.InfluenceZoneIds) == ["zone:bridge-01"]
        assert obj.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_v1_structure_model_object_roundtrips_to_structure_model() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )

        model = to_structure_model(obj)

        assert model is not None
        assert model.structure_model_id == "structures:main"
        assert model.structure_rows[0].structure_id == "structure:bridge-01"
        assert model.structure_rows[0].placement.station_start == 100.0
        assert model.interaction_rule_rows[0].structure_ref == "structure:bridge-01"
        assert model.influence_zone_rows[0].offset_max == 8.0
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_structure_model_object_updates_existing_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )
        updated_model = StructureModel(
            schema_version=1,
            project_id="proj-1",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="clearance_control",
                    placement=StructurePlacement(
                        placement_id="placement:culvert-01",
                        alignment_id="alignment:main",
                        station_start=200.0,
                        station_end=220.0,
                    ),
                )
            ],
        )
        second = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=updated_model,
        )

        assert first.Name == second.Name
        assert second.StructureCount == 1
        assert list(second.StructureIds) == ["structure:culvert-01"]
        assert find_v1_structure_model(doc) == second
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 structure source object contract tests completed.")
