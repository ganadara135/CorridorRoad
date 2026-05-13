from freecad.Corridor_Road.v1.models.output.simulation_qa_output import SimulationQaOutput
from freecad.Corridor_Road.v1.services.builders.watertight_simulation_package_service import (
    WatertightSimulationPackageBuildRequest,
    WatertightSimulationPackageService,
)
from freecad.Corridor_Road.v1.services.builders.watertight_simulation_qa_service import WatertightSimulationQaSolidInput


def test_watertight_simulation_package_service_builds_ready_manifest() -> None:
    output = WatertightSimulationPackageService().build(
        WatertightSimulationPackageBuildRequest(
            project_id="proj-1",
            output_refs=["RoadBody", "DrainageNetwork"],
            simulation_qa_output=SimulationQaOutput(
                schema_version=1,
                project_id="proj-1",
                simulation_qa_output_id="simulation-qa:test",
                simulation_ready=True,
                terrain_status="ready",
            ),
            terrain_ref="TerrainMesh",
            terrain_bound_box=(-1.0, 12.0, -1.0, 8.0, -5.0, 5.0),
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    shape_valid=True,
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    shape_valid=True,
                    structure_refs=["structure:inlet-01"],
                    flow_route_refs=["flow-route:pipe-01"],
                ),
            ],
        )
    )

    assert output.package_status == "ready"
    assert output.simulation_ready is True
    assert output.simulation_qa_output_ref == "simulation-qa:test"
    assert output.terrain_status == "ready"
    assert output.terrain_ref == "TerrainMesh"
    assert output.terrain_bound_box == (-1.0, 12.0, -1.0, 8.0, -5.0, 5.0)
    assert output.output_count == 2
    assert output.total_volume == 12.0
    assert output.target_families == ["road_body_envelope", "drainage_pipeline_network_body"]
    assert output.solid_rows[1].structure_refs == ["structure:inlet-01"]
    assert output.solid_rows[1].flow_route_refs == ["flow-route:pipe-01"]


def test_watertight_simulation_package_service_blocks_when_qa_not_ready() -> None:
    output = WatertightSimulationPackageService().build(
        WatertightSimulationPackageBuildRequest(
            project_id="proj-1",
            simulation_qa_output=SimulationQaOutput(
                schema_version=1,
                project_id="proj-1",
                simulation_ready=False,
                missing_contexts=["drainage"],
            ),
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    shape_valid=True,
                )
            ],
        )
    )

    assert output.package_status == "blocked"
    assert output.simulation_ready is False
    assert output.missing_contexts == ["drainage"]
    assert output.output_count == 1
