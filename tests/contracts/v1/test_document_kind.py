"""GR-1B: a document is a General Road document or an Intersection document.

A General Road document holds one Alignment and no Intersection, so intersection review content
is not shown and Intersection Presets work only before its road exists, switching it to an
Intersection document. A new project is a General Road document; a project that stores no kind is
judged by its content.
"""

import gc
from dataclasses import replace

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import create_blank_v1_alignment
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    V1BuildCorridorTaskPanel,
    corridor_build_guided_review_steps,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import build_document_applied_section_set
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    CmdV1IntersectionPresets,
    create_intersection_from_existing_alignments,
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.commands.cmd_project_setup import apply_v1_project_setup, create_corridorroad_project
from freecad.Corridor_Road.v1.objects.document_kind import (
    GENERAL_ROAD_ALIGNMENT_REFUSAL,
    document_kind,
    require_alignment_slot,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment, list_v1_alignments
from freecad.Corridor_Road.v1.objects.project_setup_adapter import project_setup_draft_from_project
from freecad.Corridor_Road.v1.services.editing.project_setup_service import (
    DOCUMENT_KIND_LABELS,
    document_kind_change_refusal,
    inferred_document_kind,
)
from freecad.Corridor_Road.v1.ui.viewers.cross_section_viewer import build_source_inspector_owner_rows

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _visible_review_tabs(panel) -> list[str]:
    tabs = panel.form.findChildren(QtWidgets.QTabWidget)
    tab_widget = next(widget for widget in tabs if widget.count() == len(panel._review_tab_ids))
    return [panel._review_tab_ids[index] for index in range(tab_widget.count()) if tab_widget.isTabVisible(index)]


def _project_doc(name: str, kind: str):
    doc = App.newDocument(name)
    project = create_corridorroad_project(doc)
    project.DocumentKind = kind
    return doc, project


def _set_kind(project, kind: str):
    draft = replace(project_setup_draft_from_project(project), document_kind=kind)
    return apply_v1_project_setup(project, draft)


def test_a_new_project_is_a_general_road_and_project_setup_can_change_it_before_a_road_exists() -> None:
    doc = App.newDocument("CRV1DocumentKindSetup")
    try:
        project = create_corridorroad_project(doc)
        assert project.DocumentKind == "general_road"
        assert list(DOCUMENT_KIND_LABELS.values()) == ["General Road", "Intersection"]

        result = _set_kind(project, "intersection")

        assert result.applied is True
        assert project.DocumentKind == "intersection"
    finally:
        App.closeDocument(doc.Name)


def test_the_kind_is_fixed_once_an_alignment_exists() -> None:
    doc, project = _project_doc("CRV1DocumentKindFixed", "general_road")
    try:
        create_sample_v1_alignment(doc, project=project)

        result = _set_kind(project, "intersection")

        assert result.applied is False
        assert "Document Kind stays 'General Road'" in result.refusal
        assert project.DocumentKind == "general_road"
    finally:
        App.closeDocument(doc.Name)


def test_the_kind_rules() -> None:
    assert document_kind_change_refusal("general_road", "intersection", alignment_count=0) == ""
    assert document_kind_change_refusal("general_road", "general_road", alignment_count=3) == ""
    assert document_kind_change_refusal("general_road", "intersection", alignment_count=1)
    assert inferred_document_kind(has_intersection=False, alignment_count=1) == "general_road"
    assert inferred_document_kind(has_intersection=False, alignment_count=2) == "intersection"
    assert inferred_document_kind(has_intersection=True, alignment_count=0) == "intersection"


def test_a_general_road_document_refuses_a_second_alignment() -> None:
    doc, project = _project_doc("CRV1DocumentKindOneRoad", "general_road")
    try:
        first = create_sample_v1_alignment(doc, project=project)

        with pytest.raises(RuntimeError, match="holds one Alignment"):
            create_sample_v1_alignment(doc, project=project)
        with pytest.raises(RuntimeError, match="holds one Alignment"):
            create_blank_v1_alignment(document=doc, project=project)
        # LandXML checks the ids it is about to write: the same road again is an update
        require_alignment_slot(doc, [first.AlignmentId])
        with pytest.raises(RuntimeError, match="holds one Alignment"):
            require_alignment_slot(doc, ["alignment:other"])

        assert list_v1_alignments(doc) == [first]
    finally:
        App.closeDocument(doc.Name)


def test_a_general_road_document_refuses_two_alignments_from_one_import() -> None:
    doc, _project = _project_doc("CRV1DocumentKindImport", "general_road")
    try:
        with pytest.raises(RuntimeError) as excinfo:
            require_alignment_slot(doc, ["alignment:a", "alignment:b"])
        assert str(excinfo.value) == GENERAL_ROAD_ALIGNMENT_REFUSAL
    finally:
        App.closeDocument(doc.Name)


def test_a_project_that_stores_no_kind_is_judged_by_its_content() -> None:
    doc, project = _project_doc("CRV1DocumentKindStoredNone", "")
    try:
        assert document_kind(doc) == "general_road"

        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        project.DocumentKind = ""
        assert document_kind(doc) == "intersection"
        # reading the kind does not store it
        assert project.DocumentKind == ""
    finally:
        App.closeDocument(doc.Name)


def test_intersection_presets_are_refused_once_a_general_road_has_its_road() -> None:
    doc, project = _project_doc("CRV1DocumentKindNoPresets", "general_road")
    try:
        App.setActiveDocument(doc.Name)
        assert CmdV1IntersectionPresets().IsActive() is True
        create_sample_v1_alignment(doc, project=project)
        assert CmdV1IntersectionPresets().IsActive() is False

        with pytest.raises(RuntimeError, match="not available in a General Road document"):
            create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        with pytest.raises(RuntimeError, match="not available in a General Road document"):
            create_intersection_from_existing_alignments(
                doc,
                preset_label="T Intersection - Basic",
                primary_alignment_ref="alignment:a",
                secondary_alignment_ref="alignment:b",
            )
        assert len(list_v1_alignments(doc)) == 1
    finally:
        App.closeDocument(doc.Name)


def test_a_preset_makes_a_new_general_road_document_an_intersection_document() -> None:
    doc, project = _project_doc("CRV1DocumentKindPreset", "general_road")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        assert project.DocumentKind == "intersection"
        App.setActiveDocument(doc.Name)
        assert CmdV1IntersectionPresets().IsActive() is True
    finally:
        App.closeDocument(doc.Name)


def test_a_general_road_document_with_an_intersection_source_does_not_build() -> None:
    doc = App.newDocument("CRV1DocumentKindStrayIntersection")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        project = find_project(doc)
        project.DocumentKind = "general_road"

        with pytest.raises(RuntimeError, match="General Road document builds one road"):
            build_document_applied_section_set(doc, project=project)
    finally:
        App.closeDocument(doc.Name)


def test_build_parametric_offers_no_intersection_review_in_a_general_road_document() -> None:
    _ensure_qapp()
    road_doc, _road_project = _project_doc("CRV1DocumentKindBuildRoad", "general_road")
    unset_doc, _unset_project = _project_doc("CRV1DocumentKindBuildIntersection", "intersection")
    try:
        road_panel = V1BuildCorridorTaskPanel(document=road_doc)
        unset_panel = V1BuildCorridorTaskPanel(document=unset_doc)

        assert _visible_review_tabs(road_panel) == [tab for tab in _visible_review_tabs(unset_panel) if tab != "intersections"]
        assert "intersections" in _visible_review_tabs(unset_panel)
        # the refresh after a build writes every table, the hidden tab's too
        gc.collect()
        road_panel._set_intersection_contract_review_rows([])
        assert "intersections" not in [row["step_id"] for row in corridor_build_guided_review_steps(road_doc)]
        assert "intersections" in [row["step_id"] for row in corridor_build_guided_review_steps(unset_doc)]
    finally:
        App.closeDocument(road_doc.Name)
        App.closeDocument(unset_doc.Name)


def test_the_cross_section_owner_rows_omit_the_intersection_in_a_general_road_document() -> None:
    def owners(kind: str) -> list[str]:
        return [row[0] for row in build_source_inspector_owner_rows({"source_inspector": {"document_kind": kind}})]

    assert "Intersection" not in owners("general_road")
    assert "Intersection" in owners("intersection")
