import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import V1_TREE_ASSEMBLIES, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import (
    CmdV1AssemblyEditor,
    _assembly_preview_points,
    _ditch_component_note,
    _ditch_effective_field_keys,
    _ditch_material_note,
    _ditch_shape_diagram,
    _ditch_shape_defaults,
    _ditch_visible_field_keys,
    _merge_ditch_parameters,
    _validate_assembly_model,
    assembly_preset_model_from_document,
    assembly_preset_names,
    apply_v1_assembly_model,
    show_assembly_preview_object,
    starter_assembly_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import AssemblyModel, SectionTemplate, TemplateComponent
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
        drainage = assembly_preset_model_from_document("Drainage Ditch Road", doc, project=project)
        ditch_components = [component for component in drainage.template_rows[0].component_rows if component.kind == "ditch"]
        assert ditch_components
        assert {component.parameters.get("shape") for component in ditch_components} == {"trapezoid"}
        assert ditch_components[0].parameters["bottom_width"] == 0.6
    finally:
        App.closeDocument(doc.Name)


def test_assembly_validation_reports_ditch_shape_parameter_warnings() -> None:
    model = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:ditch-validation",
        template_rows=[
            SectionTemplate(
                template_id="template:ditch-validation",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(
                        "ditch-left",
                        "ditch",
                        side="left",
                        width=1.2,
                        parameters={"shape": "trapezoid", "bottom_width": 0.5},
                    ),
                    TemplateComponent(
                        "ditch-concrete",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"shape": "u", "bottom_width": 0.7, "depth": 0.5},
                    )
                ],
            )
        ],
    )

    messages = _validate_assembly_model(model)

    assert "WARN: ditch component ditch-left missing required parameter depth." in messages
    assert "WARN: ditch component ditch-concrete uses structural material and requires wall_thickness." in messages


def test_ditch_parameter_editor_merge_preserves_unknown_parameters() -> None:
    merged = _merge_ditch_parameters(
        {"shape": "v", "depth": "0.2", "hydraulic_note": "keep"},
        {"shape": "trapezoid", "bottom_width": "0.6", "depth": "0.45", "top_width": ""},
    )

    assert merged["shape"] == "trapezoid"
    assert merged["bottom_width"] == "0.6"
    assert merged["depth"] == "0.45"
    assert "top_width" not in merged
    assert merged["hydraulic_note"] == "keep"


def test_ditch_shape_helpers_limit_visible_fields_and_defaults() -> None:
    assert _ditch_visible_field_keys("u") == ("bottom_width", "depth", "wall_thickness", "lining_thickness")
    assert "lining_thickness" in _ditch_effective_field_keys("v", "riprap_lined")
    assert _ditch_visible_field_keys("custom_polyline") == ("section_points",)
    assert _ditch_shape_defaults("v")["invert_offset"] == "0.800"
    assert "bottom" in _ditch_shape_diagram("trapezoid")
    assert "section_points" in _ditch_shape_diagram("custom_polyline")
    assert "structural" in _ditch_material_note("concrete", "u")


def test_ditch_component_note_reflects_shape_material_and_parameters() -> None:
    note = _ditch_component_note(
        side="right",
        material="concrete",
        parameters={"shape": "u", "bottom_width": "0.700", "depth": "0.500", "wall_thickness": "0.150"},
    )

    assert "Right U-shaped ditch" in note
    assert "bottom_width=0.700" in note
    assert "depth=0.500" in note
    assert "material=concrete" in note
    assert "policy=structural" in note


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


def test_assembly_preview_points_follow_shape_aware_ditch_parameters() -> None:
    template = SectionTemplate(
        template_id="template:ditch-preview",
        template_kind="roadway",
        component_rows=[
            TemplateComponent("lane-left", "lane", side="left", width=3.5),
            TemplateComponent(
                "ditch-left",
                "ditch",
                side="left",
                width=1.2,
                parameters={"shape": "u", "bottom_width": 1.2, "depth": 0.8},
            ),
        ],
    )

    points = _assembly_preview_points(template)

    assert any(
        round(float(left.x), 6) == round(float(right.x), 6)
        and abs(float(left.z) - float(right.z)) > 0.5
        for left, right in zip(points, points[1:])
    )


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
