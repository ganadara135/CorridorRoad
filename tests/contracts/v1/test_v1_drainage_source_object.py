import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, V1_TREE_DRAINAGE, ensure_project_tree
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DrainageCollectionRegion,
    DrainageElementRow,
    DrainageModel,
    DrainagePolicySet,
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
                offset_rule="right shoulder ditch",
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
        collection_region_rows=[
            DrainageCollectionRegion(
                collection_region_id="drainage-collection:1",
                region_kind="roadside_collection",
                station_start=0.0,
                station_end=100.0,
                alignment_ref="alignment:main",
                expected_receiver_ref="outfall:1",
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
        assert model.element_rows[0].offset_rule == "right shoulder ditch"
        assert model.policy_rows[0].policy_set_id == "drainage-policy:lined-concrete"
        assert model.collection_region_rows[0].expected_receiver_ref == "outfall:1"
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
                    offset_rule="left shoulder ditch",
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
        collection_region_rows=[
            DrainageCollectionRegion(
                collection_region_id="drainage-collection:1",
                region_kind="roadside",
                station_start=50.0,
                station_end=50.0,
            ),
            DrainageCollectionRegion(
                collection_region_id="drainage-collection:1",
                region_kind="roadside",
                station_start=0.0,
                station_end=10.0,
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
    assert "duplicate_collection_region_id" in kinds
    assert "invalid_collection_region_station_range" in kinds
    assert "unsupported_drainage_side" in kinds


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
