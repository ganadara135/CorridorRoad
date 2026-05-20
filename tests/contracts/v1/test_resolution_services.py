from freecad.Corridor_Road.v1.models.source.override_model import (
    OverrideModel,
    OverrideRow,
    OverrideScope,
    OverrideTarget,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DrainageElementRow,
    DrainageFlowRoute,
    DrainageModel,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureConnectionPoint,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.services.evaluation.drainage_resolution_service import (
    DrainageValidationService,
)
from freecad.Corridor_Road.v1.services.evaluation.override_resolution_service import (
    OverrideResolutionService,
)
from freecad.Corridor_Road.v1.services.evaluation.region_resolution_service import (
    RegionResolutionService,
    RegionValidationService,
)
from freecad.Corridor_Road.v1.services.evaluation.station_context_resolver import StationContextResolver


def test_region_resolution_picks_covering_region() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-1",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-a",
                station_start=0.0,
                station_end=50.0,
                template_ref="tmpl-a",
                priority=0,
            ),
            RegionRow(
                region_id="region-b",
                station_start=25.0,
                station_end=75.0,
                template_ref="tmpl-b",
                priority=1,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 30.0)

    assert result.active_region_id == "region-b"
    assert result.active_template_ref == "tmpl-b"


def test_region_resolution_preserves_domain_refs() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-overlap",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-normal",
                region_index=1,
                station_start=0.0,
                station_end=200.0,
                assembly_ref="assembly:road",
                template_ref="tmpl-road",
                priority=10,
            ),
            RegionRow(
                region_id="region-bridge",
                region_index=2,
                station_start=120.0,
                station_end=180.0,
                assembly_ref="assembly:bridge-deck",
                template_ref="tmpl-bridge",
                priority=80,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 150.0)

    assert result.active_region_id == "region-bridge"
    assert result.active_assembly_ref == "assembly:bridge-deck"
    assert result.overlap_region_ids == ["region-normal"]


def test_region_handoff_rows_are_station_ordered_context_contracts() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-handoff",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-road",
                region_index=1,
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:road",
                priority=10,
            ),
            RegionRow(
                region_id="region-ramp",
                region_index=2,
                station_start=100.0,
                station_end=180.0,
                assembly_ref="assembly:ramp",
                ramp_ref="ramp:entry-01",
                priority=70,
            ),
        ],
    )

    rows = RegionResolutionService().resolve_handoff_rows(region_model, [50.0, 120.0])

    assert [row.region_id for row in rows] == ["region-road", "region-ramp"]
    assert rows[1].ramp_ref == "ramp:entry-01"


def test_station_context_resolver_combines_region_structure_and_drainage_by_region() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        region_rows=[
            RegionRow("region:road", 0.0, 50.0, assembly_ref="assembly:road"),
            RegionRow("region:drainage", 50.0, 100.0, assembly_ref="assembly:ditch"),
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert",
                structure_kind="culvert",
                structure_role="crossing",
                placement=StructurePlacement(
                    placement_id="placement:culvert",
                    alignment_id="",
                    station_start=60.0,
                    station_end=80.0,
                    region_ref="region:drainage",
                ),
            ),
            StructureRow(
                structure_id="structure:other-region",
                structure_kind="wall",
                structure_role="retaining",
                placement=StructurePlacement(
                    placement_id="placement:wall",
                    alignment_id="",
                    station_start=60.0,
                    station_end=80.0,
                    region_ref="region:road",
                ),
            ),
        ],
    )
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:left",
                element_kind="ditch",
                side="left",
                region_ref="region:drainage",
                station_start=50.0,
                station_end=100.0,
            ),
            DrainageElementRow(
                drainage_element_id="drainage:right",
                element_kind="ditch",
                side="right",
                region_ref="region:road",
                station_start=50.0,
                station_end=100.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:left",
                from_element_ref="drainage:left",
                outlet_ref="drainage:outlet",
            )
        ],
    )

    context = StationContextResolver().resolve(
        region_model=region_model,
        structure_model=structure_model,
        drainage_model=drainage_model,
        station=70.0,
    )

    assert context.region_context.region_id == "region:drainage"
    assert context.region_context.assembly_ref == "assembly:ditch"
    assert context.structure_result.active_structure_ids == ["structure:culvert"]
    assert context.active_drainage_refs == ["drainage:left"]
    assert context.active_drainage_refs_by_side == {"left": ["drainage:left"]}
    assert context.active_flow_route_refs == ["flow-route:left"]


def test_drainage_validation_warns_when_flow_route_chain_has_no_outlet() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:open-chain",
        element_rows=[
            DrainageElementRow(
                "drainage:inlet-01",
                "inlet_reference",
                structure_ref="structure:inlet-01",
                station_start=10.0,
                station_end=11.0,
            ),
            DrainageElementRow(
                "drainage:culvert-01",
                "culvert_reference",
                structure_ref="structure:culvert-01",
                station_start=20.0,
                station_end=30.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute("flow-route:inlet-to-culvert", "drainage:inlet-01", "drainage:culvert-01"),
        ],
    )

    result = DrainageValidationService().validate(drainage_model)

    assert result.status == "warning"
    assert any(row.kind == "flow_route_no_reachable_outlet" for row in result.diagnostic_rows)


def test_drainage_validation_warns_when_flow_route_chain_has_multiple_outlets() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:multi-outlet",
        element_rows=[
            DrainageElementRow("drainage:inlet-01", "inlet_reference", station_start=10.0, station_end=11.0),
            DrainageElementRow("drainage:outlet-left", "outlet_reference", station_start=50.0, station_end=51.0),
            DrainageElementRow("drainage:outlet-right", "outlet_reference", station_start=55.0, station_end=56.0),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                "flow-route:left",
                "drainage:inlet-01",
                "drainage:outlet-left",
                outlet_ref="drainage:outlet-left",
            ),
            DrainageFlowRoute(
                "flow-route:right",
                "drainage:inlet-01",
                "drainage:outlet-right",
                outlet_ref="drainage:outlet-right",
            ),
        ],
    )

    result = DrainageValidationService().validate(drainage_model)

    assert result.status == "warning"
    diagnostic = next(row for row in result.diagnostic_rows if row.kind == "flow_route_multiple_reachable_outlets")
    assert "drainage:outlet-left" in diagnostic.notes
    assert "drainage:outlet-right" in diagnostic.notes


def test_drainage_validation_warns_when_structure_pipe_ports_are_unresolved() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:missing-ports",
        element_rows=[
            DrainageElementRow(
                "drainage:inlet-01",
                "inlet_reference",
                structure_ref="structure:inlet-01",
                station_start=10.0,
                station_end=11.0,
            ),
            DrainageElementRow(
                "drainage:outlet-01",
                "outlet_reference",
                structure_ref="structure:outlet-01",
                station_start=50.0,
                station_end=51.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                "flow-route:pipe-01",
                "drainage:inlet-01",
                "drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            ),
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:missing-ports",
        structure_rows=[
            StructureRow(
                "structure:inlet-01",
                "utility",
                "reference",
                StructurePlacement("placement:inlet-01", "", 10.0, 11.0),
                native_type="inlet",
            ),
            StructureRow(
                "structure:outlet-01",
                "utility",
                "reference",
                StructurePlacement("placement:outlet-01", "", 50.0, 51.0),
                native_type="outlet",
            ),
        ],
        connection_point_rows=[
            StructureConnectionPoint("connection:inlet-01:pipe-out", "structure:inlet-01", "pipe_out", 11.0, -4.0),
        ],
    )

    result = DrainageValidationService().validate(drainage_model, structure_model=structure_model)

    assert result.status == "warning"
    diagnostic = next(row for row in result.diagnostic_rows if row.kind == "flow_route_structure_ports_unresolved")
    assert "to_connection_point_ref=" in diagnostic.notes


def test_region_resolution_equal_priority_overlap_warns_and_uses_region_index() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-equal",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-b",
                region_index=2,
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-b",
                priority=20,
            ),
            RegionRow(
                region_id="region-a",
                region_index=1,
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-a",
                priority=20,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 50.0)

    assert result.active_region_id == "region-a"
    assert any(row.kind == "equal_priority_overlap" for row in result.diagnostic_rows)


def test_region_validation_reports_invalid_range_and_equal_priority_overlap() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-invalid",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-invalid",
                station_start=10.0,
                station_end=0.0,
                priority=5,
            ),
            RegionRow(
                region_id="region-a",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-a",
                priority=10,
            ),
            RegionRow(
                region_id="region-b",
                station_start=50.0,
                station_end=120.0,
                template_ref="tmpl-b",
                priority=10,
            ),
        ],
    )

    result = RegionValidationService().validate(region_model)

    assert result.status == "error"
    assert any(row.kind == "invalid_station_range" for row in result.diagnostic_rows)
    assert any(row.kind == "equal_priority_overlap" for row in result.diagnostic_rows)


def test_override_resolution_filters_by_station_and_region() -> None:
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-1",
        alignment_id="align-1",
        override_rows=[
            OverrideRow(
                override_id="ovr-a",
                override_kind="parameter_override",
                target=OverrideTarget(
                    target_id="target-a",
                    target_kind="section_parameter",
                    target_ref="lane-width",
                ),
                scope=OverrideScope(
                    scope_id="scope-a",
                    scope_kind="station_range",
                    station_start=0.0,
                    station_end=20.0,
                    region_ref="region-a",
                ),
                parameter="width",
                value=3.5,
            ),
            OverrideRow(
                override_id="ovr-b",
                override_kind="parameter_override",
                target=OverrideTarget(
                    target_id="target-b",
                    target_kind="section_parameter",
                    target_ref="lane-width",
                ),
                scope=OverrideScope(
                    scope_id="scope-b",
                    scope_kind="station_range",
                    station_start=21.0,
                    station_end=40.0,
                    region_ref="region-b",
                ),
                parameter="width",
                value=4.0,
            ),
        ],
    )

    result = OverrideResolutionService().resolve_station(
        override_model,
        10.0,
        region_id="region-a",
    )

    assert result.active_override_ids == ["ovr-a"]
