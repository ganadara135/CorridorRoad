import FreeCAD as App

from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel, CorridorStationRow
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import _persist_incremental_corridor_model
from freecad.Corridor_Road.v1.models.source.assembly_model import AssemblySubassemblyModel, SubassemblySectionTemplate
from freecad.Corridor_Road.v1.models.source.structure_model import StructureModel, StructurePlacement, StructureRow
from freecad.Corridor_Road.v1.objects.obj_corridor import create_or_update_v1_corridor_model_object, to_corridor_model
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object, to_structure_model
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import (
    create_or_update_v1_assembly_subassembly_model_object,
    to_assembly_subassembly_model,
)
from freecad.Corridor_Road.v1.objects.persistence_payload_adapter import read_incremental_record


def _structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="project:persistence",
        structure_model_id="structures:main",
        source_refs=["alignment:main"],
        structure_rows=[
            StructureRow(
                structure_id="culvert:1",
                structure_kind="culvert",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id="placement:1",
                    alignment_id="alignment:main",
                    station_start=10.0,
                    station_end=20.0,
                ),
            )
        ],
    )


def test_source_payload_legacy_fallback_and_corruption_diagnostic() -> None:
    doc = App.newDocument("CRV1PersistenceFallback")
    try:
        obj = create_or_update_v1_structure_model_object(doc, _structure_model())
        assert to_structure_model(obj) == _structure_model()

        obj.ModelPayloadJson = ""
        obj.ModelPayloadChecksum = ""
        obj.SourceFingerprint = ""
        legacy = to_structure_model(obj)
        assert legacy is not None
        assert legacy.structure_rows[0].structure_id == "culvert:1"

        create_or_update_v1_structure_model_object(doc, _structure_model())
        obj.ModelPayloadChecksum = "tampered"
        assert to_structure_model(obj) is None
        assert any("payload_property_checksum_mismatch" in row for row in obj.PersistenceDiagnosticRows)
    finally:
        App.closeDocument(doc.Name)


def test_source_and_result_payloads_survive_freecad_save_and_reopen(tmp_path) -> None:
    doc = App.newDocument("CRV1PersistenceRoundTrip")
    path = tmp_path / "phase4-persistence-roundtrip.FCStd"
    try:
        create_or_update_v1_structure_model_object(doc, _structure_model())
        create_or_update_v1_assembly_subassembly_model_object(
            doc,
            AssemblySubassemblyModel(
                schema_version=1,
                project_id="project:persistence",
                assembly_id="assembly:main",
                source_refs=["subassembly-library:main"],
                template_rows=[SubassemblySectionTemplate(template_id="template:main", template_kind="road")],
            ),
        )
        create_or_update_v1_corridor_model_object(
            doc,
            CorridorModel(
                schema_version=1,
                project_id="project:persistence",
                corridor_id="corridor:main",
                applied_section_set_ref="applied-sections:main",
                source_refs=["alignment:main", "regions:main"],
                station_rows=[CorridorStationRow(station_row_id="station:1", station=10.0)],
            ),
        )
        doc.recompute()
        doc.saveAs(str(path))
    finally:
        App.closeDocument(doc.Name)

    reopened = App.openDocument(str(path))
    try:
        structure = to_structure_model(reopened.getObject("V1StructureModel"))
        assembly = to_assembly_subassembly_model(reopened.getObject("V1AssemblySubassemblyModel"))
        corridor_obj = reopened.getObject("V1CorridorModel")
        corridor = to_corridor_model(corridor_obj)
        build_record = read_incremental_record(corridor_obj)

        assert structure is not None and structure.structure_model_id == "structures:main"
        assert structure.source_refs == ["alignment:main"]
        assert assembly is not None and assembly.template_rows[0].template_id == "template:main"
        assert corridor is not None and corridor.applied_section_set_ref == "applied-sections:main"
        assert corridor.station_rows[0].station == 10.0
        assert build_record is not None and build_record.accepted is True
        assert build_record.consumed_result_refs == ("applied-sections:main",)
    finally:
        App.closeDocument(reopened.Name)


def test_corridor_persistence_reuses_unchanged_result_without_resetting_presentation() -> None:
    doc = App.newDocument("CRV1IncrementalCorridorPersistence")
    model = CorridorModel(
        schema_version=1,
        project_id="project:persistence",
        corridor_id="corridor:main",
        applied_section_set_ref="applied-sections:main",
        source_refs=["alignment:main"],
        station_rows=[CorridorStationRow(station_row_id="station:1", station=10.0)],
    )
    try:
        first = _persist_incremental_corridor_model(doc, None, model)
        first.Label = "Custom review label"
        first_payload = str(first.ModelPayloadJson)
        first_record = read_incremental_record(first)

        second = _persist_incremental_corridor_model(doc, None, model)

        assert second is first
        assert second.Label == "Custom review label"
        assert str(second.ModelPayloadJson) == first_payload
        assert read_incremental_record(second) == first_record
        assert second.BuildServiceVersion == "corridor-model-persistence:1"
        assert second.BuildAccepted is True
    finally:
        App.closeDocument(doc.Name)
