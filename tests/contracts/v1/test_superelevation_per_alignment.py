"""Item 5.5: superelevation belongs to one Alignment, like Profile and Region.

One source was resolved first-found and handed to every road, so a side road
consumed the main road's crossfall at its own stations. Each Alignment now has one
source object, and a write for that Alignment lands in it whatever object name the
writer passes, so an edit can no longer hide behind the preset's source.
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.source.superelevation_model import (
    CrossfallControlRow,
    SuperelevationModel,
)
from freecad.Corridor_Road.v1.objects.obj_superelevation import (
    create_or_update_v1_superelevation_source_object,
    to_superelevation_model,
)

PRIMARY = "alignment:intersection-primary"
SECONDARY = "alignment:intersection-secondary"
CURVE = (
    CrossfallControlRow(control_row_id="c1L", station=0.0, side="left", crossfall_value=-3.0),
    CrossfallControlRow(control_row_id="c1R", station=0.0, side="right", crossfall_value=-3.0),
    CrossfallControlRow(control_row_id="c2L", station=60.0, side="left", crossfall_value=-7.0),
    CrossfallControlRow(control_row_id="c2R", station=60.0, side="right", crossfall_value=7.0),
)


def _crossfall_by_alignment(applied, station):
    output = {}
    for section in applied.sections:
        if round(float(getattr(section, "station", 0.0)), 3) != station:
            continue
        output[str(getattr(section, "alignment_id", ""))] = (
            round(float(getattr(section, "superelevation_left_crossfall", 0.0)), 2),
            round(float(getattr(section, "superelevation_right_crossfall", 0.0)), 2),
            str(getattr(section, "active_superelevation_id", "") or ""),
        )
    return output


def _write_source(doc, *, alignment_id, superelevation_id, object_name, control_rows=()):
    return create_or_update_v1_superelevation_source_object(
        document=doc,
        project=find_project(doc),
        superelevation_model=SuperelevationModel(
            schema_version=1,
            project_id="project:test",
            superelevation_id=superelevation_id,
            alignment_id=alignment_id,
            control_rows=list(control_rows),
        ),
        object_name=object_name,
        label=superelevation_id,
    )


def test_the_preset_writes_one_superelevation_source_for_each_road() -> None:
    doc = App.newDocument("CRV1SuperelevationPresetPerRoad")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        by_alignment = {}
        for obj in list(doc.Objects):
            model = to_superelevation_model(obj)
            if model is not None:
                by_alignment[str(model.alignment_id)] = str(model.superelevation_id)

        assert set(by_alignment) == {PRIMARY, SECONDARY}
        assert by_alignment[PRIMARY] != by_alignment[SECONDARY]
    finally:
        App.closeDocument(doc.Name)


def test_a_side_road_source_applies_to_the_side_road_only() -> None:
    doc = App.newDocument("CRV1SuperelevationSideRoadOnly")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        _write_source(
            doc,
            alignment_id=SECONDARY,
            superelevation_id="superelevation:side-curve",
            object_name="V1SuperelevationSideCurve",
            control_rows=CURVE,
        )
        doc.recompute()

        applied = build_document_applied_section_set(doc, project=find_project(doc))
        at_sixty = _crossfall_by_alignment(applied, 60.0)

        # the side road is superelevated by its own source
        assert at_sixty[SECONDARY][:2] == (-7.0, 7.0)
        assert at_sixty[SECONDARY][2] == "superelevation:side-curve"
        # and the main road is untouched by it
        assert at_sixty[PRIMARY][:2] == (-3.0, -3.0)
        assert at_sixty[PRIMARY][2] != "superelevation:side-curve"
    finally:
        App.closeDocument(doc.Name)


def test_a_source_for_another_alignment_is_not_read_at_this_road_stations() -> None:
    doc = App.newDocument("CRV1SuperelevationNoCrossRead")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        # a curve that belongs to a third Alignment which no road in this document uses
        _write_source(
            doc,
            alignment_id="alignment:somewhere-else",
            superelevation_id="superelevation:foreign",
            object_name="V1SuperelevationForeign",
            control_rows=CURVE,
        )
        doc.recompute()

        applied = build_document_applied_section_set(doc, project=find_project(doc))
        at_sixty = _crossfall_by_alignment(applied, 60.0)

        for alignment_id in (PRIMARY, SECONDARY):
            assert at_sixty[alignment_id][2] != "superelevation:foreign"
            assert at_sixty[alignment_id][:2] == (-3.0, -3.0)
    finally:
        App.closeDocument(doc.Name)


def test_a_road_without_a_source_reports_no_superelevation_contribution() -> None:
    doc = App.newDocument("CRV1SuperelevationTemplateDefault")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        # remove the side road's source, leaving that road with none
        for obj in list(doc.Objects):
            model = to_superelevation_model(obj)
            if model is not None and str(model.alignment_id) == SECONDARY:
                doc.removeObject(obj.Name)
        doc.recompute()

        applied = build_document_applied_section_set(doc, project=find_project(doc))
        at_zero = _crossfall_by_alignment(applied, 0.0)

        left, right, active = at_zero[SECONDARY]
        # no source, so no superelevation contribution and no active source id. The
        # section still carries the subassembly template's own crossfall in its geometry;
        # returning a synthetic default here would be applied as geometry rather than
        # recorded, which moved a 2 percent lane to 3 percent when it was tried.
        assert active == ""
        assert (left, right) == (0.0, 0.0)
    finally:
        App.closeDocument(doc.Name)


def test_an_edit_for_a_road_is_written_into_that_road_source() -> None:
    doc = App.newDocument("CRV1SuperelevationEditInPlace")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        # written after the preset, under another object name, as the editor once did
        _write_source(
            doc,
            alignment_id=PRIMARY,
            superelevation_id="superelevation:authored",
            object_name="V1SuperelevationSource",
            control_rows=CURVE,
        )
        doc.recompute()

        primary_sources = [
            obj for obj in doc.Objects
            if to_superelevation_model(obj) is not None and to_superelevation_model(obj).alignment_id == PRIMARY
        ]
        assert len(primary_sources) == 1
        assert to_superelevation_model(primary_sources[0]).superelevation_id == "superelevation:authored"

        applied = build_document_applied_section_set(doc, project=find_project(doc))
        at_sixty = _crossfall_by_alignment(applied, 60.0)
        assert at_sixty[PRIMARY][2] == "superelevation:authored"
        assert at_sixty[PRIMARY][:2] == (-7.0, 7.0)
    finally:
        App.closeDocument(doc.Name)
