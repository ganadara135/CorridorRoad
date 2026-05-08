from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.services.builders.solid_target_discovery_service import (
    SolidTargetDiscoveryRequest,
    SolidTargetDiscoveryService,
)


def _applied_set() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:50", 50.0, "section:50"),
            AppliedSectionStationRow("station:100", 100.0, "section:100"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0),
                component_rows=[
                    AppliedSectionComponentRow(
                        "pavement:base",
                        "pavement_layer",
                        width=6.0,
                        thickness=0.2,
                        material="asphalt",
                    )
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:50",
                station=50.0,
                frame=AppliedSectionFrame(50.0, 50.0, 0.0, 10.0),
                component_rows=[
                    AppliedSectionComponentRow(
                        "pavement:base",
                        "pavement_layer",
                        width=6.0,
                        thickness=0.2,
                        material="asphalt",
                    )
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                frame=AppliedSectionFrame(100.0, 100.0, 0.0, 10.0),
                component_rows=[
                    AppliedSectionComponentRow(
                        "pavement:base",
                        "pavement_layer",
                        width=6.0,
                        thickness=0.2,
                        material="asphalt",
                    )
                ],
            ),
        ],
    )


def _corridor_model() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        applied_section_set_ref="applied:main",
    )


def _structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                "structure:wall",
                "retaining_wall",
                "retaining",
                StructurePlacement("placement:wall", "alignment:main", 20.0, 80.0),
                geometry_spec_ref="geometry:wall",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                "geometry:wall",
                "structure:wall",
                shape_kind="wall",
                width=0.4,
                height=3.0,
                material="concrete",
            )
        ],
    )


def test_solid_target_discovery_blocks_without_applied_sections_and_corridor() -> None:
    model = SolidTargetDiscoveryService().discover(SolidTargetDiscoveryRequest())

    assert len(model.target_rows) == 1
    assert model.target_rows[0].target_family == "road_body_envelope"
    assert model.target_rows[0].readiness_status == "blocked"
    assert {row.kind for row in model.target_diagnostic_rows} == {
        "missing_applied_sections",
        "missing_corridor_model",
    }


def test_solid_target_discovery_creates_road_body_envelope_candidate() -> None:
    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=_applied_set(),
            corridor_model=_corridor_model(),
        )
    )

    target = model.target_rows[0]
    assert target.target_id == "solid-target:road-body-envelope"
    assert target.target_family == "road_body_envelope"
    assert target.scope_kind == "whole_corridor"
    assert target.station_start == 0.0
    assert target.station_end == 100.0
    assert target.readiness_status == "available"


def test_solid_target_discovery_creates_region_body_candidates() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        region_rows=[
            RegionRow("region:1", 0.0, 50.0, assembly_ref="assembly:basic"),
            RegionRow("region:2", 50.0, 100.0, structure_ref="structure:wall"),
        ],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=_applied_set(),
            corridor_model=_corridor_model(),
            region_model=region_model,
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    assert "solid-target:road-body-envelope" in targets
    assert targets["solid-target:region-body:region-1"].region_ref == "region:1"
    assert targets["solid-target:region-body:region-1"].readiness_status == "available"
    assert targets["solid-target:region-body:region-2"].structure_ref == "structure:wall"


def test_solid_target_discovery_creates_pavement_layer_component_candidates() -> None:
    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=_applied_set(),
            corridor_model=_corridor_model(),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    target = targets["solid-target:pavement-layer:pavement-base"]
    assert target.target_family == "pavement_layer_body"
    assert target.scope_kind == "assembly_component"
    assert target.component_ref == "pavement:base"
    assert target.material_ref == "asphalt"
    assert target.station_start == 0.0
    assert target.station_end == 100.0
    assert target.readiness_status == "available"


def test_solid_target_discovery_creates_structure_body_candidates() -> None:
    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=_applied_set(),
            corridor_model=_corridor_model(),
            structure_model=_structure_model(),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    target = targets["solid-target:structure-body:structure-wall"]
    assert target.target_family == "structure_body"
    assert target.scope_kind == "structure"
    assert target.structure_ref == "structure:wall"
    assert target.material_ref == "concrete"
    assert target.station_start == 20.0
    assert target.station_end == 80.0
    assert target.readiness_status == "available"
