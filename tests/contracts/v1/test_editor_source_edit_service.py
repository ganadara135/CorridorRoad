from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentModel
from freecad.Corridor_Road.v1.models.source.assembly_model import AssemblySubassemblyModel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageModel
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, ProfileModel
from freecad.Corridor_Road.v1.models.source.structure_model import StructureModel
from freecad.Corridor_Road.v1.models.source.subassembly_definition_model import SubassemblyLibrary
from freecad.Corridor_Road.v1.services.editing import (
    editor_view_model,
    prepare_alignment_edit,
    prepare_assembly_edit,
    prepare_drainage_edit,
    prepare_profile_edit,
    prepare_structure_edit,
    prepare_subassembly_library_edit,
)


def test_supported_editor_models_prepare_without_qt_or_freecad_document() -> None:
    base = {"schema_version": 1, "project_id": "project:test"}
    prepared = [
        prepare_structure_edit(StructureModel(**base, structure_model_id="structure:main")),
        prepare_profile_edit(ProfileModel(**base, profile_id="profile:main")),
        prepare_alignment_edit(AlignmentModel(**base, alignment_id="alignment:main")),
        prepare_drainage_edit(DrainageModel(**base, drainage_model_id="drainage:main")),
        prepare_assembly_edit(AssemblySubassemblyModel(**base, assembly_id="assembly:main")),
        prepare_subassembly_library_edit(SubassemblyLibrary(**base, library_id="library:main")),
    ]

    assert all(row.accepted for row in prepared)
    assert [row.source_id for row in prepared] == [
        "structure:main",
        "profile:main",
        "alignment:main",
        "drainage:main",
        "assembly:main",
        "library:main",
    ]
    assert all(editor_view_model(row).source is row.model for row in prepared)


def test_duplicate_source_row_identity_is_a_typed_edit_diagnostic() -> None:
    model = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:main",
        control_rows=[
            ProfileControlPoint("pvi:1", 0.0, 0.0),
            ProfileControlPoint("pvi:1", 10.0, 1.0),
        ],
    )

    prepared = prepare_profile_edit(model)

    assert not prepared.accepted
    assert prepared.diagnostics == (
        "error|row_id_duplicate|control_point_id|pvi:1",
    )
