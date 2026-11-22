"""The intersection kernel's low points on the Review tab of the Drainage panel (DR-8)."""

from dataclasses import dataclass

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import V1DrainageEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_drainage_review import (
    INTERSECTION_LOW_OBJECT_NAME,
    drainage_intersection_low_state,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import create_intersection_preset_sources
from freecad.Corridor_Road.v1.models.result.intersection_geometry import DrainageCandidate
from freecad.Corridor_Road.v1.ui.presentation.drainage_review_presentation import drainage_intersection_low_rows


@dataclass(frozen=True)
class _Result:
    intersection_id: str = "x:1"
    drainage_candidates: tuple = ()


def _preset_doc(label="Cross Intersection - Basic", *, applied=True):
    doc = App.newDocument("CRV1DrainageIntersectionLows")
    create_intersection_preset_sources(doc, preset_label=label)
    if applied:
        project = find_project(doc)
        sections = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=sections)
    return doc


def test_a_row_gathers_the_low_vertices_of_one_road() -> None:
    rows = drainage_intersection_low_rows(
        _Result(
            drainage_candidates=(
                DrainageCandidate(1.0, 2.0, 10.5, "road:b", 40.0),
                DrainageCandidate(3.0, 4.0, 10.5, "road:a", 12.0),
                DrainageCandidate(5.0, 6.0, 10.4992, "road:a", 15.5),
            )
        )
    )
    assert [(row["road_ref"], row["stations"], row["elevation"], row["places"]) for row in rows] == [
        ("road:a", "12.000-15.500", "10.499", 2),
        ("road:b", "40.000", "10.500", 1),
    ]
    assert rows[0]["xyz"] == ((3.0, 4.0, 10.5), (5.0, 6.0, 10.4992))


def test_no_result_gives_no_rows() -> None:
    assert drainage_intersection_low_rows(None) == []
    assert drainage_intersection_low_rows(_Result()) == []


def test_a_document_without_an_intersection_shows_nothing() -> None:
    doc = App.newDocument("CRV1DrainageNoIntersection")
    try:
        assert drainage_intersection_low_state(doc) == (None, "")
    finally:
        App.closeDocument(doc.Name)


@pytest.mark.parametrize("label", ["T Intersection - Basic", "Cross Intersection - Basic", "Roundabout - Single Lane"])
def test_every_kernel_low_vertex_is_in_a_row(label) -> None:
    doc = _preset_doc(label)
    try:
        result, note = drainage_intersection_low_state(doc)
        assert result.status == "ready" and note
        rows = drainage_intersection_low_rows(result)
        assert rows and sum(row["places"] for row in rows) == len(result.drainage_candidates)
        assert len({row["road_ref"] for row in rows}) == len(rows)
    finally:
        App.closeDocument(doc.Name)


def test_the_review_tab_lists_them_and_marks_one_without_touching_the_source() -> None:
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = _preset_doc()
    try:
        before = {obj.Name for obj in doc.Objects}
        panel = V1DrainageEditorTaskPanel(document=doc)
        # the kernel is not evaluated until the tab is in view
        assert panel._intersection_lows.rowCount() == 0
        panel._tabs.setCurrentWidget(panel._review_tab)
        assert panel._intersection_lows.rowCount() == len(panel._intersection_low_rows) > 0
        assert not panel._intersection_lows.isHidden()
        assert {obj.Name for obj in doc.Objects} == before

        panel._focus_intersection_low(0)
        marker = doc.getObject(INTERSECTION_LOW_OBJECT_NAME)
        assert marker is not None and not marker.Shape.isNull()
        assert marker.IssueKind == "drainage_intersection_low"
        assert {obj.Name for obj in doc.Objects} - before == {INTERSECTION_LOW_OBJECT_NAME}
    finally:
        App.closeDocument(doc.Name)


def test_the_review_tab_hides_the_table_without_an_intersection() -> None:
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRV1DrainageNoIntersectionPanel")
    try:
        panel = V1DrainageEditorTaskPanel(document=doc)
        panel._tabs.setCurrentWidget(panel._review_tab)
        assert panel._intersection_lows.isHidden() and panel._intersection_low_title.isHidden()
    finally:
        App.closeDocument(doc.Name)
