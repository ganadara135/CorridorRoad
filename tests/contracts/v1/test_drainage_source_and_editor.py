"""The Drainage source object, the Drainage editor (DR-1) and the Drainage result stage (DR-2)."""

import os
import tempfile
from dataclasses import dataclass, field

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import (
    V1DrainageEditorTaskPanel,
    apply_v1_drainage_model,
    drainage_editor_inputs,
    refresh_drainage_result,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_rebuild_downstream import rebuild_downstream
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.drainage_model import (
    DitchRun,
    DrainageLink,
    DrainageModel,
    DrainagePoint,
    DrainagePolicy,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    find_v1_drainage_model,
    to_drainage_model,
)
from freecad.Corridor_Road.v1.objects.obj_drainage_result import find_v1_drainage_result_object, to_drainage_result
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.result_freshness import document_result_freshness
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.persistence_payload_adapter import write_model_payload

_QAPP = None


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _road_with_ditches(name: str):
    """A road whose Full Set Road Assembly has a ditch on each side, over one Region."""

    doc, project = _new_project_doc(name)
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=40.0)
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Full Set Road", doc, project=project, alignment=alignment),
    )
    apply_v1_region_model(
        document=doc,
        project=project,
        region_model=region_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    return doc, project


def _model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="p",
        policy=DrainagePolicy(min_grade_percent=0.5, max_inlet_spacing_m=45.0, low_point_rule="allow_ponding"),
        ditch_run_rows=[DitchRun("ditch-run:left", "left", "ditch:left", 0.0, 120.0, alignment_ref="alignment:main")],
        point_rows=[DrainagePoint("inlet:1", "inlet", 60.0, side="left", ditch_run_ref="ditch-run:left")],
        link_rows=[DrainageLink("link:1", "inlet:1", "outfall:1")],
    )


def test_the_drainage_model_survives_save_and_reopen() -> None:
    doc, project = _new_project_doc("V1DrainageSourceRoundTrip")
    path = os.path.join(tempfile.mkdtemp(), "drainage.FCStd")
    try:
        obj = create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_model())
        assert (obj.DitchRunCount, obj.PointCount, obj.LinkCount) == (1, 1, 1)
        assert obj.LowPointRule == "allow_ponding"
        doc.saveAs(path)
    finally:
        App.closeDocument(doc.Name)
    reopened = App.openDocument(path)
    try:
        assert to_drainage_model(find_v1_drainage_model(reopened)) == _model()
    finally:
        App.closeDocument(reopened.Name)


@dataclass
class _DrainageBeforeTheRework:
    schema_version: int
    project_id: str
    drainage_model_id: str = "drainage:main"
    element_rows: list[dict] = field(default_factory=list)


def test_a_drainage_object_from_before_the_rework_restores_empty_and_drops_its_old_rows() -> None:
    doc, project = _new_project_doc("V1DrainageSourceOld")
    try:
        obj = create_or_update_v1_drainage_model_object(doc, project=project)
        obj.addProperty("App::PropertyStringList", "ElementKinds", "Drainage Elements", "old")
        obj.ElementKinds = ["ditch"]
        old = _DrainageBeforeTheRework(1, "p", element_rows=[{"drainage_element_id": "drainage:left", "element_kind": "ditch"}])
        write_model_payload(obj, old, model_type="DrainageModel", row_fields=("element_rows",))

        model = to_drainage_model(obj)
        assert model is not None
        assert (model.ditch_run_rows, model.point_rows, model.link_rows) == ([], [], [])
        assert model.policy == DrainagePolicy()

        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_model())
        assert not hasattr(obj, "ElementKinds")
        assert to_drainage_model(obj) == _model()
    finally:
        App.closeDocument(doc.Name)


def test_the_editor_prefills_ditch_runs_without_writing_and_apply_tags_the_ditch_points() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageEditorPrefill")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)

        # opening the editor writes nothing
        assert find_v1_drainage_model(doc) is None
        runs = [panel._run(row) for row in range(panel._table.rowCount())]
        assert [(run.subassembly_ref, run.side) for run in runs] == [("ditch:left", "left"), ("ditch:right", "right")]
        assert "Apply to keep them" in panel._status.toPlainText()

        assert panel._apply() is True
        stored = to_drainage_model(find_v1_drainage_model(doc))
        assert [run.ditch_run_id for run in stored.ditch_run_rows] == [run.ditch_run_id for run in runs]

        show_v1_centerline3d_preview_object(doc, project=project)
        applied = build_document_applied_section_set(doc, project=project)
        refs = {
            (point.side, point.drainage_ref)
            for section in applied.sections
            for point in section.point_rows
            if point.point_role == "ditch_surface"
        }
        assert refs == {(run.side, run.ditch_run_id) for run in runs}
    finally:
        App.closeDocument(doc.Name)


def test_apply_refuses_a_run_on_a_ditch_the_assembly_does_not_have() -> None:
    doc, project = _road_with_ditches("V1DrainageEditorRefuse")
    try:
        model = DrainageModel(
            schema_version=1,
            project_id="p",
            ditch_run_rows=[DitchRun("ditch-run:x", "left", "ditch:median", 0.0, 100.0)],
        )

        with pytest.raises(ValueError, match="'ditch:median' is not a ditch in any Assembly"):
            apply_v1_drainage_model(document=doc, drainage_model=model)
        assert find_v1_drainage_model(doc) is None
    finally:
        App.closeDocument(doc.Name)


def _freshness(doc) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {row.stage: (row.status, row.changed_inputs) for row in document_result_freshness(doc)}


def test_the_drainage_result_is_a_stage_after_applied_sections() -> None:
    doc, project = _road_with_ditches("V1DrainageResultStage")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        prefilled = drainage_editor_inputs(doc)["model"]
        apply_v1_drainage_model(document=doc, drainage_model=prefilled)

        # new Ditch Runs retag the ditch points: Applied Sections are stale, Drainage not built yet
        freshness = _freshness(doc)
        assert freshness["applied_sections"] == ("stale", ("drainage_ditch_runs",))
        assert freshness["drainage"][0] == "missing"
        assert "Run Rebuild Downstream" in refresh_drainage_result(doc)
        assert find_v1_drainage_result_object(doc) is None

        report = rebuild_downstream(doc)
        assert not report.failed, report.text
        assert report.rebuilt_stages == ("applied_sections", "drainage")
        assert _freshness(doc)["drainage"] == ("current", ())
        result = to_drainage_result(find_v1_drainage_result_object(doc))
        assert sorted(row.side for row in result.flowline_rows) == ["left", "right"]
        assert not [row for row in result.check_rows if row.kind == "flowline_missing"]
        assert all(len(row.station_rows) >= 2 for row in result.flowline_rows)

        # a Policy edit makes only the Drainage stale, and the panel's Apply evaluates it at once
        stricter = DrainagePolicy(min_grade_percent=50.0)
        apply_v1_drainage_model(
            document=doc,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id=prefilled.project_id,
                policy=stricter,
                ditch_run_rows=prefilled.ditch_run_rows,
            ),
        )
        freshness = _freshness(doc)
        assert freshness["applied_sections"] == ("current", ())
        assert freshness["drainage"] == ("stale", ("drainage",))
        summary = refresh_drainage_result(doc)
        assert summary.startswith("Drainage checks: warning")
        assert "under the 50.00 % minimum" in summary
        assert _freshness(doc)["drainage"] == ("current", ())
    finally:
        App.closeDocument(doc.Name)


def test_the_panel_adds_the_suggested_points_and_apply_settles_the_checks() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageSuggestions")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed

        panel = V1DrainageEditorTaskPanel(document=doc)
        suggestions = list(panel._suggestions)
        assert suggestions, "the sample road's low points need inlets or outfalls"
        assert {row.reason for row in suggestions} <= {"low_point", "spacing"}

        panel._add_suggestions(selected_only=False)
        assert panel._point_table.rowCount() == len(suggestions)
        # adding them twice adds nothing
        panel._add_suggestions(selected_only=False)
        assert panel._point_table.rowCount() == len(suggestions)
        # nothing is written until Apply
        assert to_drainage_model(find_v1_drainage_model(doc)).point_rows == []

        assert panel._apply() is True
        stored = to_drainage_model(find_v1_drainage_model(doc))
        assert len(stored.point_rows) == len(suggestions)
        assert all(point.side in {"left", "right"} for point in stored.point_rows)
        result = to_drainage_result(find_v1_drainage_result_object(doc))
        assert result.suggestion_rows == []
        assert not {row.kind for row in result.check_rows} & {"low_point_uncollected", "inlet_spacing"}
        assert _freshness(doc)["drainage"] == ("current", ())
        assert panel._suggestions == []

        # every suggested inlet now drains nowhere until Link Downhill joins it to a lower point
        inlets = [point.point_id for point in stored.point_rows if point.kind == "inlet"]
        assert {row.check_id for row in result.check_rows if row.kind == "drains_nowhere"} == {f"drains_nowhere:{name}" for name in inlets}
        panel._link_downhill()
        assert panel._link_table.rowCount() == len(inlets)
        assert panel._apply() is True
        result = to_drainage_result(find_v1_drainage_result_object(doc))
        assert not {row.kind for row in result.check_rows} & {"drains_nowhere", "link_uphill", "link_loop", "link_unplaced"}
        assert len(result.link_rows) == len(inlets)
        assert all(row.grade_percent < 0.0 for row in result.link_rows)
    finally:
        App.closeDocument(doc.Name)
