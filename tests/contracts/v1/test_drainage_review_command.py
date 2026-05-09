import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_review import (
    CmdV1DrainageReview,
    V1DrainageReviewTaskPanel,
    build_drainage_review_output,
    run_v1_drainage_review_command,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.quantity_model import QuantityFragment, QuantityModel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_drainage import create_or_update_v1_drainage_model_object
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object
from freecad.Corridor_Road.v1.services.mapping.drainage_review_mapper import DrainageReviewMapper

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


def _drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:side-ditch-right",
                element_kind="ditch",
                side="right",
                station_start=0.0,
                station_end=100.0,
                assembly_component_ref="ditch:right",
                policy_set_ref="drainage-policy:lined-concrete",
            )
        ],
    )


def _region_model() -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="proj-review",
        region_model_id="regions:main",
        region_rows=[
            RegionRow(
                region_id="region:drainage",
                station_start=0.0,
                station_end=100.0,
                drainage_refs=["drainage:side-ditch-right", "drainage:missing"],
            )
        ],
    )


def _applied_set() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-review",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-review",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, z=10.0),
                point_rows=[
                    AppliedSectionPoint(
                        "ditch:right-edge",
                        0.0,
                        -5.0,
                        10.0,
                        "ditch_surface",
                        -5.0,
                        component_ref="ditch:right",
                        side="right",
                        drainage_ref="drainage:side-ditch-right",
                    ),
                    AppliedSectionPoint(
                        "ditch:right-flow",
                        0.0,
                        -6.0,
                        9.8,
                        "ditch_surface",
                        -6.0,
                        component_ref="ditch:right",
                        side="right",
                        drainage_ref="drainage:side-ditch-right",
                    ),
                ],
            )
        ],
    )


def test_drainage_review_mapper_reports_source_handoff_and_applied_context() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_drainage_model(),
        region_model=_region_model(),
        applied_section_set=_applied_set(),
        project_id="proj-review",
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    region_rows = [row for row in output.element_rows if row.kind == "region_handoff"]
    applied_rows = [row for row in output.element_rows if row.kind == "applied_section_ditch_context"]

    assert summary["summary:drainage-elements"] == 1
    assert summary["summary:missing-region-refs"] == 1
    assert summary["summary:ditch-surface-points"] == 2
    assert summary["summary:ditch-surface-points-with-drainage"] == 2
    assert any("drainage_ref=drainage:missing;status=missing" in row.notes for row in region_rows)
    assert applied_rows[0].notes == "ditch_points=2;drainage_refs=drainage:side-ditch-right;component_refs=ditch:right;sides=right"
    assert output.source_refs == ["drainage:main", "regions:main", "applied:main"]


def test_drainage_review_mapper_reports_drainage_quantity_summary() -> None:
    quantity_model = QuantityModel(
        schema_version=1,
        project_id="proj-review",
        quantity_model_id="quantity:drainage",
        corridor_id="corridor:main",
        fragment_rows=[
            QuantityFragment(
                fragment_id="quantity:ditch",
                quantity_kind="drainage_ditch_length",
                measurement_kind="drainage_applied_section_longitudinal",
                value=20.0,
                unit="m",
                station_start=0.0,
                station_end=20.0,
                component_ref="ditch:right",
                drainage_ref="drainage:side-ditch-right",
            ),
            QuantityFragment(
                fragment_id="quantity:flowline",
                quantity_kind="drainage_flowline_length",
                measurement_kind="drainage_applied_section_flowline",
                value=19.5,
                unit="m",
                station_start=0.0,
                station_end=20.0,
                component_ref="ditch:right",
                drainage_ref="drainage:side-ditch-right",
            ),
        ],
    )

    output = DrainageReviewMapper().map(
        drainage_model=_drainage_model(),
        region_model=_region_model(),
        applied_section_set=_applied_set(),
        quantity_model=quantity_model,
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    quantity_rows = [row for row in output.element_rows if row.kind == "drainage_quantity"]
    assert summary["summary:drainage-ditch-length"] == 20.0
    assert summary["summary:drainage-flowline-length"] == 19.5
    assert len(quantity_rows) == 2
    assert quantity_rows[0].source_ref == "drainage:side-ditch-right"
    assert "quantity:drainage" in output.source_refs


def test_drainage_review_panel_loads_document_context() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageReviewPanelTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_model())
        create_or_update_v1_region_model_object(doc, project=project, region_model=_region_model())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_applied_set())

        panel = V1DrainageReviewTaskPanel(document=doc)

        assert panel._summary_table.rowCount() == 6
        assert panel._element_table.rowCount() == 1
        assert panel._region_table.rowCount() == 2
        assert panel._applied_table.rowCount() == 1
        assert "Warnings: 1 Region drainage ref" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_run_v1_drainage_review_command_returns_panel() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageReviewRunCommandTest")
    try:
        panel = run_v1_drainage_review_command(document=doc)

        assert isinstance(panel, V1DrainageReviewTaskPanel)
        assert panel.document == doc
    finally:
        App.closeDocument(doc.Name)


def test_build_drainage_review_output_reads_document_objects() -> None:
    doc, project = _new_project_doc("V1DrainageReviewOutputTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_model())
        create_or_update_v1_region_model_object(doc, project=project, region_model=_region_model())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_applied_set())

        output = build_drainage_review_output(doc)

        assert output.drainage_model_id == "drainage:main"
        assert len(output.element_rows) == 4
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_resources_and_toolbar_order() -> None:
    resources = CmdV1DrainageReview().GetResources()
    commands = corridorroad_workflow_toolbar_commands()

    assert resources["MenuText"] == "Drainage Review"
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("drainage_review.svg")
    assert commands.index("CorridorRoad_V1EditDrainage") < commands.index("CorridorRoad_V1DrainageReview")
    assert commands.index("CorridorRoad_V1DrainageReview") < commands.index("CorridorRoad_V1AppliedSections")
