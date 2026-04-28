import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import V1_TREE_ASSEMBLIES, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import (
    CmdV1AssemblyEditor,
    assembly_preset_model_from_document,
    assembly_preset_names,
    apply_v1_assembly_model,
    show_assembly_preview_object,
    starter_assembly_model_from_document,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_assembly import find_v1_assembly_model, to_assembly_model


def _new_project_doc():
    doc = App.newDocument("V1AssemblyEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_starter_assembly_model_builds_basic_road_components() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)

        components = model.template_rows[0].component_rows
        assert model.assembly_id == "assembly:basic-road"
        assert model.active_template_id == "template:basic-road"
        assert model.alignment_id == alignment.AlignmentId
        assert [component.kind for component in components[:4]] == ["lane", "lane", "shoulder", "shoulder"]
        assert components[0].side == "left"
        assert components[0].width == 3.5
    finally:
        App.closeDocument(doc.Name)


def test_assembly_presets_offer_multiple_practical_templates() -> None:
    doc, project = _new_project_doc()
    try:
        names = assembly_preset_names()

        assert "Basic Road" in names
        assert "Urban Curb & Gutter" in names
        assert "Bridge Interface" in names
        urban = assembly_preset_model_from_document("Urban Curb & Gutter", doc, project=project)
        components = urban.template_rows[0].component_rows
        assert urban.assembly_id == "assembly:urban-curb-gutter"
        assert urban.active_template_id == "template:urban-curb-gutter"
        assert "gutter" in [component.kind for component in components]
        assert "sidewalk" in [component.kind for component in components]
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_assembly_model_creates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        model = starter_assembly_model_from_document(doc, project=project)

        obj = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        roundtrip = to_assembly_model(obj)

        assert obj == find_v1_assembly_model(doc)
        assert obj.V1ObjectType == "V1AssemblyModel"
        assert obj.CRRecordKind == "v1_assembly_model"
        assert roundtrip.assembly_id == "assembly:basic-road"
        assert len(roundtrip.template_rows[0].component_rows) == 6
    finally:
        App.closeDocument(doc.Name)


def test_show_assembly_preview_object_creates_front_view_cross_section() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        model = starter_assembly_model_from_document(doc, project=project)

        obj = show_assembly_preview_object(doc, model)

        assert obj is not None
        assert obj.CRRecordKind == "v1_assembly_show_preview"
        assert obj.V1ObjectType == "V1AssemblyShowPreview"
        assert obj.AssemblyId == "assembly:basic-road"
        assert int(obj.ComponentCount) == 6
        assert obj.Shape.BoundBox.XLength > 0.0
        assert obj.Shape.BoundBox.ZLength > 0.0
        assert obj.Name in _group_names(tree[V1_TREE_ASSEMBLIES])
    finally:
        App.closeDocument(doc.Name)


def test_assembly_editor_command_resources_are_v1_assembly() -> None:
    resources = CmdV1AssemblyEditor().GetResources()

    assert resources["MenuText"] == "Assembly"
    assert "v1" in resources["ToolTip"]


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 assembly editor command contract tests completed.")
