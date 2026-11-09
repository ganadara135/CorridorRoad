"""Culverts and the structures around them moved to Drainage: older Structure data is dropped, not broken."""

from dataclasses import dataclass, field

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
    is_removed_drainage_structure,
)
from freecad.Corridor_Road.v1.objects.obj_structure import (
    create_or_update_v1_structure_model_object,
    to_structure_model,
    validate_structure_model,
)
from freecad.Corridor_Road.v1.objects.persistence_payload_adapter import write_model_payload
from freecad.Corridor_Road.v1.services.editing.editor_source_service import (
    prepare_structure_edit,
    without_removed_drainage_structures,
)


def _row(structure_id: str, kind: str, start: float, end: float, *, native_type: str = "") -> StructureRow:
    return StructureRow(
        structure_id=structure_id,
        structure_kind=kind,
        structure_role="interface",
        placement=StructurePlacement(f"placement:{structure_id}", "alignment:main", start, end),
        geometry_spec_ref=f"geometry-spec:{structure_id}",
        native_type=native_type,
    )


def _model() -> StructureModel:
    ids = ("structure:bridge-01", "structure:culvert-01", "structure:inlet-01")
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="alignment:main",
        structure_rows=[
            _row("structure:bridge-01", "bridge", 100.0, 180.0, native_type="bridge_deck"),
            _row("structure:culvert-01", "culvert", 10.0, 20.0, native_type="pipe_culvert"),
            _row("structure:inlet-01", "utility", 30.0, 32.0, native_type="inlet"),
        ],
        geometry_spec_rows=[StructureGeometrySpec(f"geometry-spec:{structure_id}", structure_id, width=3.0, height=2.0) for structure_id in ids],
        bridge_geometry_spec_rows=[BridgeGeometrySpec("geometry-spec:structure:bridge-01", deck_width=10.0, deck_thickness=1.2)],
    )


def test_a_row_of_a_drainage_kind_or_native_type_is_recognised() -> None:
    assert is_removed_drainage_structure(_row("a", "culvert", 0.0, 1.0))
    assert is_removed_drainage_structure(_row("b", "utility", 0.0, 1.0, native_type="headwall"))
    assert is_removed_drainage_structure(_row("c", "Inlet", 0.0, 1.0))
    assert not is_removed_drainage_structure(_row("d", "bridge", 0.0, 1.0, native_type="bridge_deck"))
    assert not is_removed_drainage_structure(_row("e", "retaining_wall", 0.0, 1.0))
    assert not is_removed_drainage_structure(_row("f", "utility", 0.0, 1.0))


def test_the_removed_rows_go_with_their_specs_and_nothing_else_changes() -> None:
    cleaned, removed = without_removed_drainage_structures(_model())

    assert removed == ("structure:culvert-01", "structure:inlet-01")
    assert [row.structure_id for row in cleaned.structure_rows] == ["structure:bridge-01"]
    assert [row.geometry_spec_id for row in cleaned.geometry_spec_rows] == ["geometry-spec:structure:bridge-01"]
    assert [row.geometry_spec_ref for row in cleaned.bridge_geometry_spec_rows] == ["geometry-spec:structure:bridge-01"]

    same, nothing = without_removed_drainage_structures(cleaned)
    assert same is cleaned and nothing == ()


def test_applying_drops_the_rows_and_says_which() -> None:
    prepared = prepare_structure_edit(_model())

    assert [row.structure_id for row in prepared.model.structure_rows] == ["structure:bridge-01"]
    notes = [row for row in prepared.diagnostics if row.startswith("warning|structure_moved_to_drainage|")]
    assert [row.split("|")[2] for row in notes] == ["structure:culvert-01", "structure:inlet-01"]
    assert prepared.accepted

    clean = prepare_structure_edit(prepare_structure_edit(_model()).model)
    assert not any("structure_moved_to_drainage" in row for row in clean.diagnostics)


def test_validation_warns_about_a_row_that_belongs_to_drainage_now() -> None:
    diagnostics = validate_structure_model(_model())

    moved = [row for row in diagnostics if row.startswith("warning|structure_moved_to_drainage|")]
    assert [row.split("|")[2] for row in moved] == ["structure:culvert-01", "structure:inlet-01"]
    assert not any(row.startswith("warning|structure_moved_to_drainage|structure:bridge-01") for row in diagnostics)


@dataclass
class _StructureModelWithCulvertSpecs(StructureModel):
    """What a Structure payload held before the culvert specs and connection points were removed."""

    culvert_geometry_spec_rows: list = field(default_factory=list)
    connection_point_rows: list = field(default_factory=list)


def test_a_structure_saved_with_culvert_specs_and_connection_points_restores_and_drops_their_properties() -> None:
    doc = App.newDocument("V1StructureBeforeCulvertRemoval")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    try:
        model = _model()
        obj = create_or_update_v1_structure_model_object(doc, project=project, structure_model=model)
        obj.addProperty("App::PropertyStringList", "CulvertGeometrySpecRows", "Kind Geometry Specs", "from before")
        obj.CulvertGeometrySpecRows = ["{}"]
        obj.addProperty("App::PropertyStringList", "ConnectionPointRows", "Connection Points", "from before")
        obj.ConnectionPointRows = ["{}"]
        old = _StructureModelWithCulvertSpecs(
            **{name: getattr(model, name) for name in model.__dataclass_fields__},
            culvert_geometry_spec_rows=[{"geometry_spec_ref": "geometry-spec:structure:culvert-01", "barrel_shape": "box"}],
            connection_point_rows=[
                {
                    "connection_point_id": "connection:bridge-01:a",
                    "structure_ref": "structure:bridge-01",
                    "point_role": "left_port",
                    "station": 100.0,
                    "offset": 0.0,
                }
            ],
        )
        write_model_payload(
            obj,
            old,
            model_type="StructureModel",
            row_fields=("structure_rows", "geometry_spec_rows", "culvert_geometry_spec_rows", "connection_point_rows"),
        )

        restored = to_structure_model(obj)
        assert restored == model

        create_or_update_v1_structure_model_object(doc, project=project, structure_model=model)
        assert not hasattr(obj, "CulvertGeometrySpecRows")
        assert not hasattr(obj, "ConnectionPointRows")
    finally:
        App.closeDocument(doc.Name)
