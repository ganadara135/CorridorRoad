"""The parametric spec as the stored source of an intersection (plan phase R7b).

The spec is stored on the Intersection object (`SpecJson`), written when an intersection is created
from a preset or from existing Alignments, and edited in the Intersection panel's Parametric Spec
group. The stored spec, not the rows, decides the geometry the kernel builds.
"""

import json

from dataclasses import replace

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    V1IntersectionPresetsTaskPanel,
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.source.intersection_spec import (
    AnchorSpec,
    CornerOverride,
    IntersectionSpec,
    LegOverride,
    RoundaboutSpec,
    intersection_spec_from_dict,
    intersection_spec_to_dict,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    store_intersection_spec,
    stored_intersection_spec,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.builders.intersection_kernel_context_service import spec_from_intersection_model
from freecad.Corridor_Road.v1.services.editing.intersection_spec_editing_service import (
    LegFormRow,
    form_from_spec,
    spec_from_form,
)

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _section_stations(doc, road):
    applied = build_document_applied_section_set(doc, project=find_project(doc))
    apply_v1_applied_section_set(document=doc, project=find_project(doc), applied_section_set=applied)
    return sorted(round(s.station, 6) for s in applied.sections if s.alignment_id == road)


FULL = IntersectionSpec(
    "x", "roundabout", ("a", "b"),
    anchor=AnchorSpec("manual", (("a", 10.0), ("b", 20.0)), (1.0, 2.0)),
    corner_radius_m=11.0,
    grading_mode="flatten_intersection",
    leg_overrides=(LegOverride("a", "ahead", False), LegOverride("b", "back", True, 6.0, 7.0)),
    corner_overrides=(CornerOverride("a:ahead|b:back", 9.0, "fillet"),),
    roundabout=RoundaboutSpec(12.0, 6.6, 0.99, 5.0, None, "cw"),
)


def test_a_spec_survives_its_json_round_trip() -> None:
    assert intersection_spec_from_dict(json.loads(json.dumps(intersection_spec_to_dict(FULL)))) == FULL
    plain = IntersectionSpec("t", "t", ("a", "b"))
    assert intersection_spec_from_dict(intersection_spec_to_dict(plain)) == plain


def test_the_form_gives_back_the_spec_it_was_loaded_from() -> None:
    spec, errors = spec_from_form(form_from_spec(FULL), base=FULL)
    assert not errors
    # the form stores only legs that change something; both of FULL's do
    assert spec == FULL


def test_the_form_says_what_is_wrong() -> None:
    form = form_from_spec(IntersectionSpec("t", "t", ("a", "a")))
    spec, errors = spec_from_form(form)
    assert spec is None and any("different" in e for e in errors)
    form = form_from_spec(IntersectionSpec("r", "roundabout", ("a", "b"), roundabout=RoundaboutSpec(6.0, 6.0)))
    spec, errors = spec_from_form(form)
    assert spec is None and any("central island" in e for e in errors)
    form = form_from_spec(IntersectionSpec("t", "t", ("a", "b")))
    form.corner_radius_m = -1.0
    assert spec_from_form(form)[0] is None


def test_a_leg_row_that_changes_nothing_is_not_stored() -> None:
    form = form_from_spec(IntersectionSpec("t", "t", ("a", "b")))
    form.leg_rows = [LegFormRow("a", "ahead"), LegFormRow("b", "back", False)]
    spec, _errors = spec_from_form(form)
    assert spec.leg_overrides == (LegOverride("b", "back", False),)


def test_creating_an_intersection_stores_its_spec_and_a_bad_spec_falls_back_to_the_rows() -> None:
    doc = App.newDocument("CRV1SpecStored")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        obj = find_v1_intersection_model(doc)
        stored = stored_intersection_spec(obj)
        assert stored is not None and stored == spec_from_intersection_model(to_intersection_model(obj))
        assert stored.kind == "t" and stored.corner_radius_m == 12.0
        obj.SpecJson = "{not json"
        assert stored_intersection_spec(obj) is None
    finally:
        App.closeDocument(doc.Name)


def test_the_stored_spec_decides_the_geometry() -> None:
    doc = App.newDocument("CRV1SpecDecides")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        obj = find_v1_intersection_model(doc)
        spec = stored_intersection_spec(obj)
        main = spec.road_refs[0]
        assert {103.0, 137.0} <= set(_section_stations(doc, main))
        # a 15 m radius: the fillet centre is 5 + 15 m from both centrelines, the mouths 20 m out
        store_intersection_spec(obj, replace(spec, corner_radius_m=15.0))
        stations = set(_section_stations(doc, main))
        assert {100.0, 140.0} <= stations and not ({103.0, 137.0} & stations)
    finally:
        App.closeDocument(doc.Name)


def test_the_panel_loads_checks_and_applies_the_spec() -> None:
    _ensure_qapp()
    doc = App.newDocument("CRV1SpecPanel")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        apply_v1_applied_section_set(
            document=doc, project=find_project(doc), applied_section_set=build_document_applied_section_set(doc, project=find_project(doc))
        )
        panel = V1IntersectionPresetsTaskPanel(document=doc)
        assert panel._load_spec()
        assert panel._spec_kind_combo.currentData() == "t"
        assert panel._spec_corner_radius.value() == pytest.approx(12.0)
        assert not panel._spec_ring_group.isVisibleTo(panel.form)

        result = panel._check_spec()
        assert result is not None and result.status == "ready"
        assert panel._spec_leg_table.rowCount() == 3
        text = panel._status.toPlainText()
        assert "Kernel status: ready" in text and "corner_radius_m" in text and "(spec)" in text

        panel._spec_corner_radius.setValue(15.0)
        assert panel._apply_spec()
        obj = find_v1_intersection_model(doc)
        assert stored_intersection_spec(obj).corner_radius_m == 15.0

        # a closed leg: untick the side road, check, and the kernel no longer has it
        panel._check_spec()
        for row in range(panel._spec_leg_table.rowCount()):
            if panel._spec_leg_table.item(row, 0).text() == stored_intersection_spec(obj).road_refs[1]:
                panel._spec_leg_table.item(row, 2).setCheckState(_unchecked_state())
        spec, errors = spec_from_form(panel._spec_form())
        assert not errors and any(not row.enabled for row in spec.leg_overrides)
    finally:
        App.closeDocument(doc.Name)


def _unchecked_state():
    from freecad.Corridor_Road.qt_compat import QtCore

    holder = getattr(QtCore.Qt, "CheckState", QtCore.Qt)
    return getattr(holder, "Unchecked", getattr(QtCore.Qt, "Unchecked"))
