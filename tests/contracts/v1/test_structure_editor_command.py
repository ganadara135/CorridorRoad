import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_STRUCTURES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands.cmd_structure_editor import (
    CmdV1StructureEditor,
    _bridge_spec_from_detail,
    _kind_detail_field_specs,
    _kind_detail_values,
    _replace_kind_spec,
    apply_v1_structure_model,
    show_v1_structure_preview_object,
    starter_structure_model_from_document,
    structure_preset_model_from_document,
    structure_preset_names,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_structure import find_v1_structure_model, to_structure_model


def _new_project_doc():
    doc = App.newDocument("V1StructureEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def test_starter_structure_model_uses_generated_station_range() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        model = starter_structure_model_from_document(doc, project=project, alignment=alignment)

        stations = list(stationing.StationValues)
        assert len(model.structure_rows) == 1
        assert model.structure_rows[0].structure_kind == "bridge"
        assert min(stations) <= model.structure_rows[0].placement.station_start <= max(stations)
        assert min(stations) <= model.structure_rows[0].placement.station_end <= max(stations)
        assert model.alignment_id == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_structure_presets_offer_practical_structure_sets() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        names = structure_preset_names()

        assert "Bridge Segment" in names
        assert "Culvert Crossing" in names
        assert "Retaining Wall" in names
        model = structure_preset_model_from_document("Culvert Crossing", doc, project=project, alignment=alignment)

        assert len(model.structure_rows) == 1
        assert model.structure_rows[0].structure_id == "structure:culvert-01"
        assert model.structure_rows[0].structure_kind == "culvert"
        assert model.structure_rows[0].geometry_spec_ref == "geometry-spec:culvert-01"
        assert model.geometry_spec_rows[0].structure_ref == "structure:culvert-01"
        assert model.geometry_spec_rows[0].shape_kind == "box"
        assert model.geometry_spec_rows[0].width == 3.0
        assert model.geometry_spec_rows[0].height == 2.0
        assert model.geometry_spec_rows[0].vertical_position_mode == "profile_frame"
        assert model.culvert_geometry_spec_rows[0].geometry_spec_ref == "geometry-spec:culvert-01"
        assert model.culvert_geometry_spec_rows[0].barrel_shape == "box"
        assert model.culvert_geometry_spec_rows[0].wall_thickness == 0.3
        assert model.structure_rows[0].placement.station_start < model.structure_rows[0].placement.station_end
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_structure_model_creates_structure_source_object_only() -> None:
    doc, project, tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
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
                    ),
                )
            ],
        )

        obj = apply_v1_structure_model(document=doc, project=project, structure_model=model)
        roundtrip = to_structure_model(obj)

        assert obj == find_v1_structure_model(doc)
        assert obj.V1ObjectType == "V1StructureModel"
        assert obj.CRRecordKind == "v1_structure_model"
        assert obj.StructureCount == 1
        assert roundtrip.structure_rows[0].structure_id == "structure:bridge-01"
        assert obj.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_structure_model_reuses_existing_structure_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first_model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="",
                        station_start=0.0,
                        station_end=100.0,
                    ),
                )
            ],
        )
        second_model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:wall-01",
                        alignment_id="",
                        station_start=100.0,
                        station_end=160.0,
                    ),
                )
            ],
        )

        first = apply_v1_structure_model(document=doc, project=project, structure_model=first_model)
        second = apply_v1_structure_model(document=doc, project=project, structure_model=second_model)

        assert first.Name == second.Name
        assert second.StructureCount == 1
        assert list(second.StructureIds) == ["structure:wall-01"]
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_structure_preview_object_creates_visible_3d_preview() -> None:
    doc, project, tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        model = structure_preset_model_from_document("Bridge Segment", doc, project=project, alignment=alignment)

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview is not None
        assert preview.Name == "V1StructureShowPreview"
        assert preview.CRRecordKind == "v1_structure_show_preview"
        assert preview.V1ObjectType == "V1StructureShowPreview"
        assert preview.StructureModelId == "structures:main"
        assert int(preview.StructureCount) == 1
        assert int(preview.GeometrySpecCount) == 1
        assert preview.PreviewGeometrySource == "geometry_spec"
        assert preview.PreviewPathSource == "alignment"
        assert preview.Shape.BoundBox.XLength > 0.0
        assert preview.Shape.BoundBox.ZLength > 0.0
        assert preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_follows_3d_centerline_when_applied_sections_exist() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        applied = AppliedSectionSet(
            schema_version=1,
            project_id="proj-structure-editor",
            applied_section_set_id="applied-sections:main",
            station_rows=[
                AppliedSectionStationRow("station:0", 0.0, "section:0"),
                AppliedSectionStationRow("station:50", 50.0, "section:50"),
                AppliedSectionStationRow("station:100", 100.0, "section:100"),
            ],
            sections=[
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:0",
                    station=0.0,
                    frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=0.0),
                ),
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:50",
                    station=50.0,
                    frame=AppliedSectionFrame(station=50.0, x=50.0, y=0.0, z=5.0),
                ),
                AppliedSection(
                    schema_version=1,
                    project_id="proj-structure-editor",
                    applied_section_id="section:100",
                    station=100.0,
                    frame=AppliedSectionFrame(station=100.0, x=50.0, y=50.0, z=10.0),
                ),
            ],
        )
        create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=applied,
        )
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-01",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-01",
                        alignment_id="",
                        station_start=0.0,
                        station_end=100.0,
                        offset=0.0,
                    ),
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewPathSource == "3d_centerline"
        assert len(list(preview.Shape.Solids)) > 1
        assert preview.Shape.BoundBox.YLength > 40.0
        assert preview.Shape.BoundBox.ZLength > 10.0
    finally:
        App.closeDocument(doc.Name)


def test_structure_preview_uses_geometry_spec_dimensions_and_notes() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        model = StructureModel(
            schema_version=1,
            project_id="proj-structure-editor",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:bridge-wide",
                    structure_kind="bridge",
                    structure_role="interface",
                    placement=StructurePlacement(
                        placement_id="placement:bridge-wide",
                        alignment_id="",
                        station_start=0.0,
                        station_end=40.0,
                        offset=0.0,
                    ),
                    geometry_spec_ref="geometry-spec:bridge-wide",
                )
            ],
            geometry_spec_rows=[
                StructureGeometrySpec(
                    geometry_spec_id="geometry-spec:bridge-wide",
                    structure_ref="structure:bridge-wide",
                    shape_kind="deck_slab",
                    width=20.0,
                    height=2.5,
                    skew_angle_deg=7.5,
                    base_elevation=3.0,
                )
            ],
            bridge_geometry_spec_rows=[
                BridgeGeometrySpec(
                    geometry_spec_ref="geometry-spec:bridge-wide",
                    deck_width=22.0,
                    deck_thickness=2.8,
                )
            ],
        )

        preview = show_v1_structure_preview_object(doc, model, project=project)

        assert preview.PreviewGeometrySource == "geometry_spec"
        assert preview.Shape.BoundBox.YLength >= 21.0
        assert preview.Shape.BoundBox.ZLength >= 2.7
        assert any("warning|skew_angle|structure:bridge-wide|" in row for row in list(preview.PreviewReviewNotes))
    finally:
        App.closeDocument(doc.Name)


def test_structure_editor_command_resources_are_v1_structures() -> None:
    resources = CmdV1StructureEditor().GetResources()

    assert resources["MenuText"] == "Structures"
    assert "v1" in resources["ToolTip"]


def test_structure_detail_helpers_update_kind_specific_bridge_spec() -> None:
    fields = _kind_detail_field_specs("bridge")
    spec = _bridge_spec_from_detail(
        "geometry-spec:bridge-01",
        {
            "deck_width": "14.0",
            "deck_thickness": "1.5",
            "girder_depth": "2.0",
            "barrier_height": "1.1",
            "clearance_height": "5.5",
            "abutment_start_offset": "0",
            "abutment_end_offset": "0",
            "pier_station_refs": "120, 150",
            "approach_slab_length": "6.5",
            "bearing_elevation_mode": "profile_frame",
        },
    )
    rows = _replace_kind_spec([BridgeGeometrySpec("geometry-spec:old", deck_width=9.0)], spec)
    values = _kind_detail_values("bridge", "geometry-spec:bridge-01", rows, [], [])

    assert ("deck_width", "Deck Width") in fields
    assert len(rows) == 2
    assert values["deck_width"] == "14.000"
    assert values["pier_station_refs"] == "120, 150"


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 structure editor command contract tests completed.")
