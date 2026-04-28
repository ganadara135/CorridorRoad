import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_REGIONS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands.cmd_region_editor import (
    CmdV1RegionEditor,
    apply_v1_region_model,
    region_assembly_reference_warnings,
    starter_region_model_from_document,
)
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import starter_assembly_model_from_document
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_assembly import create_or_update_v1_assembly_model_object
from freecad.Corridor_Road.v1.objects.obj_region import find_v1_region_model, to_region_model
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing


def _new_project_doc():
    doc = App.newDocument("V1RegionEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def test_starter_region_model_uses_generated_station_range() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        model = starter_region_model_from_document(doc, project=project, alignment=alignment)

        stations = list(stationing.StationValues)
        assert len(model.region_rows) == 1
        assert model.region_rows[0].primary_kind == "normal_road"
        assert model.region_rows[0].station_start == min(stations)
        assert model.region_rows[0].station_end == max(stations)
        assert model.region_rows[0].priority == 10
        assert model.alignment_id == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_starter_region_model_uses_existing_v1_assembly_ref() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        assembly_model = starter_assembly_model_from_document(doc, project=project)
        create_or_update_v1_assembly_model_object(
            document=doc,
            project=project,
            assembly_model=assembly_model,
        )

        model = starter_region_model_from_document(doc, project=project)

        assert model.region_rows[0].assembly_ref == "assembly:basic-road"
        assert model.region_rows[0].template_ref == "template:basic-road"
    finally:
        App.closeDocument(doc.Name)


def test_region_assembly_reference_warnings_report_missing_refs() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-region-editor",
        region_model_id="regions:main",
        region_rows=[
            RegionRow(
                region_id="region:known",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:basic-road",
            ),
            RegionRow(
                region_id="region:missing",
                station_start=50.0,
                station_end=100.0,
                assembly_ref="assembly:missing",
            ),
        ],
    )

    warnings = region_assembly_reference_warnings(model, ["assembly:basic-road"])

    assert warnings == ["WARNING: region:missing references missing assembly_ref assembly:missing."]


def test_apply_v1_region_model_creates_region_source_object_only() -> None:
    doc, project, tree = _new_project_doc()
    try:
        model = RegionModel(
            schema_version=1,
            project_id="proj-region-editor",
            region_model_id="regions:main",
            alignment_id="alignment:main",
            region_rows=[
                RegionRow(
                    region_id="region:bridge-drainage",
                    region_index=1,
                    primary_kind="bridge",
                    applied_layers=["ditch", "drainage"],
                    station_start=100.0,
                    station_end=180.0,
                    assembly_ref="assembly:bridge",
                    structure_refs=["structure:bridge-01"],
                    drainage_refs=["drainage:deck-drain"],
                    priority=80,
                    notes="Bridge region with drainage and ditch layers.",
                )
            ],
        )

        obj = apply_v1_region_model(document=doc, project=project, region_model=model)
        roundtrip = to_region_model(obj)

        assert obj == find_v1_region_model(doc)
        assert obj.V1ObjectType == "V1RegionModel"
        assert obj.CRRecordKind == "v1_region_model"
        assert obj.RegionCount == 1
        assert roundtrip.region_rows[0].primary_kind == "bridge"
        assert roundtrip.region_rows[0].applied_layers == ["ditch", "drainage"]
        assert roundtrip.region_rows[0].structure_refs == ["structure:bridge-01"]
        assert roundtrip.region_rows[0].drainage_refs == ["drainage:deck-drain"]
        assert obj.Name in _group_names(tree[V1_TREE_REGIONS])
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_region_model_reuses_existing_region_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first_model = RegionModel(
            schema_version=1,
            project_id="proj-region-editor",
            region_model_id="regions:main",
            region_rows=[
                RegionRow(
                    region_id="region:normal",
                    primary_kind="normal_road",
                    station_start=0.0,
                    station_end=100.0,
                )
            ],
        )
        second_model = RegionModel(
            schema_version=1,
            project_id="proj-region-editor",
            region_model_id="regions:main",
            region_rows=[
                RegionRow(
                    region_id="region:ramp",
                    primary_kind="ramp",
                    station_start=100.0,
                    station_end=160.0,
                    priority=70,
                )
            ],
        )

        first = apply_v1_region_model(document=doc, project=project, region_model=first_model)
        second = apply_v1_region_model(document=doc, project=project, region_model=second_model)

        assert first.Name == second.Name
        assert second.RegionCount == 1
        assert list(second.RegionIds) == ["region:ramp"]
    finally:
        App.closeDocument(doc.Name)


def test_region_editor_command_resources_are_v1_regions() -> None:
    resources = CmdV1RegionEditor().GetResources()

    assert resources["MenuText"] == "Regions"
    assert "v1" in resources["ToolTip"]


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 region editor command contract tests completed.")
