import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_ASSEMBLIES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    AssemblyModel,
    SectionTemplate,
    TemplateComponent,
)
from freecad.Corridor_Road.v1.objects.obj_assembly import (
    create_or_update_v1_assembly_model_object,
    find_v1_assembly_model,
    to_assembly_model,
)


def _new_project_doc():
    doc = App.newDocument("V1AssemblySourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_assembly_model() -> AssemblyModel:
    return AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:basic-road",
        alignment_id="alignment:main",
        active_template_id="template:basic-road",
        template_rows=[
            SectionTemplate(
                template_id="template:basic-road",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(
                        component_id="lane:left",
                        kind="lane",
                        component_index=1,
                        side="left",
                        width=3.5,
                        slope=-0.02,
                        thickness=0.25,
                        material="asphalt",
                    ),
                    TemplateComponent(
                        component_id="ditch:right",
                        kind="ditch",
                        component_index=2,
                        side="right",
                        width=1.2,
                        slope=-0.03,
                        target_ref="drainage:side-ditch-right",
                        enabled=False,
                    ),
                ],
            )
        ],
    )


def test_create_or_update_v1_assembly_model_object_routes_to_assemblies_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_assembly_model_object(
            document=doc,
            project=project,
            assembly_model=_sample_assembly_model(),
        )

        assert obj.V1ObjectType == "V1AssemblyModel"
        assert obj.CRRecordKind == "v1_assembly_model"
        assert obj.AssemblyId == "assembly:basic-road"
        assert obj.ActiveTemplateId == "template:basic-road"
        assert obj.TemplateCount == 1
        assert obj.ComponentCount == 2
        assert list(obj.ComponentKinds) == ["lane", "ditch"]
        assert list(obj.ComponentEnabledValues) == [1, 0]
        assert obj.Name in _group_names(tree[V1_TREE_ASSEMBLIES])
    finally:
        App.closeDocument(doc.Name)


def test_v1_assembly_model_object_roundtrips_to_source_model() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_assembly_model_object(
            document=doc,
            project=project,
            assembly_model=_sample_assembly_model(),
        )

        model = to_assembly_model(obj)

        assert model is not None
        assert model.assembly_id == "assembly:basic-road"
        assert model.active_template_id == "template:basic-road"
        assert model.template_rows[0].component_rows[0].side == "left"
        assert model.template_rows[0].component_rows[0].width == 3.5
        assert model.template_rows[0].component_rows[1].kind == "ditch"
        assert model.template_rows[0].component_rows[1].enabled is False
        assert model.template_rows[0].component_rows[1].target_ref == "drainage:side-ditch-right"
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_assembly_model_object_updates_existing_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first = create_or_update_v1_assembly_model_object(
            document=doc,
            project=project,
            assembly_model=_sample_assembly_model(),
        )
        updated_model = AssemblyModel(
            schema_version=1,
            project_id="proj-1",
            assembly_id="assembly:bridge",
            active_template_id="template:bridge",
            template_rows=[
                SectionTemplate(
                    template_id="template:bridge",
                    template_kind="bridge_deck",
                    component_rows=[
                        TemplateComponent("bridge_deck", "structure_interface", side="center", width=10.0)
                    ],
                )
            ],
        )
        second = create_or_update_v1_assembly_model_object(
            document=doc,
            project=project,
            assembly_model=updated_model,
        )

        assert first.Name == second.Name
        assert second.AssemblyId == "assembly:bridge"
        assert second.ComponentCount == 1
        assert find_v1_assembly_model(doc) == second
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 assembly source object contract tests completed.")
