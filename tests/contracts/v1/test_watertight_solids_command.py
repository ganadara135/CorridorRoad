import json
import math
import tempfile
from pathlib import Path

import FreeCAD as App
import Part
from types import SimpleNamespace

import freecad.Corridor_Road.v1.commands.cmd_watertight_solids as watertight_cmd
from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_EXCHANGE_PACKAGES,
    V1_TREE_REPORTS,
    V1_TREE_WATERTIGHT_SOLIDS,
    ensure_project_tree,
)
from freecad.Corridor_Road.init_gui import corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel, CorridorSamplingPolicy, CorridorStationRow
from freecad.Corridor_Road.v1.models.result.applied_section_solid_profile import (
    AppliedSectionSolidProfile,
    AppliedSectionSolidProfileSet,
    SolidProfileNode,
)
from freecad.Corridor_Road.v1.models.result.surface_model import SurfaceModel, SurfaceRow
from freecad.Corridor_Road.v1.models.output.watertight_solid_output import WatertightSolidOutput, WatertightSolidOutputRow
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageFlowRoute, DrainageModel
from freecad.Corridor_Road.v1.models.source.structure_model import (
    CulvertGeometrySpec,
    StructureConnectionPoint,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_corridor import create_or_update_v1_corridor_model_object
from freecad.Corridor_Road.v1.objects.obj_drainage import create_or_update_v1_drainage_model_object
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object
from freecad.Corridor_Road.v1.objects.obj_surface import create_or_update_v1_surface_model_object
from freecad.Corridor_Road.v1.objects.obj_watertight_solid import create_or_update_v1_watertight_solid_output_object
from freecad.Corridor_Road.v1.objects.obj_simulation_qa import to_simulation_qa_output
from freecad.Corridor_Road.v1.objects.obj_simulation_package import to_simulation_package_output
from freecad.Corridor_Road.v1.commands.cmd_watertight_solids import (
    CmdV1WatertightSolids,
    V1WatertightSolidsTaskPanel,
    WATERTIGHT_SOLIDS_BLOCKED_MESSAGE,
    WATERTIGHT_SOLIDS_COMMAND_ID,
    _drainage_pipeline_network_solid_shape,
    drainage_watertight_handoff_summary,
    _profile_set_on_centerline3d,
    discover_watertight_solid_targets,
    export_document_simulation_package_json,
    watertight_solid_prerequisite_status,
)

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _sample_sections(*, include_component: bool = False, include_lined_ditch: bool = False) -> AppliedSectionSet:
    component_rows = [
        AppliedSectionComponentRow(
            "pavement:base",
            "pavement_layer",
            side="center",
            width=6.0,
            thickness=0.25,
            material="asphalt",
        )
    ] if include_component else []
    if include_lined_ditch:
        component_rows.append(
            AppliedSectionComponentRow(
                "ditch:right",
                "ditch",
                side="right",
                width=1.2,
                material="concrete",
                parameters={"lining_thickness": "0.15"},
            )
        )

    def point_rows(station: float) -> list[AppliedSectionPoint]:
        if not include_lined_ditch:
            return []
        return [
            AppliedSectionPoint("ditch:right-edge", station, -5.0, 10.0, "ditch_surface", -5.0),
            AppliedSectionPoint("ditch:right-mid", station, -5.6, 9.7, "ditch_surface", -5.6),
            AppliedSectionPoint("ditch:right-flow", station, -6.2, 9.8, "ditch_surface", -6.2),
        ]

    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                point_rows=point_rows(0.0),
                component_rows=list(component_rows),
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                point_rows=point_rows(20.0),
                component_rows=list(component_rows),
            ),
        ],
    )


def _sample_corridor() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        applied_section_set_ref="sections:main",
        surface_build_refs=["surface:main"],
        sampling_policy=CorridorSamplingPolicy("corridor:main:sampling", 20.0),
        station_rows=[
            CorridorStationRow("station:0", 0.0, source_reason="section:0"),
            CorridorStationRow("station:20", 20.0, source_reason="section:20"),
        ],
    )


def _sample_surface() -> SurfaceModel:
    return SurfaceModel(
        schema_version=1,
        project_id="proj-1",
        surface_model_id="surface:main",
        corridor_id="corridor:main",
        surface_rows=[
            SurfaceRow("corridor:main:design", "design_surface", "corridor:main:design:tin"),
            SurfaceRow("corridor:main:subgrade", "subgrade_surface", "corridor:main:subgrade:tin"),
        ],
    )


def _populate_ready_build_corridor_outputs(
    doc,
    project,
    *,
    include_component: bool = False,
    include_lined_ditch: bool = False,
) -> None:
    create_or_update_v1_applied_section_set_object(
        doc,
        project=project,
        applied_section_set=_sample_sections(include_component=include_component, include_lined_ditch=include_lined_ditch),
    )
    create_or_update_v1_corridor_model_object(doc, project=project, corridor_model=_sample_corridor())
    create_or_update_v1_surface_model_object(doc, project=project, surface_model=_sample_surface())


def _pipeline_structure_model(*, include_native_specs: bool = False) -> StructureModel:
    geometry_spec_rows = []
    inlet_spec_ref = "geometry-spec:inlet-01" if include_native_specs else ""
    outlet_spec_ref = "geometry-spec:outlet-01" if include_native_specs else ""
    if include_native_specs:
        geometry_spec_rows = [
            StructureGeometrySpec(
                "geometry-spec:inlet-01",
                "structure:inlet-01",
                shape_kind="inlet_box",
                width=1.2,
                height=1.0,
                material="concrete",
            ),
            StructureGeometrySpec(
                "geometry-spec:outlet-01",
                "structure:outlet-01",
                shape_kind="outlet_headwall",
                width=1.4,
                height=1.1,
                material="concrete",
            ),
        ]
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:pipeline",
        structure_rows=[
            StructureRow(
                "structure:inlet-01",
                "utility",
                "reference",
                StructurePlacement("placement:inlet-01", "alignment:main", 30.0, 32.0),
                geometry_spec_ref=inlet_spec_ref,
                native_type="inlet" if include_native_specs else "",
            ),
            StructureRow(
                "structure:outlet-01",
                "utility",
                "reference",
                StructurePlacement("placement:outlet-01", "alignment:main", 90.0, 92.0),
                geometry_spec_ref=outlet_spec_ref,
                native_type="outlet" if include_native_specs else "",
            ),
        ],
        geometry_spec_rows=geometry_spec_rows,
        connection_point_rows=[
            StructureConnectionPoint(
                "connection:inlet-01:pipe-out",
                "structure:inlet-01",
                "pipe_out",
                station=32.0,
                offset=-4.5,
                invert_elevation=44.2,
                diameter=0.6,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                "connection:outlet-01:pipe-in",
                "structure:outlet-01",
                "pipe_in",
                station=90.0,
                offset=-6.0,
                invert_elevation=43.6,
                diameter=0.6,
                shape_kind="circular",
            ),
        ],
    )


def _pipeline_drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:pipeline",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                connection_point_ref="connection:inlet-01:pipe-out",
                station_start=30.0,
                station_end=32.0,
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outlet-01",
                element_kind="outfall_reference",
                structure_ref="structure:outlet-01",
                connection_point_ref="connection:outlet-01:pipe-in",
                station_start=90.0,
                station_end=92.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:pipe-01",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            )
        ],
    )


def _populate_pipeline_sources(doc, project) -> None:
    create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())
    create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())


def _populate_pipeline_sources_with_structure_specs(doc, project) -> None:
    create_or_update_v1_structure_model_object(
        doc,
        project=project,
        structure_model=_pipeline_structure_model(include_native_specs=True),
    )
    create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())


def _drainage_handoff_mixed_model() -> DrainageModel:
    base = _pipeline_drainage_model()
    return DrainageModel(
        schema_version=1,
        project_id="proj-1",
        drainage_model_id="drainage:mixed-handoff",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:ditch-right",
                element_kind="ditch",
                side="right",
                station_start=0.0,
                station_end=30.0,
            ),
            *list(base.element_rows),
            DrainageElementRow(
                drainage_element_id="drainage:node-no-port",
                element_kind="junction_reference",
                structure_ref="structure:no-port",
                station_start=44.0,
                station_end=45.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:capture-01",
                from_element_ref="drainage:ditch-right",
                to_element_ref="drainage:inlet-01",
                outlet_ref="drainage:outlet-01",
            ),
            *list(base.flow_route_rows),
            DrainageFlowRoute(
                flow_route_id="flow-route:unresolved-01",
                from_element_ref="drainage:node-no-port",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            ),
        ],
    )


def _structure_body_source_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:body-test",
        structure_rows=[
            StructureRow(
                "structure:culvert-01",
                "culvert",
                "drainage_crossing",
                StructurePlacement("placement:culvert-01", "alignment:main", 30.0, 36.0, offset=-4.5),
                geometry_spec_ref="geometry-spec:culvert-01",
                native_type="box_culvert",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                "geometry-spec:culvert-01",
                "structure:culvert-01",
                shape_kind="box",
                width=1.5,
                height=1.2,
                material="concrete",
            )
        ],
    )


def _pipe_culvert_structure_body_source_model(*, wall_thickness: float = 0.0) -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:pipe-culvert-test",
        structure_rows=[
            StructureRow(
                "structure:pipe-culvert-01",
                "culvert",
                "drainage_crossing",
                StructurePlacement("placement:pipe-culvert-01", "alignment:main", 40.0, 46.0, offset=-3.0),
                geometry_spec_ref="geometry-spec:pipe-culvert-01",
                native_type="pipe_culvert",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                "geometry-spec:pipe-culvert-01",
                "structure:pipe-culvert-01",
                shape_kind="circular",
                width=1.2,
                height=1.2,
                material="concrete",
            )
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec(
                "geometry-spec:pipe-culvert-01",
                barrel_shape="circular",
                diameter=1.2,
                wall_thickness=wall_thickness,
            )
        ],
    )


def _external_structure_body_source_model(geometry_ref: str) -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:external-test",
        structure_rows=[
            StructureRow(
                "structure:external-01",
                "culvert",
                "external_body",
                StructurePlacement("placement:external-01", "alignment:main", 50.0, 56.0, offset=-2.0),
                geometry_ref=geometry_ref,
                reference_mode="source_ref",
                geometry_source_mode="external_ref",
            )
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                "connection:external-01:pipe-in",
                "structure:external-01",
                "pipe_in",
                station=50.0,
                offset=-2.0,
                invert_elevation=40.0,
                diameter=0.8,
                shape_kind="circular",
            )
        ],
    )


def _create_structure_body_output(doc, project, *, structure_ref: str, object_name: str):
    output = WatertightSolidOutput(
        schema_version=1,
        project_id="proj-1",
        watertight_solid_output_id=f"watertight-solids:{object_name}",
        corridor_id="corridor:main",
        solid_rows=[
            WatertightSolidOutputRow(
                output_object_id=f"watertight-solid:{object_name}",
                target_id=f"solid-target:structure-body:{structure_ref.split(':')[-1]}",
                target_family="structure_body",
                scope_kind="structure",
                station_start=30.0,
                station_end=32.0,
                structure_ref=structure_ref,
                validation_status="ok",
                is_watertight=True,
                is_valid_solid=True,
                volume=1.0,
                face_count=6,
                edge_count=12,
            )
        ],
    )
    return create_or_update_v1_watertight_solid_output_object(
        document=doc,
        watertight_solid_output=output,
        shape=Part.makeBox(1.0, 1.0, 1.0),
        project=project,
        object_name=object_name,
        label=f"Watertight Solid - {structure_ref}",
    )


def test_watertight_solids_resources_are_final_v1_stage() -> None:
    resources = CmdV1WatertightSolids().GetResources()

    assert resources["MenuText"] == "Watertight Solids"
    assert "topology-first" in resources["ToolTip"]


def test_watertight_solids_panel_routes_existing_output_objects_to_tree() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsExistingOutputTreeRouteTest")
    try:
        output = WatertightSolidOutput(
            schema_version=1,
            project_id="proj-1",
            watertight_solid_output_id="watertight-solids:existing",
            corridor_id="corridor:main",
            solid_rows=[
                WatertightSolidOutputRow(
                    output_object_id="watertight-solid:existing",
                    target_id="solid-target:existing",
                    target_family="road_body_envelope",
                    scope_kind="whole_corridor",
                    station_start=0.0,
                    station_end=10.0,
                    generated_object_ref="V1WatertightSolidOutput_Existing",
                    validation_status="ok",
                    is_watertight=True,
                    is_valid_solid=True,
                    volume=1.0,
                    face_count=6,
                    edge_count=12,
                    profile_count=2,
                )
            ],
        )
        obj = create_or_update_v1_watertight_solid_output_object(
            document=doc,
            watertight_solid_output=output,
            project=None,
            object_name="V1WatertightSolidOutput_Existing",
            label="Watertight Solid - Existing",
        )
        tree = ensure_project_tree(project, include_references=False)
        assert obj.Name not in _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])

        V1WatertightSolidsTaskPanel(document=doc)

        assert obj.Name in _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_toolbar_is_after_ai_assist() -> None:
    commands = corridorroad_workflow_toolbar_commands()

    assert commands[-2:] == ["CorridorRoad_AIAssist", WATERTIGHT_SOLIDS_COMMAND_ID]


def test_watertight_solids_prerequisites_block_without_build_corridor() -> None:
    doc = App.newDocument("V1WatertightSolidsMissingPrereqTest")
    try:
        status = watertight_solid_prerequisite_status(doc)

        assert status.ready is False
        assert WATERTIGHT_SOLIDS_BLOCKED_MESSAGE in status.messages
        assert status.applied_sections_ready is False
        assert status.corridor_model_ready is False
        assert status.surface_model_ready is False
        assert discover_watertight_solid_targets(doc).target_rows[0].readiness_status == "blocked"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_prerequisites_ready_after_build_corridor_objects_exist() -> None:
    doc = App.newDocument("V1WatertightSolidsReadyPrereqTest")
    try:
        doc.addObject("App::FeaturePython", "V1AppliedSectionSet")
        doc.addObject("App::FeaturePython", "V1CorridorModel")
        doc.addObject("App::FeaturePython", "V1SurfaceModel")

        status = watertight_solid_prerequisite_status(doc)
        target_model = discover_watertight_solid_targets(doc)

        assert status.ready is True
        assert status.applied_sections_ready is True
        assert status.corridor_model_ready is True
        assert status.surface_model_ready is True
        assert target_model.target_rows[0].target_family == "road_body_envelope"
        assert target_model.target_rows[0].readiness_status == "blocked"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_prerequisites_block_on_build_parametric_error_diagnostics() -> None:
    doc, project = _new_project_doc("V1WatertightSolidsBuildParametricDiagnosticBlockTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        diagnostic = doc.addObject("App::FeaturePython", "V1CorridorDaylightSurfacePreviewDiagnostic")
        diagnostic.addProperty("App::PropertyString", "CRRecordKind", "V1").CRRecordKind = "v1_corridor_surface_preview_diagnostic"
        diagnostic.addProperty("App::PropertyString", "SurfaceRole", "V1").SurfaceRole = "daylight"
        diagnostic.addProperty("App::PropertyString", "SurfaceKind", "V1").SurfaceKind = "daylight_surface"
        diagnostic.addProperty("App::PropertyString", "PreviewStatus", "V1").PreviewStatus = "error"
        diagnostic.addProperty("App::PropertyString", "PreviewDiagnostic", "V1").PreviewDiagnostic = "Slope Face Surface preview was not created."

        status = watertight_solid_prerequisite_status(doc)

        assert status.ready is False
        assert status.applied_sections_ready is True
        assert status.corridor_model_ready is True
        assert status.surface_model_ready is True
        assert status.build_parametric_ready is False
        assert status.build_parametric_diagnostic_count == 1
        assert WATERTIGHT_SOLIDS_BLOCKED_MESSAGE in status.messages
        assert any("daylight" in message and "blocking" in message for message in status.messages)
        assert status.table_rows()[-1] == (
            "Build Parametric Diagnostics",
            "Missing",
            "Resolve blocking Build Parametric diagnostics.",
        )
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_shows_blocked_state_and_disables_build_buttons() -> None:
    _ensure_qapp()
    doc = App.newDocument("V1WatertightSolidsPanelBlockedTest")
    try:
        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert WATERTIGHT_SOLIDS_BLOCKED_MESSAGE in panel._status.toPlainText()
        assert panel._target_table.rowCount() == 1
        assert panel._validate_button.isEnabled() is False
        assert panel._build_selected_button.isEnabled() is False
        assert panel._build_enabled_button.isEnabled() is False
        assert panel._show_button.isEnabled() is False
        assert panel._hide_button.isEnabled() is False
        assert panel._focus_button.isEnabled() is False
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solid_profiles_are_reprojected_to_centerline3d_frame() -> None:
    profile_set = AppliedSectionSolidProfileSet(
        schema_version=1,
        project_id="proj-1",
        profile_set_id="solid-profiles:test",
        target_ref="solid-target:lined-ditch",
        source_refs=["applied:main"],
        profile_rows=[
            AppliedSectionSolidProfile(
                profile_id="solid-profile:1",
                target_id="solid-target:lined-ditch",
                station=100.0,
                applied_section_ref="applied-section:100",
                node_rows=[
                    SolidProfileNode(
                        node_id="node:top",
                        semantic_role="top",
                        x=100.0,
                        y=-5.0,
                        z=1.0,
                        lateral_offset=-5.0,
                        vertical_offset=0.25,
                    )
                ],
                is_closed=True,
            )
        ],
    )
    original_frame = watertight_cmd._centerline3d_coordinate_frame
    try:
        watertight_cmd._centerline3d_coordinate_frame = lambda _document: {
            "adapter": lambda station, offset: (1000.0 + float(station), 2000.0 + float(offset), 30.0),
            "coordinate_mode": "centerline3d_result",
        }

        converted = _profile_set_on_centerline3d(None, profile_set)
    finally:
        watertight_cmd._centerline3d_coordinate_frame = original_frame

    node = converted.profile_rows[0].node_rows[0]
    assert node.x == 1100.0
    assert node.y == 1995.0
    assert node.z == 30.25
    assert "centerline3d_result" in converted.source_refs
    assert "path_source=centerline3d_result" in converted.profile_rows[0].notes


def test_watertight_solids_panel_selects_available_target_and_tracks_enabled_state() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelTargetSelectionTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert panel._target_table.rowCount() == 1
        assert panel._validate_button.isEnabled() is False

        panel._target_table.selectRow(0)
        assert panel._selected_target_id == "solid-target:road-body-envelope"
        assert panel._validate_button.isEnabled() is True
        assert panel._build_selected_button.isEnabled() is False
        assert panel._build_enabled_button.isEnabled() is False

        enabled_item = panel._target_table.item(0, 0)
        enabled_item.setCheckState(QtCore.Qt.Checked)

        assert panel._target_state_by_id["solid-target:road-body-envelope"].enabled is True
        assert "Enabled targets: 1" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_validate_builds_profile_and_edge_network_counts() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelValidateTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)

        panel._validate_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        assert state.validation_status == "ok"
        assert state.profile_count == 2
        assert state.face_count == 6
        assert state.edge_count == 12
        assert panel._target_table.item(0, 1).text() == "Road Body Envelope"
        assert panel._target_table.item(0, 2).text() == "Envelope"
        assert panel._target_table.item(0, 6).text() == "ok"
        assert panel._target_table.item(0, 7).text() == "2"
        assert panel._target_table.item(0, 8).text() == "6"
        assert panel._target_table.item(0, 9).text() == "12"
        assert "Selected validation: ok; profiles=2; faces=6; edges=12" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_build_selected_creates_output_object() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelBuildSelectedTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)
        panel._validate_button.click()

        assert panel._build_selected_button.isEnabled() is True
        panel._build_selected_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        obj = doc.getObject(state.output_object_ref)
        qa_obj = doc.getObject("V1SimulationQaOutput")
        assert state.build_status == "built"
        assert state.volume > 0.0
        assert obj is not None
        assert qa_obj is not None
        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.SolidCount == 1
        assert obj.Shape.Volume > 0.0
        assert list(obj.TargetIds) == ["solid-target:road-body-envelope"]
        tree = ensure_project_tree(project, include_references=False)
        assert obj.Name in _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])
        assert qa_obj.Name in _group_names(tree[V1_TREE_REPORTS])
        assert qa_obj.V1ObjectType == "V1SimulationQaOutput"
        assert qa_obj.CRRecordKind == "v1_simulation_qa_output"
        assert qa_obj.OutputCount == 1
        assert qa_obj.RoadBodyStatus == "ready"
        assert qa_obj.TerrainStatus == "ready"
        assert qa_obj.TerrainDomainStatus == "not_checked"
        assert qa_obj.TerrainIssueCount == 0
        assert qa_obj.PortConnectionStatus == "not_checked"
        assert qa_obj.PortIssueCount == 0
        assert qa_obj.DrainageStatus == "missing"
        assert qa_obj.SimulationReady is False
        assert list(qa_obj.FamilyNames) == ["road_body_envelope"]
        assert list(qa_obj.MissingContexts) == ["drainage", "structure"]
        qa_output = to_simulation_qa_output(qa_obj)
        assert qa_output is not None
        assert qa_output.road_body_status == "ready"
        assert qa_output.terrain_domain_status == "not_checked"
        assert qa_output.port_connection_status == "not_checked"
        assert qa_output.output_count == 1
        assert panel._qa_family_table.rowCount() == 1
        assert panel._qa_family_table.item(0, 0).text() == "road_body_envelope"
        assert panel._qa_family_table.item(0, 1).text() == "ready"
        assert panel._qa_diagnostic_table.rowCount() == 2
        assert {panel._qa_diagnostic_table.item(row, 1).text() for row in range(panel._qa_diagnostic_table.rowCount())} == {
            "missing_drainage",
            "missing_structure",
        }
        assert panel._target_table.item(0, 10).text() == "built"
        assert panel._target_table.item(0, 11).text() != "-"
        assert panel._target_table.item(0, 12).text() == state.output_object_ref
        assert panel._show_button.isEnabled() is True
        assert panel._hide_button.isEnabled() is True
        assert panel._focus_button.isEnabled() is True
        assert panel._build_package_button.isEnabled() is True
        panel._build_package_button.click()
        package_obj = doc.getObject("V1SimulationPackageOutput")
        assert package_obj is not None
        assert panel._export_package_button.isEnabled() is True
        assert package_obj.V1ObjectType == "V1SimulationPackageOutput"
        assert package_obj.CRRecordKind == "v1_simulation_package_output"
        assert package_obj.PackageStatus == "blocked"
        assert package_obj.OutputCount == 1
        assert package_obj.SimulationQaOutputRef == "simulation-qa:watertight-solids"
        assert package_obj.TerrainStatus == "ready"
        assert package_obj.TerrainRef
        assert list(package_obj.SolidOutputRefs) == [obj.Name]
        assert list(package_obj.SolidTargetFamilies) == ["road_body_envelope"]
        assert package_obj.Name in _group_names(tree[V1_TREE_EXCHANGE_PACKAGES])
        package_output = to_simulation_package_output(package_obj)
        assert package_output is not None
        assert package_output.package_status == "blocked"
        assert package_output.terrain_status == "ready"
        assert package_output.terrain_ref == package_obj.TerrainRef
        assert package_output.output_count == 1
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "simulation_package.json"
            export_info = export_document_simulation_package_json(str(export_path), document=doc, project=project)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            assert export_info["simulation_package_output_id"] == "simulation-package:watertight-solids"
            assert export_info["package_status"] == "blocked"
            assert export_info["terrain_status"] == "ready"
            assert export_info["terrain_ref"] == package_obj.TerrainRef
            assert export_info["solid_row_count"] == 1
            assert export_info["geometry_file_count"] == 1
            assert export_info["geometry_export_status"] == "exported"
            assert export_info["geometry_directory"] == str(export_path.with_name("simulation_package_geometry"))
            assert exported["terrain_context"]["status"] == "ready"
            assert exported["terrain_context"]["ref"] == package_obj.TerrainRef
            assert exported["solid_rows"][0]["output_ref"] == obj.Name
            assert exported["solid_rows"][0]["target_families"] == ["road_body_envelope"]
            assert exported["solid_rows"][0]["geometry_object_ref"] == obj.Name
            assert exported["solid_rows"][0]["geometry_format"] == "brep"
            assert exported["solid_rows"][0]["geometry_status"] == "exported"
            assert exported["geometry_files"][0]["output_ref"] == obj.Name
            geometry_file = Path(temp_dir) / exported["solid_rows"][0]["geometry_file"]
            assert geometry_file.is_file()
            assert export_info["geometry_file_paths"] == [str(geometry_file)]
        status_text = panel._status.toPlainText()
        assert "Simulation QA:" in status_text
        assert "road_body=ready" in status_text
        assert "terrain=ready" in status_text
        assert "drainage=missing" in status_text
        assert "simulation_ready=no" in status_text
        assert "Simulation package:" in status_text
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_simulation_package_records_actual_terrain_shape_context() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsTerrainShapePackageTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        terrain = doc.addObject("Part::Feature", "DesignTerrain")
        terrain.Shape = Part.makeBox(80.0, 80.0, 10.0, App.Vector(-10.0, -20.0, -10.0))

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)
        panel._validate_button.click()
        panel._build_selected_button.click()
        panel._build_package_button.click()

        package_obj = doc.getObject("V1SimulationPackageOutput")
        qa_obj = doc.getObject("V1SimulationQaOutput")
        assert package_obj is not None
        assert qa_obj is not None
        assert package_obj.TerrainStatus == "ready"
        assert package_obj.TerrainRef == terrain.Name
        assert package_obj.TerrainBoundBox == "-10|70|-20|60|-10|0"
        assert qa_obj.TerrainDomainStatus == "ok"

        package_output = to_simulation_package_output(package_obj)
        assert package_output is not None
        assert package_output.terrain_ref == terrain.Name
        assert package_output.terrain_bound_box == (-10.0, 70.0, -20.0, 60.0, -10.0, 0.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "simulation_package.json"
            export_document_simulation_package_json(str(export_path), document=doc, project=project)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            assert exported["terrain_context"]["ref"] == terrain.Name
            assert exported["terrain_context"]["bound_box"] == [-10.0, 70.0, -20.0, 60.0, -10.0, 0.0]
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_watertight_solids_panel_show_hide_focus_controls_built_output_object() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelShowHideFocusTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        panel._target_table.selectRow(0)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id["solid-target:road-body-envelope"]
        obj = doc.getObject(state.output_object_ref)
        assert obj is not None

        panel._hide_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is False
        assert f"Hidden solid: {obj.Name}" in panel._status.toPlainText()

        panel._show_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert f"Shown solid: {obj.Name}" in panel._status.toPlainText()

        if getattr(obj, "ViewObject", None) is not None:
            obj.ViewObject.Visibility = False
        panel._focus_button.click()
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert f"Focused solid: {obj.Name}" in panel._status.toPlainText()

        if getattr(obj, "ViewObject", None) is not None:
            obj.ViewObject.Visibility = False
        panel._focus_target_row_output(panel._target_table.item(0, 1))
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is True
        assert panel._selected_target_id == "solid-target:road-body-envelope"
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_panel_show_hide_focus_preserves_lined_ditch_side_context() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelLinedDitchFocusTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project, include_lined_ditch=True)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        lined_ditch_row = _target_table_row(panel, "solid-target:lined-ditch:right")
        assert lined_ditch_row >= 0
        assert panel._target_table.item(lined_ditch_row, 1).text() == "Drainage Lined Ditch Solid - lined_ditch:right"
        assert panel._target_table.item(lined_ditch_row, 2).text() == "Drainage: Lined Ditch"
        assert "lined_ditch:right" in panel._target_table.item(lined_ditch_row, 4).text()
        assert "ditch:right" in panel._target_table.item(lined_ditch_row, 4).text()
        assert "concrete" in panel._target_table.item(lined_ditch_row, 4).text()

        panel._target_table.selectRow(lined_ditch_row)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id["solid-target:lined-ditch:right"]
        obj = doc.getObject(state.output_object_ref)
        assert state.build_status == "built"
        assert obj is not None
        assert obj.DrainageRefs == ["lined_ditch:right"]

        panel._hide_button.click()
        assert f"Hidden solid: {obj.Name}" in panel._status.toPlainText()
        assert "drainage=lined_ditch:right" in panel._status.toPlainText()
        assert "side=right" in panel._status.toPlainText()
        assert "component=ditch:right" in panel._status.toPlainText()
        assert "material=concrete" in panel._status.toPlainText()

        panel._show_button.click()
        assert f"Shown solid: {obj.Name}" in panel._status.toPlainText()
        assert "drainage=lined_ditch:right" in panel._status.toPlainText()

        panel._focus_target_row_output(panel._target_table.item(lined_ditch_row, 1))
        assert panel._selected_target_id == "solid-target:lined-ditch:right"
        assert f"Focused solid: {obj.Name}" in panel._status.toPlainText()
        assert "side=right" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_discovery_reads_document_drainage_model_owner() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelDrainageOwnerTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project, include_lined_ditch=True)
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:side-ditch-right",
                        element_kind="ditch",
                        side="right",
                        station_start=0.0,
                        station_end=20.0,
                        policy_set_ref="drainage-policy:lined-concrete",
                    )
                ],
            ),
        )

        panel = V1WatertightSolidsTaskPanel(document=doc)
        state = panel._target_state_by_id["solid-target:lined-ditch:right"]

        assert state.target_row.drainage_ref == "drainage:side-ditch-right"
        assert "drainage:main" in state.target_row.source_refs
        assert "drainage-policy:lined-concrete" in state.target_row.source_refs
        assert "drainage:side-ditch-right" in panel._target_table.item(_target_table_row(panel, state.target_id), 4).text()
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_status_summarizes_drainage_solid_handoff_readiness() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsDrainageHandoffSummaryTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_handoff_mixed_model())

        panel = V1WatertightSolidsTaskPanel(document=doc)
        summary = drainage_watertight_handoff_summary(doc, target_model=panel._target_model)
        status_text = panel._status.toPlainText()

        assert summary.readiness_status == "blocked"
        assert summary.flow_route_count == 3
        assert summary.capture_only_route_count == 1
        assert summary.pipe_candidate_count == 1
        assert summary.unresolved_port_route_count == 1
        assert summary.pipe_segment_target_count == 1
        assert summary.pipeline_network_target_count == 1
        assert "Drainage Solid QA:" in status_text
        assert "status=blocked" in status_text
        assert "capture_only=1" in status_text
        assert "pipe_candidates=1" in status_text
        assert "unresolved_ports=1" in status_text
        assert "network_fuse=compound_first_slice" in status_text
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_discovers_and_builds_drainage_pipeline_body() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsDrainagePipelineBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        _populate_pipeline_sources(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:drainage-pipeline:pipeline-segment-flow-route-pipe-01"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        assert panel._target_table.item(row_index, 1).text() == "Drainage Pipe Segment Solid - flow-route:pipe-01"
        assert panel._target_table.item(row_index, 2).text() == "Drainage: Pipe Segment"
        assert "flow-route:pipe-01" in panel._target_table.item(row_index, 4).text()
        assert panel._target_state_by_id[target_id].target_row.readiness_status == "available"

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()

        state = panel._target_state_by_id[target_id]
        assert state.validation_status == "ok"
        assert state.profile_count >= 2
        assert state.volume > 0.0
        assert "caps=2" in state.validation_message

        panel._build_selected_button.click()

        obj = doc.getObject(state.output_object_ref)
        assert state.build_status == "built"
        assert obj is not None
        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.TargetFamilies == ["drainage_pipeline_body"]
        assert obj.DrainageRefs == ["pipeline-segment:flow-route-pipe-01"]
        assert obj.FlowRouteRefs == ["flow-route:pipe-01"]
        assert obj.Shape.Volume > 0.0
        assert obj.Name in _group_names(ensure_project_tree(project, include_references=False)[V1_TREE_WATERTIGHT_SOLIDS])
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_discovers_and_builds_structure_body_from_native_spec() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsStructureBodyBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_structure_body_source_model())

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:structure-body:structure-culvert-01"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        assert panel._target_table.item(row_index, 1).text() == "Structure Body Solid - structure:culvert-01"
        assert panel._target_table.item(row_index, 2).text() == "Structure Body"
        assert panel._target_state_by_id[target_id].target_row.readiness_status == "available"

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()

        state = panel._target_state_by_id[target_id]
        assert state.validation_status == "ok"
        assert state.volume > 0.0
        assert "Structure body solid candidate ready" in state.validation_message

        panel._build_selected_button.click()

        obj = doc.getObject(state.output_object_ref)
        assert state.build_status == "built"
        assert obj is not None
        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.TargetFamilies == ["structure_body"]
        assert obj.StructureRefs == ["structure:culvert-01"]
        assert obj.Shape.Volume > 0.0
        assert state.watertight_output.solid_rows[0].material_ref == "concrete"
        assert state.watertight_output.solid_rows[0].path_source == "applied_section_frame"
        assert list(obj.PathSources) == ["applied_section_frame"]
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_builds_pipe_culvert_structure_body_as_cylinder() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPipeCulvertBodyBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipe_culvert_structure_body_source_model())

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:structure-body:structure-pipe-culvert-01"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        panel._target_table.selectRow(row_index)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id[target_id]
        obj = doc.getObject(state.output_object_ref)
        expected_volume = math.pi * (1.2 / 2.0) ** 2 * 6.0

        assert state.build_status == "built"
        assert obj is not None
        assert obj.TargetFamilies == ["structure_body"]
        assert obj.StructureRefs == ["structure:pipe-culvert-01"]
        assert abs(float(obj.Shape.Volume) - expected_volume) < 0.05
        assert obj.FaceCounts[0] < 6
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_builds_pipe_culvert_structure_body_as_hollow_wall_when_thickness_exists() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsHollowPipeCulvertBodyBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=_pipe_culvert_structure_body_source_model(wall_thickness=0.15),
        )

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:structure-body:structure-pipe-culvert-01"
        row_index = _target_table_row(panel, target_id)

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id[target_id]
        obj = doc.getObject(state.output_object_ref)
        expected_volume = math.pi * ((1.5 / 2.0) ** 2 - (1.2 / 2.0) ** 2) * 6.0

        assert state.build_status == "built"
        assert obj is not None
        assert abs(float(obj.Shape.Volume) - expected_volume) < 0.08
        assert float(obj.Shape.Volume) < math.pi * (1.5 / 2.0) ** 2 * 6.0
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_reuses_external_structure_body_shape() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsExternalStructureBodyBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        external_obj = doc.addObject("Part::Feature", "ExternalStructureBody")
        external_obj.Shape = Part.makeBox(2.0, 3.0, 4.0, App.Vector(49.0, -3.5, 38.0))
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=_external_structure_body_source_model(external_obj.Name),
        )

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:structure-body:structure-external-01"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        assert panel._target_state_by_id[target_id].target_row.readiness_status == "available"

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()

        state = panel._target_state_by_id[target_id]
        assert state.validation_status == "ok"
        assert "External Structure body shape candidate ready" in state.validation_message
        assert "connection_point_status=ok" in state.validation_message

        panel._build_selected_button.click()

        obj = doc.getObject(state.output_object_ref)
        notes = state.watertight_output.solid_rows[0].notes

        assert state.build_status == "built"
        assert obj is not None
        assert obj.TargetFamilies == ["structure_body"]
        assert obj.StructureRefs == ["structure:external-01"]
        assert abs(float(obj.Shape.Volume) - 24.0) < 0.001
        assert f"geometry_ref={external_obj.Name}" in notes
        assert f"external_object={external_obj.Name}" in notes
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_blocks_external_structure_body_when_connection_points_are_outside_shape() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsExternalStructureBodyPointMismatchTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        external_obj = doc.addObject("Part::Feature", "ExternalStructureBody")
        external_obj.Shape = Part.makeBox(2.0, 3.0, 4.0)
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=_external_structure_body_source_model(external_obj.Name),
        )

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:structure-body:structure-external-01"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        assert panel._target_state_by_id[target_id].target_row.readiness_status == "available"

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()

        state = panel._target_state_by_id[target_id]
        assert state.validation_status == "error"
        assert state.build_status == "blocked"
        assert "connection_point_status=outside_shape" in state.validation_message
        assert "connection:external-01:pipe-in" in state.validation_message
    finally:
        App.closeDocument(doc.Name)


def test_watertight_solids_discovers_and_builds_drainage_pipeline_network_body() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsDrainagePipelineNetworkBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        _populate_pipeline_sources(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:drainage-pipeline-network:main"
        row_index = _target_table_row(panel, target_id)

        assert row_index >= 0
        assert panel._target_table.item(row_index, 1).text() == "Drainage Pipe Network Solid - drainage-pipeline-network:main"
        assert panel._target_table.item(row_index, 2).text() == "Drainage: Pipe Network"
        assert "flow-route:pipe-01" in panel._target_table.item(row_index, 4).text()
        assert panel._target_state_by_id[target_id].target_row.readiness_status == "available"

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()

        state = panel._target_state_by_id[target_id]
        assert state.validation_status == "ok"
        assert state.profile_count >= 2
        assert state.volume > 0.0
        assert "fuse_mode=compound_first_slice" in state.validation_message

        panel._build_selected_button.click()

        obj = doc.getObject(state.output_object_ref)
        assert state.build_status == "built"
        assert obj is not None
        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.TargetFamilies == ["drainage_pipeline_network_body"]
        assert obj.DrainageRefs == ["drainage-pipeline-network:main"]
        assert obj.FlowRouteRefs == ["flow-route:pipe-01"]
        assert obj.StructureRefs == ["structure:inlet-01,structure:outlet-01"]
        assert obj.Shape.Volume > 0.0
        assert "connectors=2" in state.validation_message
        assert "connector_count=2" in state.watertight_output.solid_rows[0].notes
        assert "structure_refs=structure:inlet-01,structure:outlet-01" in state.watertight_output.solid_rows[0].notes
        assert "connection_point_refs=connection:inlet-01:pipe-out,connection:outlet-01:pipe-in" in state.watertight_output.solid_rows[0].notes
        assert obj.Name in _group_names(ensure_project_tree(project, include_references=False)[V1_TREE_WATERTIGHT_SOLIDS])

        panel._build_package_button.click()
        package_obj = doc.getObject("V1SimulationPackageOutput")
        assert package_obj is not None
        assert package_obj.DrainageReadinessStatus == "ready"
        assert package_obj.DrainageSourceStatus == "ready"
        assert package_obj.DrainageFlowRouteCount == 1
        assert package_obj.DrainagePipeCandidateCount == 1
        assert package_obj.DrainagePipelineNetworkTargetCount == 1
        assert package_obj.DrainageNetworkFuseStatus == "built"
        package_output = to_simulation_package_output(package_obj)
        assert package_output is not None
        assert package_output.drainage_readiness_status == "ready"
        assert package_output.drainage_network_fuse_status == "built"

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "simulation_package.json"
            export_document_simulation_package_json(str(export_path), document=doc, project=project)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            assert exported["drainage_readiness"]["status"] == "ready"
            assert exported["drainage_readiness"]["pipe_candidate_count"] == 1
            assert exported["drainage_readiness"]["pipeline_network_target_count"] == 1
            assert exported["drainage_readiness"]["network_fuse_status"] == "built"
    finally:
        App.closeDocument(doc.Name)


def test_drainage_pipeline_network_body_includes_built_structure_body_outputs() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsDrainagePipelineNetworkStructureFuseTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        _populate_pipeline_sources(doc, project)
        structure_obj = _create_structure_body_output(
            doc,
            project,
            structure_ref="structure:inlet-01",
            object_name="V1WatertightSolidOutput_StructureInlet01",
        )

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:drainage-pipeline-network:main"
        row_index = _target_table_row(panel, target_id)

        panel._target_table.selectRow(row_index)
        panel._validate_button.click()
        panel._build_selected_button.click()

        state = panel._target_state_by_id[target_id]
        obj = doc.getObject(state.output_object_ref)
        notes = state.watertight_output.solid_rows[0].notes

        assert state.build_status == "built"
        assert obj is not None
        assert obj.Shape.Volume > 0.0
        assert "structure_bodies=1" in state.validation_message
        assert "structure_body_count=1" in notes
        assert "structure_fuse_status=included" in notes
        assert f"structure_body_object_refs={structure_obj.Name}" in notes
        assert structure_obj.Name in state.watertight_output.solid_rows[0].source_refs
    finally:
        App.closeDocument(doc.Name)


def test_drainage_pipeline_network_build_enabled_autobuilds_structure_body_dependencies() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsDrainagePipelineNetworkDependencyBuildTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project)
        _populate_pipeline_sources_with_structure_specs(doc, project)

        panel = V1WatertightSolidsTaskPanel(document=doc)
        target_id = "solid-target:drainage-pipeline-network:main"
        row_index = _target_table_row(panel, target_id)

        panel._target_table.item(row_index, 0).setCheckState(QtCore.Qt.Checked)
        panel._build_enabled_button.click()

        network_state = panel._target_state_by_id[target_id]
        inlet_state = panel._target_state_by_id["solid-target:structure-body:structure-inlet-01"]
        outlet_state = panel._target_state_by_id["solid-target:structure-body:structure-outlet-01"]
        notes = network_state.watertight_output.solid_rows[0].notes

        assert inlet_state.build_status == "built"
        assert outlet_state.build_status == "built"
        assert network_state.build_status == "built"
        assert "dependencies_built=2" in network_state.validation_message
        assert "port_connectors=0" in network_state.validation_message
        assert "structure_port_terminals=2" in network_state.validation_message
        assert "structure_port_status=direct" in network_state.validation_message
        assert "Build Enabled summary: built=1; failed=0; targets=1" in panel._status.toPlainText()
        assert "structure_body_count=2" in notes
        assert "port_connector_count=0" in notes
        assert "port_connector_status=not_needed" in notes
        assert "structure_port_terminal_count=2" in notes
        assert "structure_port_contact_status=direct" in notes
        assert "structure_fuse_status=included" in notes
        assert inlet_state.output_object_ref in notes
        assert outlet_state.output_object_ref in notes
        inlet_obj = doc.getObject(inlet_state.output_object_ref)
        outlet_obj = doc.getObject(outlet_state.output_object_ref)
        assert inlet_obj is not None
        assert outlet_obj is not None
        assert abs((float(inlet_obj.Shape.BoundBox.YMin) + float(inlet_obj.Shape.BoundBox.YMax)) / 2.0 - -4.5) < 0.01
        assert abs((float(inlet_obj.Shape.BoundBox.ZMin) + float(inlet_obj.Shape.BoundBox.ZMax)) / 2.0 - 44.2) < 0.01
        assert abs((float(outlet_obj.Shape.BoundBox.YMin) + float(outlet_obj.Shape.BoundBox.YMax)) / 2.0 - -6.0) < 0.01
        assert abs((float(outlet_obj.Shape.BoundBox.ZMin) + float(outlet_obj.Shape.BoundBox.ZMax)) / 2.0 - 43.6) < 0.01
        assert inlet_obj.FaceCounts[0] > 6
        assert outlet_obj.FaceCounts[0] > 6
        assert float(inlet_obj.Shape.Volume) < 1.2 * 1.0 * 2.0
        assert float(outlet_obj.Shape.Volume) < 1.4 * 1.1 * 2.0
        assert "solid_kind=inlet_body_solid" in inlet_state.watertight_output.solid_rows[0].notes
        assert "solid_kind=outlet_body_solid" in outlet_state.watertight_output.solid_rows[0].notes
    finally:
        App.closeDocument(doc.Name)


def test_drainage_pipeline_network_shape_attempts_boolean_fuse_before_compound_fallback() -> None:
    rows = [
        SimpleNamespace(centerline_points=[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)], diameter=1.0),
        SimpleNamespace(centerline_points=[(5.0, 0.0, 0.0), (10.0, 0.0, 0.0)], diameter=1.0),
    ]

    result = _drainage_pipeline_network_solid_shape(rows)

    assert result.fuse_mode in {"boolean_fuse", "compound_fallback"}
    assert "shape_count=2" in result.notes
    assert result.shape.Volume > 0.0


def test_drainage_pipeline_network_shape_adds_junction_connector_body() -> None:
    rows = [
        SimpleNamespace(
            pipeline_segment_id="pipeline-segment:a",
            centerline_points=[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)],
            diameter=1.0,
        ),
        SimpleNamespace(
            pipeline_segment_id="pipeline-segment:b",
            centerline_points=[(5.0, 0.0, 0.0), (10.0, 2.0, 0.0)],
            diameter=1.0,
        ),
    ]
    junctions = [
        SimpleNamespace(
            junction_kind="junction",
            point=(5.0, 0.0, 0.0),
            pipeline_segment_refs=["pipeline-segment:a", "pipeline-segment:b"],
        )
    ]

    result = _drainage_pipeline_network_solid_shape(rows, junction_rows=junctions)

    assert result.connector_count == 1
    assert "connector_count=1" in result.notes
    assert result.shape.Volume > 0.0


def test_drainage_pipeline_network_shape_adds_terminal_structure_connectors() -> None:
    rows = [
        SimpleNamespace(
            pipeline_segment_id="pipeline-segment:a",
            centerline_points=[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)],
            diameter=1.0,
        )
    ]
    junctions = [
        SimpleNamespace(
            junction_kind="terminal",
            point=(0.0, 0.0, 0.0),
            pipeline_segment_refs=["pipeline-segment:a"],
            notes="connection_point_refs=connection:inlet:pipe-out;structure_connector_status=pending",
        ),
        SimpleNamespace(
            junction_kind="terminal",
            point=(5.0, 0.0, 0.0),
            pipeline_segment_refs=["pipeline-segment:a"],
            notes="connection_point_refs=connection:outlet:pipe-in;structure_connector_status=pending",
        ),
    ]

    result = _drainage_pipeline_network_solid_shape(rows, junction_rows=junctions)

    assert result.connector_count == 2
    assert "connector_count=2" in result.notes
    assert result.shape.Volume > 0.0


def test_drainage_pipeline_network_shape_adds_port_bridge_connectors_to_structure_body() -> None:
    rows = [
        SimpleNamespace(
            pipeline_segment_id="pipeline-segment:a",
            centerline_points=[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)],
            diameter=1.0,
        )
    ]
    junctions = [
        SimpleNamespace(
            junction_kind="terminal",
            point=(0.0, 0.0, 0.0),
            pipeline_segment_refs=["pipeline-segment:a"],
            notes="connection_point_refs=connection:inlet:pipe-out;structure_refs=structure:inlet",
        )
    ]
    structure_shape = Part.makeBox(1.0, 2.0, 2.0, App.Vector(10.0, -1.0, -1.0))

    result = _drainage_pipeline_network_solid_shape(
        rows,
        junction_rows=junctions,
        structure_body_shapes=[structure_shape],
        structure_body_shape_map={"structure:inlet": [(structure_shape, "StructureBodyInlet")]},
        connection_point_map={
            "connection:inlet:pipe-out": SimpleNamespace(
                diameter=2.0,
                width=0.0,
                height=0.0,
                direction="downstream",
            )
        },
    )

    assert result.connector_count == 1
    assert result.port_connector_count == 1
    assert result.structure_port_terminal_count == 1
    assert result.structure_port_contact_status == "bridged"
    assert "port_connector_count=1" in result.notes
    assert "structure_port_contact_status=bridged" in result.notes
    assert result.shape.Volume > 25.0


def test_drainage_pipeline_network_shape_trims_terminal_inside_structure_body_to_boundary() -> None:
    rows = [
        SimpleNamespace(
            pipeline_segment_id="pipeline-segment:a",
            centerline_points=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
            diameter=1.0,
        )
    ]
    junctions = [
        SimpleNamespace(
            junction_kind="terminal",
            point=(0.0, 0.0, 0.0),
            pipeline_segment_refs=["pipeline-segment:a"],
            notes="connection_point_refs=connection:inlet:pipe-out;structure_refs=structure:inlet",
        )
    ]
    structure_shape = Part.makeBox(2.0, 2.0, 2.0, App.Vector(-1.0, -1.0, -1.0))

    result = _drainage_pipeline_network_solid_shape(
        rows,
        junction_rows=junctions,
        structure_body_shapes=[structure_shape],
        structure_body_shape_map={"structure:inlet": [(structure_shape, "StructureBodyInlet")]},
    )

    assert result.endpoint_trim_count == 1
    assert result.port_connector_count == 0
    assert result.structure_port_terminal_count == 1
    assert result.structure_port_contact_status == "trimmed"
    assert "endpoint_trim_count=1" in result.notes
    assert "structure_port_contact_status=trimmed" in result.notes
    assert result.shape.Volume > 0.0


def _target_table_row(panel, target_id: str) -> int:
    for row_index in range(panel._target_table.rowCount()):
        item = panel._target_table.item(row_index, 1)
        if item is not None and str(item.data(QtCore.Qt.UserRole) or "") == target_id:
            return row_index
    return -1


def test_watertight_solids_panel_build_enabled_builds_each_enabled_target_independently() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1WatertightSolidsPanelBuildEnabledTest")
    try:
        _populate_ready_build_corridor_outputs(doc, project, include_component=True)

        panel = V1WatertightSolidsTaskPanel(document=doc)

        assert panel._target_table.rowCount() == 2
        assert panel._build_enabled_button.isEnabled() is False
        for row_index in range(panel._target_table.rowCount()):
            panel._target_table.item(row_index, 0).setCheckState(QtCore.Qt.Checked)

        assert panel._build_enabled_button.isEnabled() is True
        panel._build_enabled_button.click()

        road_state = panel._target_state_by_id["solid-target:road-body-envelope"]
        component_state = panel._target_state_by_id["solid-target:pavement-layer:pavement-base"]
        assert road_state.build_status == "built"
        assert component_state.build_status == "built"
        assert road_state.volume > 0.0
        assert component_state.volume > 0.0
        assert doc.getObject(road_state.output_object_ref) is not None
        assert doc.getObject(component_state.output_object_ref) is not None
        assert road_state.output_object_ref != component_state.output_object_ref
        tree = ensure_project_tree(project, include_references=False)
        names = _group_names(tree[V1_TREE_WATERTIGHT_SOLIDS])
        assert road_state.output_object_ref in names
        assert component_state.output_object_ref in names
        assert "Build Enabled summary: built=2; failed=0; targets=2; volume=" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)
