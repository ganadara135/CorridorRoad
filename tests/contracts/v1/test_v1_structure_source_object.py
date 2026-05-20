import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_STRUCTURES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureConnectionPoint,
    StructureGeometrySpec,
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.objects.obj_structure import (
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
    validate_structure_model,
)


def _new_project_doc():
    doc = App.newDocument("V1StructureSourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="alignment:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:bridge-01",
                structure_kind="bridge",
                structure_role="interface",
                placement=StructurePlacement(
                    placement_id="placement:bridge-01",
                    alignment_id="alignment:main",
                    station_start=100.0,
                    station_end=180.0,
                    offset=0.0,
                    region_ref="region:bridge",
                ),
                geometry_spec_ref="geometry-spec:bridge-01",
                geometry_ref="",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:bridge-01",
                structure_ref="structure:bridge-01",
                shape_kind="deck_slab",
                width=12.0,
                height=1.4,
                length_mode="station_range",
                skew_angle_deg=5.0,
                vertical_position_mode="absolute_elevation",
                base_elevation=100.0,
                top_elevation=101.4,
                material="concrete",
                style_role="bridge",
            )
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec(
                geometry_spec_ref="geometry-spec:bridge-01",
                deck_width=12.0,
                deck_thickness=1.4,
                clearance_height=5.2,
                approach_slab_length=6.0,
                bearing_elevation_mode="absolute_elevation",
            )
        ],
        interaction_rule_rows=[
            StructureInteractionRule(
                interaction_rule_id="rule:bridge-section",
                structure_ref="structure:bridge-01",
                rule_kind="section_handoff",
                target_scope="section",
                priority=20,
            )
        ],
        influence_zone_rows=[
            StructureInfluenceZone(
                influence_zone_id="zone:bridge-01",
                structure_ref="structure:bridge-01",
                zone_kind="clearance",
                station_start=95.0,
                station_end=185.0,
                offset_min=-8.0,
                offset_max=8.0,
            )
        ],
    )


def test_create_or_update_v1_structure_model_object_routes_to_structures_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )

        assert obj.V1ObjectType == "V1StructureModel"
        assert obj.CRRecordKind == "v1_structure_model"
        assert obj.StructureModelId == "structures:main"
        assert obj.AlignmentId == "alignment:main"
        assert obj.StructureCount == 1
        assert list(obj.StructureIds) == ["structure:bridge-01"]
        assert list(obj.PlacementRegionRefs) == ["region:bridge"]
        assert list(obj.GeometrySpecRefs) == ["geometry-spec:bridge-01"]
        assert list(obj.GeometrySpecIds) == ["geometry-spec:bridge-01"]
        assert list(obj.GeometrySpecStructureRefs) == ["structure:bridge-01"]
        assert list(obj.GeometrySpecSkewAngles) == [5.0]
        assert list(obj.GeometrySpecVerticalPositionModes) == ["absolute_elevation"]
        assert len(list(obj.BridgeGeometrySpecRows)) == 1
        assert list(obj.RuleIds) == ["rule:bridge-section"]
        assert list(obj.InfluenceZoneIds) == ["zone:bridge-01"]
        assert obj.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_v1_structure_model_object_roundtrips_to_structure_model() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )

        model = to_structure_model(obj)

        assert model is not None
        assert model.structure_model_id == "structures:main"
        assert model.structure_rows[0].structure_id == "structure:bridge-01"
        assert model.structure_rows[0].geometry_spec_ref == "geometry-spec:bridge-01"
        assert model.structure_rows[0].placement.station_start == 100.0
        assert model.structure_rows[0].placement.region_ref == "region:bridge"
        assert model.geometry_spec_rows[0].width == 12.0
        assert model.geometry_spec_rows[0].skew_angle_deg == 5.0
        assert model.geometry_spec_rows[0].base_elevation == 100.0
        assert model.geometry_spec_rows[0].material == "concrete"
        assert model.bridge_geometry_spec_rows[0].deck_width == 12.0
        assert model.bridge_geometry_spec_rows[0].clearance_height == 5.2
        assert model.interaction_rule_rows[0].structure_ref == "structure:bridge-01"
        assert model.influence_zone_rows[0].offset_max == 8.0
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_structure_model_object_updates_existing_object() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        first = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=_sample_structure_model(),
        )
        updated_model = StructureModel(
            schema_version=1,
            project_id="proj-1",
            structure_model_id="structures:main",
            alignment_id="alignment:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="clearance_control",
                    placement=StructurePlacement(
                        placement_id="placement:culvert-01",
                        alignment_id="alignment:main",
                        station_start=200.0,
                        station_end=220.0,
                    ),
                )
            ],
        )
        second = create_or_update_v1_structure_model_object(
            document=doc,
            project=project,
            structure_model=updated_model,
        )

        assert first.Name == second.Name
        assert second.StructureCount == 1
        assert list(second.StructureIds) == ["structure:culvert-01"]
        assert find_v1_structure_model(doc) == second
    finally:
        App.closeDocument(doc.Name)


def test_structure_geometry_spec_validation_rejects_non_positive_dimensions() -> None:
    model = _sample_structure_model()
    model.geometry_spec_rows = [
        StructureGeometrySpec(
            geometry_spec_id="geometry-spec:bad",
            structure_ref="structure:bridge-01",
            width=0.0,
            height=-1.0,
        )
    ]

    diagnostics = validate_structure_model(model)

    assert any(row.startswith("error|geometry_width|geometry-spec:bad|") for row in diagnostics)
    assert any(row.startswith("error|geometry_height|geometry-spec:bad|") for row in diagnostics)


def test_structure_validation_does_not_require_region_when_region_model_exists() -> None:
    model = _sample_structure_model()
    model.structure_rows = [
        StructureRow(
            structure_id="structure:bridge-01",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement("placement:bridge-01", "alignment:main", 100.0, 180.0),
            geometry_spec_ref="geometry-spec:bridge-01",
        )
    ]

    diagnostics = validate_structure_model(model, region_model=object())

    assert not any("region_ref" in row or "Region" in row for row in diagnostics)


def test_structure_validation_ignores_legacy_region_ref() -> None:
    model = _sample_structure_model()
    model.structure_rows = [
        StructureRow(
            structure_id="structure:bridge-01",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement(
                "placement:bridge-01",
                "alignment:main",
                100.0,
                180.0,
                region_ref="region:missing",
            ),
            geometry_spec_ref="geometry-spec:bridge-01",
        )
    ]

    diagnostics = validate_structure_model(model, region_model=object())

    assert not any("missing_structure_region_ref" in row for row in diagnostics)


def test_structure_validation_reports_missing_native_and_kind_specs() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:bridge-missing-spec-ref",
                structure_kind="bridge",
                structure_role="interface",
                placement=StructurePlacement("placement:1", "alignment:main", 0.0, 10.0),
                reference_mode="native",
            ),
            StructureRow(
                structure_id="structure:culvert-missing-kind",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:2", "alignment:main", 10.0, 20.0),
                geometry_spec_ref="geometry-spec:culvert-missing-kind",
                reference_mode="native",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec:culvert-missing-kind",
                structure_ref="structure:culvert-missing-kind",
                width=3.0,
                height=2.0,
            )
        ],
    )

    diagnostics = validate_structure_model(model)

    assert any(row.startswith("error|geometry_spec_missing|structure:bridge-missing-spec-ref|") for row in diagnostics)
    assert any(row.startswith("error|culvert_geometry_spec_missing|structure:culvert-missing-kind|") for row in diagnostics)


def test_structure_validation_reports_skew_and_reference_conflict() -> None:
    model = _sample_structure_model()
    model.structure_rows = [
        StructureRow(
            structure_id="structure:bridge-01",
            structure_kind="bridge",
            structure_role="interface",
            placement=StructurePlacement("placement:bridge-01", "alignment:main", 100.0, 180.0),
            geometry_spec_ref="geometry-spec:bridge-01",
            geometry_ref="external:bridge-solid",
            reference_mode="native",
        )
    ]

    diagnostics = validate_structure_model(model)

    assert any(row.startswith("warning|unsupported_skew_angle|geometry-spec:bridge-01|") for row in diagnostics)
    assert any(row.startswith("warning|geometry_reference_conflict|structure:bridge-01|") for row in diagnostics)


def test_structure_validation_reports_kind_specific_required_fields() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
                geometry_spec_ref="geometry-spec:culvert-01",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", width=3.0, height=2.0)
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec("geometry-spec:culvert-01", barrel_shape="box", barrel_count=0, span=0.0, rise=0.0)
        ],
    )

    diagnostics = validate_structure_model(model)

    assert any(row.startswith("error|culvert_barrel_count|geometry-spec:culvert-01|") for row in diagnostics)
    assert any(row.startswith("error|culvert_span|geometry-spec:culvert-01|") for row in diagnostics)
    assert any(row.startswith("error|culvert_rise|geometry-spec:culvert-01|") for row in diagnostics)


def test_structure_validation_accepts_pipe_in_pipe_out_culvert_roles() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
                geometry_spec_ref="geometry-spec:culvert-01",
                native_type="pipe_culvert",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", width=1.2, height=1.2)
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec(
                "geometry-spec:culvert-01",
                barrel_shape="circular",
                barrel_count=1,
                diameter=1.2,
            )
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:pipe-in",
                structure_ref="structure:culvert-01",
                point_role="pipe_in",
                station=10.0,
                offset=0.0,
                diameter=1.2,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:pipe-out",
                structure_ref="structure:culvert-01",
                point_role="pipe_out",
                station=20.0,
                offset=0.0,
                diameter=1.2,
                shape_kind="circular",
            ),
        ],
    )

    diagnostics = validate_structure_model(model)

    assert not any(row.startswith("error|culvert_connection_points_incomplete|") for row in diagnostics)
    assert not any(row.startswith("error|connection_point_diameter|") for row in diagnostics)


def test_structure_validation_reports_drainage_endpoint_role_and_size_errors() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-01", "alignment:main", 10.0, 12.0),
                geometry_spec_ref="geometry-spec:inlet-01",
                native_type="inlet",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:inlet-01", "structure:inlet-01", width=1.0, height=1.0)
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-01:pipe-out",
                structure_ref="structure:inlet-01",
                point_role="pipe_out",
                station=13.0,
                offset=-5.0,
                diameter=0.0,
                shape_kind="circular",
            )
        ],
    )

    diagnostics = validate_structure_model(model)

    assert any(row.startswith("warning|inlet_collection_point_missing|structure:inlet-01|") for row in diagnostics)
    assert any(row.startswith("error|connection_point_outside_structure_station_range|connection:inlet-01:pipe-out|") for row in diagnostics)
    assert any(row.startswith("error|connection_point_diameter|connection:inlet-01:pipe-out|") for row in diagnostics)


def test_structure_validation_checks_region_station_boundary_when_region_ref_exists() -> None:
    model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement(
                    "placement:culvert-01",
                    "alignment:main",
                    40.0,
                    70.0,
                    region_ref="region:1",
                ),
                geometry_spec_ref="geometry-spec:culvert-01",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", width=3.0, height=2.0)
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec("geometry-spec:culvert-01", barrel_shape="box", barrel_count=1, span=3.0, rise=2.0)
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:upstream",
                structure_ref="structure:culvert-01",
                point_role="upstream",
                station=40.0,
                offset=0.0,
                width=3.0,
                height=2.0,
                shape_kind="box",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:downstream",
                structure_ref="structure:culvert-01",
                point_role="downstream",
                station=70.0,
                offset=0.0,
                width=3.0,
                height=2.0,
                shape_kind="box",
            ),
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        region_rows=[
            RegionRow(
                region_id="region:1",
                station_start=45.0,
                station_end=65.0,
                assembly_ref="assembly:road",
            )
        ],
    )

    diagnostics = validate_structure_model(model, region_model=region_model)

    assert any(row.startswith("error|structure_outside_region_station_range|structure:culvert-01|") for row in diagnostics)


def test_kind_specific_geometry_specs_roundtrip() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        source = StructureModel(
            schema_version=1,
            project_id="proj-1",
            structure_model_id="structures:main",
            structure_rows=[
                StructureRow(
                    structure_id="structure:culvert-01",
                    structure_kind="culvert",
                    structure_role="clearance_control",
                    placement=StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
                    geometry_spec_ref="geometry-spec:culvert-01",
                ),
                StructureRow(
                    structure_id="structure:wall-01",
                    structure_kind="retaining_wall",
                    structure_role="interface",
                    placement=StructurePlacement("placement:wall-01", "alignment:main", 30.0, 70.0),
                    geometry_spec_ref="geometry-spec:wall-01",
                ),
            ],
            geometry_spec_rows=[
                StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", width=3.0, height=2.0),
                StructureGeometrySpec("geometry-spec:wall-01", "structure:wall-01", width=0.9, height=3.0),
            ],
            culvert_geometry_spec_rows=[
                CulvertGeometrySpec(
                    geometry_spec_ref="geometry-spec:culvert-01",
                    barrel_shape="box",
                    barrel_count=2,
                    span=3.0,
                    rise=2.0,
                    wall_thickness=0.3,
                )
            ],
            retaining_wall_geometry_spec_rows=[
                RetainingWallGeometrySpec(
                    geometry_spec_ref="geometry-spec:wall-01",
                    wall_height=3.0,
                    wall_thickness=0.9,
                    footing_width=2.0,
                    retained_side="right",
                )
            ],
        )

        obj = create_or_update_v1_structure_model_object(document=doc, project=project, structure_model=source)
        model = to_structure_model(obj)

        assert model.culvert_geometry_spec_rows[0].barrel_count == 2
        assert model.retaining_wall_geometry_spec_rows[0].retained_side == "right"
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 structure source object contract tests completed.")
