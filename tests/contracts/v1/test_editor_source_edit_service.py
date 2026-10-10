from freecad.Corridor_Road.v1.models.source.assembly_model import AssemblySubassemblyModel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageModel
from freecad.Corridor_Road.v1.models.source.structure_model import StructureModel, StructurePlacement, StructureRow
from freecad.Corridor_Road.v1.models.source.subassembly_definition_model import SubassemblyLibrary
from freecad.Corridor_Road.v1.services.editing import (
    prepare_assembly_edit,
    prepare_drainage_edit,
    prepare_structure_edit,
    prepare_subassembly_library_edit,
)


def test_supported_editor_models_prepare_without_qt_or_freecad_document() -> None:
    base = {"schema_version": 1, "project_id": "project:test"}
    prepared = [
        prepare_structure_edit(StructureModel(**base, structure_model_id="structure:main")),
        prepare_drainage_edit(DrainageModel(**base, drainage_model_id="drainage:main")),
        prepare_assembly_edit(AssemblySubassemblyModel(**base, assembly_id="assembly:main")),
        prepare_subassembly_library_edit(SubassemblyLibrary(**base, library_id="library:main")),
    ]

    assert all(row.accepted for row in prepared)
    assert [row.source_id for row in prepared] == [
        "structure:main",
        "drainage:main",
        "assembly:main",
        "library:main",
    ]


def test_duplicate_source_row_identity_is_a_typed_edit_diagnostic() -> None:
    placement = StructurePlacement("placement:1", "alignment:main", 0.0, 10.0)
    model = StructureModel(
        schema_version=1,
        project_id="project:test",
        structure_model_id="structure:main",
        structure_rows=[
            StructureRow("structure:1", "culvert", "crossing", placement),
            StructureRow("structure:1", "culvert", "crossing", placement),
        ],
    )

    prepared = prepare_structure_edit(model)

    assert not prepared.accepted
    assert prepared.diagnostics == (
        "error|row_id_duplicate|structure_id|structure:1",
    )
