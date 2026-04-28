import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import V1_TREE_APPLIED_SECTIONS, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import assembly_preset_model_from_document, starter_assembly_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    CmdV1AppliedSections,
    applied_section_review_rows,
    apply_v1_applied_section_set,
    build_document_applied_section_set,
    show_applied_section_preview_object,
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


def test_applied_section_review_rows_summarize_station_context() -> None:
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

        rows = applied_section_review_rows(result)

        assert len(rows) == len(result.station_rows)
        assert rows[0]["region_id"] == "region:normal-01"
        assert rows[0]["assembly_id"] == "assembly:basic-road"
        assert rows[0]["template_id"] == "template:basic-road"
        assert rows[0]["surface_left_width"] > 0.0
        assert rows[0]["surface_right_width"] > 0.0
        assert rows[0]["component_count"] == 6
        assert rows[0]["status"] == "ok"
    finally:
        App.closeDocument(doc.Name)


def test_build_document_applied_section_set_uses_region_specific_assembly_objects() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=120.0)
        road_model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)
        bridge_model = assembly_preset_model_from_document("Bridge Interface", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_model_object(
            doc,
            project=project,
            assembly_model=road_model,
            object_name="V1AssemblyModelRoad",
            label="Road Assembly",
        )
        create_or_update_v1_assembly_model_object(
            doc,
            project=project,
            assembly_model=bridge_model,
            object_name="V1AssemblyModelBridge",
            label="Bridge Assembly",
        )
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        region_model.region_rows[0] = type(region_model.region_rows[0])(
            region_id="region:bridge-all",
            region_index=1,
            primary_kind="bridge",
            station_start=0.0,
            station_end=100000.0,
            assembly_ref="assembly:bridge-interface",
            template_ref="template:bridge-interface",
            priority=80,
        )
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        result = build_document_applied_section_set(doc, project=project)

        assert result.sections
        assert {section.assembly_id for section in result.sections} == {"assembly:bridge-interface"}
        assert {section.template_id for section in result.sections} == {"template:bridge-interface"}
        assert result.sections[0].component_rows[0].source_template_id == "template:bridge-interface"
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


def test_show_applied_section_preview_object_creates_selected_section_line() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        result = build_document_applied_section_set(doc, project=project)

        obj = show_applied_section_preview_object(doc, result, 0)

        assert obj is not None
        assert obj.CRRecordKind == "v1_applied_section_show_preview"
        assert obj.V1ObjectType == "V1AppliedSectionShowPreview"
        assert obj.RegionId == "region:normal-01"
        assert obj.AssemblyId == "assembly:basic-road"
        assert obj.TemplateId == "template:basic-road"
        assert obj.PreviewMode == "section_points"
        assert int(obj.PreviewPointCount) >= 4
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
        assert obj.Name in _group_names(tree[V1_TREE_APPLIED_SECTIONS])
    finally:
        App.closeDocument(doc.Name)


def test_applied_sections_command_resources_are_v1() -> None:
    resources = CmdV1AppliedSections().GetResources()

    assert resources["MenuText"] == "Applied Sections"
    assert "v1" in resources["ToolTip"]


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 applied sections command contract tests completed.")
