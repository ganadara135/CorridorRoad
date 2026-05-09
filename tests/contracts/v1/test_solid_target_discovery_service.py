from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
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


def test_solid_target_discovery_separates_subbase_and_shoulder_component_bodies() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0),
                component_rows=[
                    AppliedSectionComponentRow("subbase:main", "subbase", width=6.0, thickness=0.3, material="crushed_stone"),
                    AppliedSectionComponentRow("shoulder:left", "shoulder", side="left", width=1.5, thickness=0.2, material="aggregate"),
                    AppliedSectionComponentRow("shoulder:right", "shoulder", side="right", width=0.0, thickness=0.2, material="aggregate"),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                frame=AppliedSectionFrame(100.0, 100.0, 0.0, 10.0),
                component_rows=[
                    AppliedSectionComponentRow("subbase:main", "subbase", width=6.0, thickness=0.3, material="crushed_stone"),
                    AppliedSectionComponentRow("shoulder:left", "shoulder", side="left", width=1.5, thickness=0.2, material="aggregate"),
                    AppliedSectionComponentRow("shoulder:right", "shoulder", side="right", width=1.5, thickness=0.2, material="aggregate"),
                ],
            ),
        ],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=applied,
            corridor_model=_corridor_model(),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    subbase = targets["solid-target:subbase:subbase-main"]
    shoulder_left = targets["solid-target:shoulder:shoulder-left"]
    shoulder_right = targets["solid-target:shoulder:shoulder-right"]
    assert subbase.target_family == "subbase_body"
    assert subbase.material_ref == "crushed_stone"
    assert subbase.readiness_status == "available"
    assert shoulder_left.target_family == "shoulder_body"
    assert shoulder_left.readiness_status == "available"
    assert shoulder_right.target_family == "shoulder_body"
    assert shoulder_right.readiness_status == "blocked"
    assert {row.kind for row in model.target_diagnostic_rows} == {"component_target_invalid_dimensions"}


def test_solid_target_discovery_blocks_lined_ditch_body_without_lining_policy() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:left-edge", 0.0, 5.0, 10.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 0.0, 6.2, 9.8, "ditch_surface", 6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow("ditch:left", "ditch", side="left", width=1.2, material=""),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                frame=AppliedSectionFrame(100.0, 100.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:left-edge", 100.0, 5.0, 10.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 100.0, 6.2, 9.8, "ditch_surface", 6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow("ditch:left", "ditch", side="left", width=1.2, material=""),
                ],
            ),
        ],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=applied,
            corridor_model=_corridor_model(),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    target = targets["solid-target:lined-ditch:left"]
    assert target.target_family == "lined_ditch_body"
    assert target.scope_kind == "drainage"
    assert target.component_ref == "ditch:left"
    assert target.drainage_ref == "lined_ditch:left"
    assert target.readiness_status == "blocked"
    assert target.station_start == 0.0
    assert target.station_end == 100.0
    assert {row.kind for row in model.target_diagnostic_rows} == {"lined_ditch_missing_lining_policy"}


def test_solid_target_discovery_marks_lined_ditch_body_available_when_lining_policy_exists() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:right-edge", 0.0, -5.0, 10.0, "ditch_surface", -5.0),
                    AppliedSectionPoint("ditch:right-flow", 0.0, -6.2, 9.8, "ditch_surface", -6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow(
                        "ditch:right",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"lining_thickness": "0.15"},
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                frame=AppliedSectionFrame(100.0, 100.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:right-edge", 100.0, -5.0, 10.0, "ditch_surface", -5.0),
                    AppliedSectionPoint("ditch:right-flow", 100.0, -6.2, 9.8, "ditch_surface", -6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow(
                        "ditch:right",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"lining_thickness": "0.15"},
                    ),
                ],
            ),
        ],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=applied,
            corridor_model=_corridor_model(),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    target = targets["solid-target:lined-ditch:right"]
    assert target.target_family == "lined_ditch_body"
    assert target.readiness_status == "available"
    assert target.material_ref == "concrete"
    assert model.target_diagnostic_rows == []


def test_solid_target_discovery_uses_drainage_model_owner_for_lined_ditch_body() -> None:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:right-edge", 0.0, -5.0, 10.0, "ditch_surface", -5.0),
                    AppliedSectionPoint("ditch:right-flow", 0.0, -6.2, 9.8, "ditch_surface", -6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow(
                        "ditch:right",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"lining_thickness": "0.15"},
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                frame=AppliedSectionFrame(100.0, 100.0, 0.0, 10.0),
                point_rows=[
                    AppliedSectionPoint("ditch:right-edge", 100.0, -5.0, 10.0, "ditch_surface", -5.0),
                    AppliedSectionPoint("ditch:right-flow", 100.0, -6.2, 9.8, "ditch_surface", -6.2),
                ],
                component_rows=[
                    AppliedSectionComponentRow(
                        "ditch:right",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"lining_thickness": "0.15"},
                    ),
                ],
            ),
        ],
    )
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:primary-lined-ditch",
                element_kind="ditch",
                side="right",
                station_start=0.0,
                station_end=100.0,
                assembly_component_ref="ditch:right",
                policy_set_ref="drainage-policy:lined-concrete",
            )
        ],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="proj-1",
            corridor_ref="corridor:main",
            applied_section_set=applied,
            corridor_model=_corridor_model(),
            drainage_model=drainage_model,
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    target = targets["solid-target:lined-ditch:right"]
    assert target.readiness_status == "available"
    assert target.drainage_ref == "drainage:primary-lined-ditch"
    assert "drainage:main" in target.source_refs
    assert "drainage:primary-lined-ditch" in target.source_refs
    assert "drainage-policy:lined-concrete" in target.source_refs
    assert "DrainageModel owner=drainage:primary-lined-ditch" in target.notes


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
