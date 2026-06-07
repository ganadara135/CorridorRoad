from freecad.Corridor_Road.v1.services.builders.watertight_simulation_qa_service import (
    WatertightSimulationQaBuildRequest,
    WatertightSimulationQaService,
    WatertightSimulationQaSolidInput,
)


def test_watertight_simulation_qa_reports_first_slice_ready_state() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            terrain_bound_box=(-1.0, 12.0, -1.0, 8.0, -5.0, 5.0),
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                ),
            ],
        )
    )

    assert output.simulation_ready is True
    assert output.road_body_status == "ready"
    assert output.terrain_status == "ready"
    assert output.drainage_status == "ready"
    assert output.structure_status == "missing"
    assert output.solid_validity_status == "ok"
    assert output.geometry_contact_status == "ok"
    assert output.terrain_domain_status == "ok"
    assert output.port_connection_status == "not_checked"
    assert output.contact_issue_count == 0
    assert output.terrain_issue_count == 0
    assert output.port_issue_count == 0
    assert output.total_volume == 12.0
    assert output.missing_contexts == ["structure"]
    assert [row.family for row in output.family_rows] == ["drainage_pipeline_network_body", "road_body_envelope"]


def test_watertight_simulation_qa_blocks_missing_context_and_invalid_solids() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=False,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="BadRoad",
                    target_families=["road_body_envelope"],
                    volumes=[0.0],
                    valid_solid_statuses=[False],
                    shape_valid=False,
                )
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.drainage_status == "missing"
    assert output.terrain_status == "missing"
    assert output.solid_validity_status == "check"
    assert output.geometry_contact_status == "not_checked"
    assert output.invalid_output_count == 1
    assert output.zero_volume_output_count == 1
    assert {row.kind for row in output.diagnostic_rows} == {
        "missing_drainage",
        "missing_structure",
        "missing_terrain",
        "invalid_solid_outputs",
        "zero_volume_solid_outputs",
    }


def test_watertight_simulation_qa_blocks_disconnected_drainage_body() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(30.0, 32.0, 20.0, 22.0, 0.5, 1.0),
                ),
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.geometry_contact_status == "check"
    assert output.contact_issue_count == 1
    assert "drainage_body_disconnected_from_road_body" in {row.kind for row in output.diagnostic_rows}


def test_watertight_simulation_qa_accepts_intersection_patch_with_shared_region_context() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RegionBody",
                    target_families=["region_body"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                    source_refs=["region:primary-intersection"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="IntersectionPatch",
                    target_families=["intersection_patch_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                    source_refs=["intersection:t-01", "region:primary-intersection"],
                ),
            ],
        )
    )

    assert output.geometry_contact_status == "ok"
    assert output.contact_issue_count == 0
    assert "intersection_patch_body" in {row.family for row in output.family_rows}


def test_watertight_simulation_qa_blocks_intersection_patch_region_context_mismatch() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RegionBody",
                    target_families=["region_body"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                    source_refs=["region:primary-approach"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="IntersectionPatch",
                    target_families=["intersection_patch_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                    source_refs=["intersection:t-01", "region:primary-intersection"],
                ),
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.geometry_contact_status == "check"
    assert output.contact_issue_count == 1
    assert "intersection_patch_region_context_mismatch" in {row.kind for row in output.diagnostic_rows}
    mismatch_rows = [row for row in output.diagnostic_rows if row.kind == "intersection_patch_region_context_mismatch"]
    assert "patch_regions=region:primary-intersection" in mismatch_rows[0].message
    assert "road_regions=region:primary-approach" in mismatch_rows[0].message


def test_watertight_simulation_qa_reports_intersection_patch_nearest_road_gap() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RegionBody",
                    target_families=["region_body"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                    edge_xy_segments=[(0.0, 0.0, 10.0, 0.0)],
                    source_refs=["region:primary-intersection"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="IntersectionPatch",
                    target_families=["intersection_patch_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(14.0, 16.0, 2.0, 3.0, 0.5, 1.0),
                    edge_xy_segments=[(14.0, 2.0, 16.0, 2.0)],
                    source_refs=["intersection:t-01", "region:primary-intersection"],
                ),
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.geometry_contact_status == "check"
    assert output.contact_issue_count == 1
    disconnected_rows = [row for row in output.diagnostic_rows if row.kind == "intersection_patch_disconnected_from_road_body"]
    assert len(disconnected_rows) == 1
    assert "nearest_xy_gap=4.000" in disconnected_rows[0].message
    assert "nearest_edge_xy_gap=4.472" in disconnected_rows[0].message


def test_watertight_simulation_qa_reports_intersection_patch_edge_pair_gap() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RegionBody",
                    target_families=["region_body"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                    edge_xy_segments=[(0.0, 0.0, 10.0, 0.0)],
                    source_refs=["region:primary-intersection"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="IntersectionPatch",
                    target_families=["intersection_patch_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(1.0, 3.0, 1.0, 2.0, 0.5, 1.0),
                    edge_xy_segments=[(1.0, 2.0, 3.0, 2.0)],
                    source_refs=["intersection:t-01", "region:primary-intersection"],
                ),
            ],
        )
    )

    assert output.geometry_contact_status == "ok"
    assert output.contact_issue_count == 1
    edge_rows = [row for row in output.diagnostic_rows if row.kind == "intersection_patch_edge_pair_gap"]
    assert len(edge_rows) == 1
    assert edge_rows[0].severity == "warning"
    assert "nearest_edge_xy_gap=2.000" in edge_rows[0].message


def test_watertight_simulation_qa_reports_intersection_patch_trim_candidate_edges() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RegionBody",
                    target_families=["region_body"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                    edge_xy_segments=[(0.0, 3.0, 10.0, 3.0)],
                    source_refs=["region:primary-intersection"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="IntersectionPatch",
                    target_families=["intersection_patch_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(4.0, 6.0, 2.0, 4.0, 0.5, 1.0),
                    edge_xy_segments=[(5.0, 2.0, 5.0, 4.0)],
                    source_refs=["intersection:t-01", "region:primary-intersection"],
                ),
            ],
        )
    )

    assert output.geometry_contact_status == "ok"
    assert output.contact_issue_count == 1
    trim_rows = [row for row in output.diagnostic_rows if row.kind == "intersection_patch_trim_candidate"]
    assert len(trim_rows) == 1
    assert trim_rows[0].severity == "info"
    assert "candidate_edge_pairs=1" in trim_rows[0].message
    assert "nearest_edge_xy_gap=0.000" in trim_rows[0].message


def test_watertight_simulation_qa_blocks_road_outside_terrain_domain() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            terrain_bound_box=(100.0, 120.0, 100.0, 120.0, -5.0, 5.0),
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                ),
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.terrain_domain_status == "check"
    assert output.terrain_issue_count == 2
    assert "solid_outside_terrain_domain" in {row.kind for row in output.diagnostic_rows}


def test_watertight_simulation_qa_reports_port_connection_ready_state() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="StructureBody",
                    target_families=["structure_body"],
                    volumes=[1.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                    structure_refs=["structure:inlet-01"],
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                    structure_refs=["structure:inlet-01"],
                    source_refs=["connection:inlet-01:pipe-out"],
                ),
            ],
        )
    )

    assert output.simulation_ready is True
    assert output.structure_status == "ready"
    assert output.port_connection_status == "ok"
    assert output.port_issue_count == 0


def test_watertight_simulation_qa_blocks_missing_port_connection_context() -> None:
    output = WatertightSimulationQaService().build(
        WatertightSimulationQaBuildRequest(
            project_id="proj-1",
            terrain_ready=True,
            solid_inputs=[
                WatertightSimulationQaSolidInput(
                    output_ref="RoadBody",
                    target_families=["road_body_envelope"],
                    volumes=[10.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(0.0, 10.0, 0.0, 6.0, 0.0, 2.0),
                ),
                WatertightSimulationQaSolidInput(
                    output_ref="DrainageNetwork",
                    target_families=["drainage_pipeline_network_body"],
                    volumes=[2.0],
                    valid_solid_statuses=[True],
                    shape_valid=True,
                    bound_box=(5.0, 6.0, 2.0, 3.0, 0.5, 1.0),
                    structure_refs=["structure:inlet-01"],
                ),
            ],
        )
    )

    assert output.simulation_ready is False
    assert output.port_connection_status == "check"
    assert output.port_issue_count == 2
    assert {
        "drainage_port_connection_points_missing",
        "drainage_structure_body_missing_for_port",
    }.issubset({row.kind for row in output.diagnostic_rows})
