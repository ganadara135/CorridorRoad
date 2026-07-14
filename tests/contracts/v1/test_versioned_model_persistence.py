import json

from freecad.Corridor_Road.v1.models.persistence import (
    checksum_for,
    restore_model_payload,
    serialize_model_payload,
)
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.models.source.structure_model import StructureModel, StructurePlacement, StructureRow


def test_nested_structure_model_roundtrips_through_versioned_payload() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="project:test",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:bridge-1",
                structure_kind="bridge",
                structure_role="interface",
                placement=StructurePlacement(
                    placement_id="placement:bridge-1",
                    alignment_id="alignment:main",
                    station_start=10.0,
                    station_end=40.0,
                ),
            )
        ],
    )
    payload = serialize_model_payload(
        model,
        model_type="StructureModel",
        row_fields=("structure_rows",),
        required_refs=("project_id", "structure_model_id"),
    )

    restored = restore_model_payload(
        payload.to_json(),
        expected_model_type="StructureModel",
        model_class=StructureModel,
    )

    assert restored.accepted
    assert restored.model == model
    assert restored.source_fingerprint == payload.source_fingerprint


def test_restore_rejects_checksum_and_row_count_corruption() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="project:test",
        drainage_model_id="drainage:main",
        element_rows=[DrainageElementRow("ditch:1", "ditch")],
    )
    payload = serialize_model_payload(
        model,
        model_type="DrainageModel",
        row_fields=("element_rows",),
    )
    corrupted = json.loads(payload.to_json())
    corrupted["data"]["element_rows"] = []

    checksum_result = restore_model_payload(
        json.dumps(corrupted),
        expected_model_type="DrainageModel",
        model_class=DrainageModel,
    )
    assert not checksum_result.accepted
    assert checksum_result.diagnostics[0].code == "payload_checksum_mismatch"

    corrupted["checksum"] = checksum_for(
        {
            key: corrupted[key]
            for key in (
                "payload_schema_version",
                "model_type",
                "model_schema_version",
                "data",
                "row_counts",
                "required_refs",
            )
        }
    )
    count_result = restore_model_payload(
        json.dumps(corrupted),
        expected_model_type="DrainageModel",
        model_class=DrainageModel,
    )
    assert not count_result.accepted
    assert count_result.diagnostics[0].code == "row_count_mismatch"


def test_v1_payload_migrates_explicitly_to_v2() -> None:
    model = DrainageModel(schema_version=1, project_id="project:test", drainage_model_id="drainage:main")
    payload = serialize_model_payload(model, model_type="DrainageModel")
    legacy = json.loads(payload.to_json())
    legacy["payload_schema_version"] = 1
    legacy.pop("row_counts")
    legacy.pop("required_refs")
    legacy["checksum"] = checksum_for(
        {
            "payload_schema_version": 1,
            "model_type": legacy["model_type"],
            "model_schema_version": legacy["model_schema_version"],
            "data": legacy["data"],
            "row_counts": {},
            "required_refs": [],
        }
    )

    restored = restore_model_payload(
        json.dumps(legacy),
        expected_model_type="DrainageModel",
        model_class=DrainageModel,
    )

    assert restored.accepted
    assert restored.migrated
    assert restored.payload_schema_version == 2
