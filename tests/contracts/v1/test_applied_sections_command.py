import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import starter_assembly_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    CmdV1AppliedSections,
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_region_editor import starter_region_model_from_document
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_assembly import create_or_update_v1_assembly_model_object
from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing


def _new_project_doc():
    doc = App.newDocument("V1AppliedSectionsCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_build_document_applied_section_set_uses_v1_sources() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        assembly_model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        result = build_document_applied_section_set(doc, project=project)

        assert len(result.station_rows) == 5
        assert result.sections[0].assembly_id == "assembly:basic-road"
        assert result.sections[0].template_id == "template:basic-road"
        assert result.sections[0].region_id == "region:normal-01"
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_applied_section_set_creates_result_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        obj = apply_v1_applied_section_set(document=doc, project=project)

        assert obj == find_v1_applied_section_set(doc)
        assert obj.V1ObjectType == "V1AppliedSectionSet"
        assert obj.StationCount == 5
        assert list(obj.TemplateIds) == [
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
        ]
    finally:
        App.closeDocument(doc.Name)


def test_applied_sections_command_resources_are_v1() -> None:
    resources = CmdV1AppliedSections().GetResources()

    assert resources["MenuText"] == "Applied Sections"
    assert "v1" in resources["ToolTip"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 applied sections command contract tests completed.")
