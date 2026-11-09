"""The Drainage source object, the Drainage editor (DR-1), the Drainage result stage (DR-2) and Drainage Review (DR-5)."""

import os
import tempfile
from dataclasses import dataclass, field

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import corridor_drainage_review_summary
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_drainage_review import V1DrainageReviewTaskPanel, focus_drainage_pipe
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import (
    V1DrainageEditorTaskPanel,
    apply_v1_drainage_model,
    drainage_editor_inputs,
    drainage_flowlines,
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
from freecad.Corridor_Road.v1.services.editing.drainage_editing_service import link_diagnostics
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import FlowEdit
from freecad.Corridor_Road.v1.services.evaluation.drainage_evaluation_service import suggest_points
from freecad.Corridor_Road.v1.ui.editors.drainage_editor import LINK_TO_COLUMN as LINK_TO
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
        link_rows=[DrainageLink("link:1", "inlet:1", "outfall:1", pipe_diameter_m=0.6)],
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


@dataclass
class _LinkBeforePipes:
    link_id: str
    from_ref: str
    to_ref: str


@dataclass
class _DrainageBeforePipes:
    schema_version: int
    project_id: str
    drainage_model_id: str = "drainage:main"
    policy: DrainagePolicy = field(default_factory=DrainagePolicy)
    ditch_run_rows: list = field(default_factory=list)
    point_rows: list = field(default_factory=list)
    link_rows: list = field(default_factory=list)


def test_a_link_stored_before_pipes_restores_as_open_flow() -> None:
    doc, project = _new_project_doc("V1DrainageSourceBeforePipes")
    try:
        obj = create_or_update_v1_drainage_model_object(doc, project=project)
        old = _DrainageBeforePipes(1, "p", link_rows=[_LinkBeforePipes("link:1", "inlet:1", "outfall:1")])
        write_model_payload(obj, old, model_type="DrainageModel", row_fields=("ditch_run_rows", "point_rows", "link_rows"))
        model = to_drainage_model(obj)
        assert model is not None
        assert model.link_rows == [DrainageLink("link:1", "inlet:1", "outfall:1")]
        assert model.link_rows[0].pipe_diameter_m == 0.0
    finally:
        App.closeDocument(doc.Name)


def test_the_links_tab_keeps_a_pipe_diameter_blank_for_open_flow_and_refuses_text() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageLinkPipe")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        run = panel._run_ids()[0]
        for point in (DrainagePoint("inlet:1", "inlet", 10.0, ditch_run_ref=run), DrainagePoint("outfall:1", "outfall", 90.0, ditch_run_ref=run)):
            panel._append_point(point)
        panel._append_link(DrainageLink("link:1", "inlet:1", "outfall:1", pipe_diameter_m=0.6))
        panel._append_link(DrainageLink("link:2", "outfall:1", "inlet:1"))
        assert panel._link_table.item(0, 3).text() == "0.6" and panel._link_table.item(1, 3).text() == ""
        assert [link.pipe_diameter_m for link in panel._links()] == [0.6, 0.0]
        panel._link_table.item(1, 3).setText("0.45")
        assert panel._links()[1].pipe_diameter_m == 0.45
        panel._link_table.item(1, 3).setText("wide")
        with pytest.raises(ValueError, match="Link row 2: Pipe 'wide' is not a number"):
            panel._links()
        # reconnecting a link keeps its pipe
        panel._link_table.item(1, 3).setText("")
        panel._apply_flow_edit(FlowEdit(relink=(("link:1", "inlet:1"),)))
        assert panel._links()[0].pipe_diameter_m == 0.6 and panel._links()[0].to_ref == "inlet:1"
    finally:
        App.closeDocument(doc.Name)


def test_a_negative_or_non_finite_pipe_diameter_is_refused_at_apply() -> None:
    points = [DrainagePoint("inlet:1", "inlet", 1.0, ditch_run_ref="r"), DrainagePoint("outfall:1", "outfall", 9.0, ditch_run_ref="r")]
    assert link_diagnostics([DrainageLink("link:1", "inlet:1", "outfall:1", 0.6)], points) == []
    assert link_diagnostics([DrainageLink("link:1", "inlet:1", "outfall:1", 0.0)], points) == []
    assert "pipe diameter must be 0 (open flow) or more" in link_diagnostics([DrainageLink("link:1", "inlet:1", "outfall:1", -0.3)], points)[0]
    assert "pipe diameter" in link_diagnostics([DrainageLink("link:1", "inlet:1", "outfall:1", float("nan"))], points)[0]


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


def _flow_items(panel) -> list[tuple[str, int, str]]:
    """The flow tree's point rows as (point id, depth, text), parents before children."""

    rows: list[tuple[str, int, str]] = []
    stack = [(panel._flow_tree.topLevelItem(index), 0) for index in reversed(range(panel._flow_tree.topLevelItemCount()))]
    while stack:
        item, depth = stack.pop()
        point_id = str(item.data(0, QtCore.Qt.UserRole) or "")
        if point_id:
            rows.append((point_id, depth, item.text(0)))
        stack.extend((item.child(index), depth + 1) for index in reversed(range(item.childCount())))
    return rows


def test_the_flow_tab_shows_the_points_under_what_they_drain_into_and_selects_their_rows() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageFlowTab")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed

        panel = V1DrainageEditorTaskPanel(document=doc)
        assert [panel._tabs.tabText(i) for i in range(panel._tabs.count())][:3] == ["Policy", "Ditch Runs", "Flow"]
        assert _flow_items(panel) == []
        assert panel._flow_note.text().startswith("No points yet.")

        # unsaved points show at once, each draining nowhere
        panel._add_suggestions(selected_only=False)
        panel._tabs.setCurrentWidget(panel._flow_tab)
        unlinked = _flow_items(panel)
        assert len(unlinked) == panel._point_table.rowCount()
        assert {depth for _id, depth, _text in unlinked} == {0}
        assert all("drains nowhere" in text for point_id, _depth, text in unlinked if point_id.startswith("inlet"))

        assert panel._apply() is True
        panel._link_downhill()
        panel._refresh_flow_tree()
        linked = _flow_items(panel)
        point_ids = [point_id for point_id, _depth, _text in linked]
        assert sorted(point_ids) == sorted(panel._point_text(row, 0) for row in range(panel._point_table.rowCount()))
        assert len(set(point_ids)) == len(point_ids)
        inlets = [point_id for point_id in point_ids if point_id.startswith("inlet")]
        assert any(depth > 0 for _id, depth, _text in linked), "a linked inlet sits under the point it drains into"
        assert all(depth == 0 for point_id, depth, _text in linked if not point_id.startswith("inlet"))
        # a linked inlet reads its grade; the result is current, so the checks of the last Apply show
        assert all(" into " in text for point_id, depth, text in linked if depth > 0)

        # selecting a node selects its row in the Points table and its Link in the Links table
        target = next(index for index in range(panel._flow_tree.topLevelItemCount()) if panel._flow_tree.topLevelItem(index).childCount())
        child = panel._flow_tree.topLevelItem(target).child(0)
        panel._flow_tree.setCurrentItem(child)
        chosen = child.data(0, QtCore.Qt.UserRole)
        assert chosen in inlets
        selected_points = {panel._point_text(index.row(), 0) for index in panel._point_table.selectionModel().selectedRows()}
        selected_links = {panel._link_text(index.row(), 1, combo=True) for index in panel._link_table.selectionModel().selectedRows()}
        assert selected_points == {chosen} and selected_links == {chosen}

        # a Points table that cannot be read says so instead of raising
        panel._point_table.item(0, 3).setText("abc")
        panel._refresh_flow_tree()
        assert panel._flow_tree.topLevelItemCount() == 0
        assert panel._flow_note.text().startswith("The tree needs a valid Points table")
    finally:
        App.closeDocument(doc.Name)


def test_the_flow_tab_continues_the_network_upstream_and_downstream_from_the_selected_point() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageFlowContinue")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        # no result yet: the flowlines wait for Rebuild Downstream, and the note says so
        assert drainage_flowlines(doc)[0] == [] and "Rebuild Downstream" in drainage_flowlines(doc)[1]
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed
        flowlines, note = drainage_flowlines(doc)
        assert flowlines and note == ""

        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._tabs.setCurrentWidget(panel._flow_tab)
        panel._continue_flow(upstream=True)
        assert panel._status.toPlainText() == "Select a point in the tree first."

        # an outfall at the end the first ditch falls toward, then walk up from it
        line = flowlines[0]
        low_end = min((line.station_rows[0], line.station_rows[-1]), key=lambda row: row.z)
        panel._append_point(DrainagePoint("outfall:1", "outfall", low_end.station, ditch_run_ref=line.ditch_run_ref))
        panel._refresh_flow_tree()
        panel._select_flow_node("outfall:1")
        before = panel._point_table.rowCount(), panel._link_table.rowCount()
        panel._continue_flow(upstream=True)
        added = panel._point_table.rowCount() - before[0], panel._link_table.rowCount() - before[1]
        assert added == (1, 1), panel._status.toPlainText()
        new_id = panel._point_text(panel._point_table.rowCount() - 1, 0)
        assert new_id.startswith("inlet")
        assert panel._link_text(panel._link_table.rowCount() - 1, 1, combo=True) == new_id
        assert panel._link_text(panel._link_table.rowCount() - 1, 2, combo=True) == "outfall:1"
        assert panel._flow_tree.selectedItems()[0].data(0, QtCore.Qt.UserRole) == new_id
        assert panel._status.toPlainText().endswith("Apply to keep it.")

        # a point that drains nowhere is linked to the nearest lower point
        middle = (line.station_rows[0].station + line.station_rows[-1].station) / 2.0
        panel._append_point(DrainagePoint("inlet:9", "inlet", middle, ditch_run_ref=line.ditch_run_ref))
        panel._refresh_flow_tree()
        panel._select_flow_node("inlet:9")
        panel._continue_flow(upstream=False)
        assert panel._link_table.rowCount() == before[1] + 2, panel._status.toPlainText()
        assert panel._link_text(panel._link_table.rowCount() - 1, 1, combo=True) == "inlet:9"
        panel._continue_flow(upstream=False)  # it drains now: nothing more is added
        assert panel._link_table.rowCount() == before[1] + 2
        assert "already drains into" in panel._status.toPlainText()

        assert panel._apply() is True
    finally:
        App.closeDocument(doc.Name)


def test_trace_network_proposes_then_accepts_or_discards_and_leaves_the_sample_road_clean() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageTrace")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed

        # the helper the panel uses gives the suggestions the evaluation stored
        stored = to_drainage_result(find_v1_drainage_result_object(doc))
        stored_points = to_drainage_model(find_v1_drainage_model(doc)).point_rows
        from_helper = [
            row
            for flowline in stored.flowline_rows
            for row in suggest_points(flowline, stored_points, low_point_rule="require_inlet", max_inlet_spacing_m=60.0)
        ]
        assert from_helper and sorted((row.kind, row.ditch_run_ref, row.station) for row in from_helper) == sorted(
            (row.kind, row.ditch_run_ref, row.station) for row in stored.suggestion_rows
        )

        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._tabs.setCurrentWidget(panel._flow_tab)
        assert not panel._accept_button.isEnabled() and not panel._discard_button.isEnabled()

        # Discard drops a proposal without touching the tables
        rows_before = panel._point_table.rowCount(), panel._link_table.rowCount()
        panel._trace_network()
        assert panel._trace is not None and panel._trace.found
        assert panel._accept_button.isEnabled() and not panel._trace_button.isEnabled()
        assert not any(button.isEnabled() for button in panel._continue_buttons)
        assert any(text.startswith("+  ") for _id, _depth, text in _flow_items(panel))
        assert (panel._point_table.rowCount(), panel._link_table.rowCount()) == rows_before
        panel._discard_trace()
        assert panel._trace is None and _flow_items(panel) == []
        assert panel._trace_button.isEnabled() and all(button.isEnabled() for button in panel._continue_buttons)

        # a proposal whose ids were taken meanwhile is dropped, not forced in
        panel._trace_network()
        taken = panel._trace.points[0]
        panel._append_point(DrainagePoint(taken.point_id, "inlet", 1.0, ditch_run_ref=taken.ditch_run_ref))
        panel._accept_trace()
        assert panel._trace is None and "Trace Network again" in panel._status.toPlainText()
        assert panel._point_table.rowCount() == rows_before[0] + 1
        # the clashing row stays in the tables, so reload them from the stored Drainage
        panel._load(to_drainage_model(find_v1_drainage_model(doc)))

        # Accept puts the rows in the tables; Apply keeps them and the checks settle
        panel._trace_network()
        proposed_count = len(panel._trace.points)
        proposed_links = len(panel._trace.links)
        panel._accept_trace()
        assert panel._trace is None
        assert panel._point_table.rowCount() == proposed_count and panel._link_table.rowCount() == proposed_links
        assert panel._apply() is True
        kinds = {row.kind for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}
        assert kinds.isdisjoint(
            {"low_point_uncollected", "inlet_spacing", "drains_nowhere", "link_uphill", "link_flat", "link_loop", "drains_twice"}
        ), kinds

        # nothing is left to trace
        panel._trace_network()
        assert panel._trace is None and panel._status.toPlainText().startswith("Nothing to add")
    finally:
        App.closeDocument(doc.Name)


def _apply_points_and_links(doc, points, links) -> set[str]:
    """Store the Drainage with `points` and `links`, evaluate it, and give the ids of its checks."""

    base = drainage_editor_inputs(doc)["model"]
    apply_v1_drainage_model(
        document=doc,
        drainage_model=DrainageModel(
            schema_version=base.schema_version,
            project_id=base.project_id,
            label=base.label,
            drainage_model_id=base.drainage_model_id,
            policy=base.policy,
            ditch_run_rows=list(base.ditch_run_rows),
            point_rows=list(points),
            link_rows=list(links),
        ),
    )
    refresh_drainage_result(doc)
    return {row.check_id for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}


def _select_check(panel, point_id: str, kind: str):
    panel._tabs.setCurrentWidget(panel._flow_tab)
    panel._refresh_flow_tree()
    panel._select_flow_node(point_id)
    rows = panel._flow_nodes[point_id].check_rows
    for index, row in enumerate(rows):
        if row.kind == kind:
            panel._flow_check_list.setCurrentRow(index)
            return row
    raise AssertionError(f"{point_id} has no {kind} check: {[row.kind for row in rows]}")


def test_drainage_review_lists_the_pipes_and_draws_them_as_tubes() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainagePipeReview")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed
        line = drainage_flowlines(doc)[0][0]
        run = line.ditch_run_ref
        low, high = line.low_point_stations[0], round(line.high_point_stations[0], 3)

        # no pipe yet: the list is empty and there is nothing to draw
        _apply_points_and_links(doc, [DrainagePoint("inlet:1", "inlet", high, ditch_run_ref=run)], [])
        panel = V1DrainageReviewTaskPanel(document=doc)
        assert panel._pipes.rowCount() == 0 and not panel._all_pipes_button.isEnabled()
        with pytest.raises(ValueError, match="no pipes"):
            focus_drainage_pipe(doc)

        points = [DrainagePoint("inlet:1", "inlet", high, ditch_run_ref=run), DrainagePoint("outfall:1", "outfall", low, ditch_run_ref=run)]
        _apply_points_and_links(doc, points, [DrainageLink("link:1", "inlet:1", "outfall:1", pipe_diameter_m=0.6)])
        panel = V1DrainageReviewTaskPanel(document=doc)
        assert panel._pipes.rowCount() == 1 and panel._pipes.item(0, 0).text() == "link:1"
        assert panel._pipes.item(0, 2).text() == "0.60" and panel._all_pipes_button.isEnabled()
        assert "1 pipe(s)" in panel._summary.text()

        pipe = to_drainage_result(find_v1_drainage_result_object(doc)).pipe_rows[0]
        obj = focus_drainage_pipe(doc, "link:1")
        assert obj.Name == "ReviewDrainagePipes" and not obj.Shape.isNull()
        # a cylinder of the pipe's diameter and 3D length
        assert obj.Shape.Volume == pytest.approx(3.141592653589793 * 0.3**2 * pipe.length_m, rel=1.0e-3)

        panel._focus_pipe(0)
        assert panel._status.text().startswith("Drawn in the 3D view: Drainage pipe: link:1")
        panel._focus_pipe(-1)
        assert panel._status.text().startswith("Drawn in the 3D view: Drainage pipes (1)")
        with pytest.raises(ValueError, match="No Drainage pipe link:9"):
            focus_drainage_pipe(doc, "link:9")
    finally:
        App.closeDocument(doc.Name)


def test_the_flow_tab_fixes_a_check_and_apply_clears_it() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageFlowFix")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed
        line = drainage_flowlines(doc)[0][0]
        run = line.ditch_run_ref
        # the sample ditch rises from a low point at its start to a crest, then falls to a low point at its end
        low, high = line.low_point_stations[0], round(line.high_point_stations[0], 3)
        middle = (low + high) / 2.0

        def point(point_id, kind, station):
            return DrainagePoint(point_id, kind, station, ditch_run_ref=run)

        def reopen():
            return V1DrainageEditorTaskPanel(document=doc)

        # drains_nowhere -> Add Downstream
        checks = _apply_points_and_links(doc, [point("inlet:1", "inlet", middle), point("outfall:1", "outfall", low)], [])
        assert "drains_nowhere:inlet:1" in checks
        panel = reopen()
        _select_check(panel, "inlet:1", "drains_nowhere")
        panel._run_fix("add_downstream")
        assert panel._link_table.rowCount() == 1
        assert panel._apply() is True
        assert "drains_nowhere:inlet:1" not in {row.check_id for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}

        # link_uphill -> Reconnect To a lower point; a high inlet nobody feeds -> Delete Point
        uphill = [DrainageLink("link:1", "inlet:1", "inlet:2")]
        checks = _apply_points_and_links(
            doc,
            [point("inlet:1", "inlet", middle), point("inlet:2", "inlet", high), point("outfall:1", "outfall", low)],
            uphill,
        )
        assert "link_uphill:link:1" in checks
        panel = reopen()
        _select_check(panel, "inlet:1", "link_uphill")
        assert panel._fix_buttons["reconnect"].isEnabled() and panel._fix_buttons["delete_link"].isEnabled()
        assert not panel._fix_buttons["delete_point"].isEnabled()
        assert panel._reconnect_combo.currentText() == "outfall:1"
        panel._run_fix("reconnect")
        assert panel._link_text(0, LINK_TO, combo=True) == "outfall:1"
        assert panel._apply() is True
        checks = {row.check_id for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}
        assert "link_uphill:link:1" not in checks
        assert "reverse_flow:inlet:2" in checks
        panel = reopen()
        _select_check(panel, "inlet:2", "reverse_flow")
        before = panel._point_table.rowCount()
        panel._run_fix("delete_point")
        assert panel._point_table.rowCount() == before - 1
        assert panel._apply() is True
        assert "reverse_flow:inlet:2" not in {row.check_id for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}

        # a low point nobody collects -> Add Suggested; fixes are off while a proposal waits
        checks = _apply_points_and_links(doc, [point("inlet:1", "inlet", high)], [])
        wanted = [check for check in checks if check.startswith(f"low_point_uncollected:{run}")]
        assert wanted
        panel = reopen()
        check = _select_check(panel, "inlet:1", "low_point_uncollected")
        assert panel._fix_buttons["add_suggested"].isEnabled()
        panel._run_fix("add_suggested")
        assert panel._point_table.rowCount() >= 2
        assert panel._apply() is True
        checks = {row.check_id for row in to_drainage_result(find_v1_drainage_result_object(doc)).check_rows}
        assert check.check_id not in checks
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_shows_the_result_and_highlights_a_check() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageReview")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed

        panel = V1DrainageReviewTaskPanel(document=doc)

        assert panel._run_combo.count() == 2
        assert "The Drainage result is current." == panel._freshness.text()
        assert panel._checks.rowCount() > 0
        assert panel._profile._profile is not None and len(panel._profile._profile.points) >= 10
        panel._focus_check(0)
        highlight = doc.getObject("ReviewDrainageCheckHighlight")
        assert highlight is not None and not highlight.Shape.isNull()

        summary = corridor_drainage_review_summary(doc)
        assert "Drainage checks: warning" in summary["notes"]
        assert summary["status"] == "warn"
    finally:
        App.closeDocument(doc.Name)


def test_the_panel_keeps_exact_stations_behind_its_three_decimals() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageExactStations")
    try:
        # a run ending at a station with more decimals than the table shows
        end = 174.917228527
        runs = [DitchRun("ditch-run:ditch:left", "left", "ditch:left", 0.0, end)]
        apply_v1_drainage_model(document=doc, drainage_model=DrainageModel(schema_version=1, project_id="p", ditch_run_rows=runs))
        panel = V1DrainageEditorTaskPanel(document=doc)
        assert panel._table.item(0, 5).text() == "174.917"

        # untouched cells give the exact station back, so a Policy-only Apply changes no run
        assert panel._run(0).station_end == end
        apply_v1_drainage_model(document=doc, drainage_model=panel._model_from_panel())
        assert [run.station_end for run in to_drainage_model(find_v1_drainage_model(doc)).ditch_run_rows] == [end]

        # a typed station is taken as typed
        panel._table.item(0, 5).setText("120.500")
        assert panel._run(0).station_end == 120.5
    finally:
        App.closeDocument(doc.Name)


def test_drainage_and_drainage_review_open_each_other() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageOpenEachOther")
    try:
        from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import open_drainage_review
        from freecad.Corridor_Road.v1.commands.cmd_drainage_review import open_drainage_editor

        assert isinstance(open_drainage_review(doc), V1DrainageReviewTaskPanel)
        assert isinstance(open_drainage_editor(doc), V1DrainageEditorTaskPanel)
    finally:
        App.closeDocument(doc.Name)


def test_the_rebuild_downstream_window_rebuilds_with_a_progress_bar() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1RebuildDownstreamWindow")
    try:
        from freecad.Corridor_Road.v1.commands.cmd_rebuild_downstream import open_rebuild_downstream_dialog

        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        calls = []
        assert rebuild_downstream(doc, progress=lambda done, total, stage: calls.append((done, total, stage))).rebuilt_stages == (
            "applied_sections",
            "drainage",
        )
        assert calls[0] == (0, 5, "stationing") and calls[-1][:2] == (5, 5)

        # switching the runs off retags the ditch points: Applied Sections and Drainage go stale
        apply_v1_drainage_model(document=doc, drainage_model=_with_runs(doc, enabled=False))
        dialog = open_rebuild_downstream_dialog(doc)
        assert "stale" in dialog._stage_text.text()
        dialog._rebuild()
        assert dialog._progress.value() == dialog._progress.maximum() == 5
        assert "Applied Sections: rebuilt" in dialog._report.toPlainText()
        assert dialog._stage_text.text() == "Every built result is current."
        dialog.close()
    finally:
        App.closeDocument(doc.Name)


def _with_runs(doc, *, enabled: bool) -> DrainageModel:
    model = to_drainage_model(find_v1_drainage_model(doc))
    runs = [DitchRun(run.ditch_run_id, run.side, run.subassembly_ref, run.station_start, run.station_end, run.alignment_ref, enabled) for run in model.ditch_run_rows]
    return DrainageModel(schema_version=1, project_id=model.project_id, policy=model.policy, ditch_run_rows=runs)


def test_the_drawing_above_the_tabs_follows_the_unapplied_tables_and_the_selected_row() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, project = _road_with_ditches("V1DrainageDrawing")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=build_document_applied_section_set(doc, project=project))
        apply_v1_drainage_model(document=doc, drainage_model=drainage_editor_inputs(doc)["model"])
        assert not rebuild_downstream(doc).failed

        panel = V1DrainageEditorTaskPanel(document=doc)
        runs = panel._run_ids()
        drawn = [panel._drawing_run.itemText(index) for index in range(panel._drawing_run.count())]
        assert drawn == [row.ditch_run_ref for row in panel._flowlines] and set(drawn) == set(runs)
        assert panel._drawing._profile is not None and panel._drawing._profile.links == ()

        # points and a pipe typed in but not applied are drawn at once, on the run they sit on
        first, second = runs[0], runs[1]
        stations = [row.station for row in next(f for f in panel._flowlines if f.ditch_run_ref == second).station_rows]
        low, high = stations[1], stations[-2]
        panel._append_point(DrainagePoint("inlet:a", "inlet", low, ditch_run_ref=second))
        panel._append_point(DrainagePoint("outfall:a", "outfall", high, ditch_run_ref=second))
        panel._append_link(DrainageLink("link:a", "inlet:a", "outfall:a", pipe_diameter_m=0.6))
        assert to_drainage_model(find_v1_drainage_model(doc)).link_rows == []

        # selecting the link draws its run with the link marked; another run's row switches back
        panel._link_table.selectRow(0)
        assert panel._drawing_run.currentText() == second
        profile = panel._drawing._profile
        assert [link.link_id for link in profile.links] == ["link:a"]
        assert profile.links[0].selected and profile.links[0].pipe_diameter_m == 0.6
        assert {marker.label for marker in profile.markers} == {"inlet:a", "outfall:a"}

        panel._table.selectRow(0)
        assert panel._drawing_run.currentText() == first
        assert panel._drawing._profile.links == ()

        # a pipe typed into the table shows at once; text that is no number says why it cannot draw
        panel._link_table.item(0, 3).setText("0.45")
        panel._drawing_run.setCurrentText(second)
        assert panel._drawing._profile.links[0].pipe_diameter_m == 0.45
        panel._link_table.item(0, 3).setText("wide")
        assert panel._drawing._profile is None and "cannot be drawn" in panel._drawing._message
        panel._link_table.item(0, 3).setText("0.45")

        # Apply keeps them and the drawing reads the new result
        assert panel._apply() is True
        assert panel._drawing._profile.links[0].pipe_diameter_m == 0.45
    finally:
        App.closeDocument(doc.Name)


def test_the_drawing_says_why_there_is_no_flowline_before_the_result_exists() -> None:
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc, _project = _road_with_ditches("V1DrainageDrawingEmpty")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        assert panel._drawing_run.count() == 0
        assert panel._drawing._profile is None
        assert "Rebuild Downstream" in panel._drawing._message
    finally:
        App.closeDocument(doc.Name)
