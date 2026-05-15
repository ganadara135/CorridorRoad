import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_DRAINAGE, ensure_project_tree
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DrainageElementRow,
    DrainageFlowRoute,
    DrainageModel,
    DrainagePolicySet,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.structure_model import (
    StructureConnectionPoint,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from freecad.Corridor_Road.v1.services.evaluation.drainage_resolution_service import DrainageValidationService


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        label="Drainage",
        source_refs=["region:1", "assembly:ditch-road"],
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:side-ditch-right",
                element_kind="ditch",
                alignment_ref="alignment:main",
                side="right",
                region_ref="region:1",
                assembly_component_ref="ditch:right",
                station_start=0.0,
                station_end=100.0,
                policy_set_ref="drainage-policy:lined-concrete",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outfall-main",
                element_kind="outfall_reference",
                structure_ref="outfall:1",
                connection_point_ref="connection:outfall-1:pipe-in",
                side="right",
                region_ref="region:1",
                station_start=99.0,
                station_end=100.0,
                policy_set_ref="drainage-policy:lined-concrete",
            )
        ],
        policy_rows=[
            DrainagePolicySet(
                policy_set_id="drainage-policy:lined-concrete",
                flow_intent="collect_and_convey",
                min_grade_rule="0.5%",
                collection_rule="roadside",
                discharge_rule="outfall",
                earthwork_priority="protect_lining",
            )
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:1",
                from_element_ref="drainage:side-ditch-right",
                to_element_ref="drainage:outfall-main",
                outlet_ref="drainage:outfall-main",
                direction="roadside_flow",
                risk_level="medium",
            )
        ],
    )


def test_create_or_update_v1_drainage_model_object_routes_to_drainage_tree() -> None:
    doc, project = _new_project_doc("V1DrainageModelObjectRouteTest")
    try:
        obj = create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=_drainage_model(),
        )

        assert obj.V1ObjectType == "V1DrainageModel"
        assert obj.CRRecordKind == "v1_drainage_model"
        tree = ensure_project_tree(project, include_references=False)
        assert obj.Name in {child.Name for child in tree[V1_TREE_DRAINAGE].Group}
    finally:
        App.closeDocument(doc.Name)


def test_v1_drainage_model_object_roundtrips_to_drainage_model() -> None:
    doc, project = _new_project_doc("V1DrainageModelObjectRoundtripTest")
    try:
        obj = create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=_drainage_model(),
        )

        model = to_drainage_model(obj)

        assert model is not None
        assert model.drainage_model_id == "drainage:main"
        assert model.source_refs == ["region:1", "assembly:ditch-road"]
        assert model.element_rows[0].drainage_element_id == "drainage:side-ditch-right"
        assert model.element_rows[0].side == "right"
        assert model.element_rows[0].region_ref == "region:1"
        assert model.element_rows[0].assembly_component_ref == "ditch:right"
        assert model.element_rows[1].connection_point_ref == "connection:outfall-1:pipe-in"
        assert list(obj.ElementConnectionPointRefs) == ["", "connection:outfall-1:pipe-in"]
        assert model.policy_rows[0].policy_set_id == "drainage-policy:lined-concrete"
        assert model.flow_route_rows[0].to_element_ref == "drainage:outfall-main"
        assert model.flow_route_rows[0].outlet_ref == "drainage:outfall-main"
        assert list(obj.FlowRouteOutletRefs) == ["drainage:outfall-main"]
        assert not hasattr(obj, "FlowRouteReceiverRefs")
        assert find_v1_drainage_model(doc) == obj
    finally:
        App.closeDocument(doc.Name)


def test_create_or_update_v1_drainage_model_object_updates_existing_object() -> None:
    doc, project = _new_project_doc("V1DrainageModelObjectUpdateTest")
    try:
        first = create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=_drainage_model(),
        )
        updated = DrainageModel(
            schema_version=1,
            project_id="proj-1",
            drainage_model_id="drainage:main",
            element_rows=[
                DrainageElementRow(
                    drainage_element_id="drainage:side-ditch-left",
                    element_kind="ditch",
                    side="left",
                    region_ref="region:2",
                    assembly_component_ref="ditch:left",
                    station_start=10.0,
                    station_end=50.0,
                )
            ],
        )

        second = create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=updated,
        )

        assert second == first
        assert second.ElementCount == 1
        assert list(second.DrainageElementIds) == ["drainage:side-ditch-left"]
        assert list(second.ElementSides) == ["left"]
        assert list(second.ElementRegionRefs) == ["region:2"]
        assert list(second.ElementAssemblyComponentRefs) == ["ditch:left"]
        assert to_drainage_model(second).element_rows[0].station_start == 10.0
    finally:
        App.closeDocument(doc.Name)


def test_drainage_validation_reports_duplicate_ids_invalid_ranges_and_missing_policy_refs() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:ditch-1",
                element_kind="ditch",
                side="outer",
                station_start=100.0,
                station_end=10.0,
                policy_set_ref="drainage-policy:missing",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:ditch-1",
                element_kind="ditch",
                station_start=0.0,
                station_end=20.0,
            ),
        ],
        policy_rows=[
            DrainagePolicySet(
                policy_set_id="drainage-policy:1",
                flow_intent="",
            ),
            DrainagePolicySet(
                policy_set_id="drainage-policy:1",
                flow_intent="collect_and_convey",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:1",
            ),
            DrainageFlowRoute(
                flow_route_id="flow-route:1",
            ),
        ],
    )

    result = DrainageValidationService().validate(model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "duplicate_drainage_element_id" in kinds
    assert "invalid_drainage_element_station_range" in kinds
    assert "missing_policy_set_ref" in kinds
    assert "missing_policy_ref" in kinds
    assert "duplicate_policy_set_id" in kinds
    assert "missing_flow_intent" in kinds
    assert "duplicate_flow_route_id" in kinds
    assert "unsupported_drainage_side" in kinds


def test_drainage_validation_reports_flow_route_broken_refs_without_requiring_intermediate_outlet() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:ditch-a",
                element_kind="ditch",
                station_start=0.0,
                station_end=10.0,
            ),
            DrainageElementRow(
                drainage_element_id="drainage:ditch-b",
                element_kind="ditch",
                station_start=10.0,
                station_end=20.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:missing-from",
                from_element_ref="drainage:missing",
                to_element_ref="drainage:ditch-b",
            ),
            DrainageFlowRoute(
                flow_route_id="flow-route:missing-to",
                from_element_ref="drainage:ditch-a",
                to_element_ref="drainage:missing",
                outlet_ref="bad-outlet",
            ),
            DrainageFlowRoute(
                flow_route_id="flow-route:no-outlet",
                from_element_ref="drainage:ditch-a",
                to_element_ref="drainage:ditch-b",
            ),
        ],
    )

    result = DrainageValidationService().validate(model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "missing_flow_route_from_element" in kinds
    assert "missing_flow_route_to_element" in kinds
    assert "missing_flow_route_outlet_ref" in kinds
    assert "flow_route_missing_outlet" not in kinds


def test_drainage_validation_reports_flow_route_self_loop_and_cycle() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow("drainage:a", "ditch", station_start=0.0, station_end=10.0),
            DrainageElementRow("drainage:b", "ditch", station_start=10.0, station_end=20.0),
            DrainageElementRow("drainage:c", "outfall_reference", station_start=20.0, station_end=21.0),
        ],
        flow_route_rows=[
            DrainageFlowRoute("flow-route:self", "drainage:a", "drainage:a", "drainage:c"),
            DrainageFlowRoute("flow-route:ab", "drainage:a", "drainage:b", "drainage:c"),
            DrainageFlowRoute("flow-route:ba", "drainage:b", "drainage:a", "drainage:c"),
        ],
    )

    result = DrainageValidationService().validate(model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "flow_route_self_loop" in kinds
    assert "flow_route_cycle" in kinds


def test_drainage_validation_reports_cross_region_flow_route_warning() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                "drainage:a",
                "ditch",
                region_ref="region:1",
                station_start=0.0,
                station_end=10.0,
                policy_set_ref="drainage-policy:1",
            ),
            DrainageElementRow(
                "drainage:b",
                "ditch",
                region_ref="region:2",
                station_start=10.0,
                station_end=20.0,
                policy_set_ref="drainage-policy:1",
            ),
            DrainageElementRow("drainage:outfall", "outfall_reference", station_start=20.0, station_end=21.0),
        ],
        policy_rows=[DrainagePolicySet("drainage-policy:1", "collect_and_convey")],
        flow_route_rows=[DrainageFlowRoute("flow-route:ab", "drainage:a", "drainage:b", "drainage:outfall")],
    )

    result = DrainageValidationService().validate(model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "warning"
    assert "flow_route_cross_region" in kinds


def test_drainage_validation_checks_structure_refs_against_structure_model() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:culvert",
                element_kind="culvert_reference",
                structure_ref="structure:missing",
                station_start=10.0,
                station_end=20.0,
                policy_set_ref="drainage-policy:1",
            )
        ],
        policy_rows=[DrainagePolicySet("drainage-policy:1", "cross_drainage_transfer")],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
            )
        ],
    )

    result = DrainageValidationService().validate(model, structure_model=structure_model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "missing_drainage_structure_ref" in kinds


def test_drainage_validation_checks_connection_point_refs_against_structure_model() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:culvert",
                element_kind="culvert_reference",
                structure_ref="structure:culvert-01",
                connection_point_ref="connection:culvert-01:missing",
                station_start=10.0,
                station_end=20.0,
                policy_set_ref="drainage-policy:1",
            )
        ],
        policy_rows=[DrainagePolicySet("drainage-policy:1", "cross_drainage_transfer")],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
            )
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:upstream",
                structure_ref="structure:culvert-01",
                point_role="upstream",
                station=10.0,
                offset=0.0,
            )
        ],
    )

    result = DrainageValidationService().validate(model, structure_model=structure_model)
    kinds = [row.kind for row in result.diagnostic_rows]

    assert result.status == "error"
    assert "missing_drainage_connection_point_ref" in kinds


def test_drainage_validation_checks_element_station_range_against_region() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inside",
                element_kind="ditch",
                region_ref="region:1",
                station_start=10.0,
                station_end=40.0,
                policy_set_ref="drainage-policy:1",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outside",
                element_kind="ditch",
                region_ref="region:1",
                station_start=45.0,
                station_end=70.0,
                policy_set_ref="drainage-policy:1",
            ),
        ],
        policy_rows=[
            DrainagePolicySet(
                policy_set_id="drainage-policy:1",
                flow_intent="collect_and_convey",
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        region_rows=[RegionRow("region:1", 0.0, 50.0)],
    )

    result = DrainageValidationService().validate(model, region_model=region_model)

    assert result.status == "error"
    assert [row.kind for row in result.diagnostic_rows] == ["drainage_element_outside_region_station_range"]
    assert "element_start=45" in result.diagnostic_rows[0].notes


def test_drainage_validation_allows_ui_precision_region_boundary_match() -> None:
    model = DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:left",
                element_kind="ditch",
                region_ref="region:1",
                station_start=0.0,
                station_end=203.108,
                policy_set_ref="drainage-policy:1",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:right",
                element_kind="ditch",
                region_ref="region:1",
                station_start=0.0,
                station_end=203.108,
                policy_set_ref="drainage-policy:1",
            ),
        ],
        policy_rows=[
            DrainagePolicySet(
                policy_set_id="drainage-policy:1",
                flow_intent="collect_and_convey",
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        region_rows=[RegionRow("region:1", 0.0, 203.1075)],
    )

    result = DrainageValidationService().validate(model, region_model=region_model)

    assert result.status == "ok"
    assert not result.diagnostic_rows


def test_v1_drainage_model_object_stores_validation_diagnostics() -> None:
    doc, project = _new_project_doc("V1DrainageModelObjectDiagnosticsTest")
    try:
        obj = create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:ditch-1",
                        element_kind="ditch",
                        station_start=5.0,
                        station_end=5.0,
                        policy_set_ref="drainage-policy:missing",
                    )
                ],
            ),
        )

        assert obj.ValidationStatus == "error"
        assert any("invalid_drainage_element_station_range" in row for row in list(obj.DiagnosticRows))
        assert any("missing_policy_set_ref" in row for row in list(obj.DiagnosticRows))
    finally:
        App.closeDocument(doc.Name)


def test_v1_drainage_model_object_removes_obsolete_route_properties() -> None:
    doc, project = _new_project_doc("V1DrainageModelObjectObsoleteRoutePropertiesTest")
    try:
        obj = doc.addObject("App::FeaturePython", "V1DrainageModel")
        obj.addProperty("App::PropertyStringList", "FlowRouteReceiverRefs", "Flow Routes", "receiver refs")
        obj.addProperty("App::PropertyStringList", "CollectionRegionIds", "Flow Routes", "legacy collection ids")
        obj.addProperty("App::PropertyFloatList", "CollectionStationStarts", "Flow Routes", "legacy collection starts")
        obj.FlowRouteReceiverRefs = ["outfall:old"]
        obj.CollectionRegionIds = ["drainage-collection:old"]
        obj.CollectionStationStarts = [0.0]

        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=_drainage_model(),
        )

        assert not hasattr(obj, "FlowRouteReceiverRefs")
        assert not hasattr(obj, "CollectionRegionIds")
        assert not hasattr(obj, "CollectionStationStarts")
        assert list(obj.FlowRouteOutletRefs) == ["drainage:outfall-main"]
    finally:
        App.closeDocument(doc.Name)
