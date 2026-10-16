"""GR-1: one source object per concern.

Readers pair Profile, Region, Stationing and Superelevation with their Alignment and read
Drainage as the project's single object. Writers used fixed object names, so on an
intersection preset document an editor wrote a second object for a road that the build
never read. Writes now land in the object of the same identity, editors open the
selected road's source, and a duplicate that still exists stops the build.
"""

import FreeCAD as App
import pytest

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import build_document_applied_section_set
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import create_intersection_preset_sources
from freecad.Corridor_Road.v1.commands.cmd_region_editor import V1RegionEditorTaskPanel, apply_v1_region_model
from freecad.Corridor_Road.v1.commands.cmd_review_stations import V1StationingReviewTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_superelevation_editor import V1SuperelevationEditorTaskPanel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageModel
from freecad.Corridor_Road.v1.objects.obj_alignment import find_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_drainage import (
    create_or_update_v1_drainage_model_object,
    list_v1_drainage_models,
)
from freecad.Corridor_Road.v1.objects.obj_region import (
    V1RegionModelObject,
    find_v1_region_model,
    list_v1_region_models,
    to_region_model,
    update_v1_region_model_object,
)
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing, find_v1_stationing, list_v1_stationings
from freecad.Corridor_Road.v1.objects.obj_superelevation import list_v1_superelevation_sources, to_superelevation_model
from freecad.Corridor_Road.v1.objects.source_identity import duplicate_source_rows

PRIMARY = "alignment:intersection-primary"
SECONDARY = "alignment:intersection-secondary"
PRESETS = ("T Intersection - Basic", "Cross Intersection - Basic", "Roundabout - Single Lane")

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _preset_doc(name: str, preset: str = "T Intersection - Basic"):
    doc = App.newDocument(name)
    create_intersection_preset_sources(doc, preset_label=preset)
    return doc


def _names(objects) -> list[str]:
    return sorted(str(obj.Name) for obj in objects)


@pytest.mark.parametrize("preset", PRESETS)
def test_preset_documents_hold_each_source_once(preset) -> None:
    doc = _preset_doc("CRV1SourceIdentityPreset", preset)
    try:
        assert duplicate_source_rows(doc) == []
        assert list_v1_drainage_models(doc) == []
    finally:
        App.closeDocument(doc.Name)


def test_applying_a_road_region_updates_the_object_the_build_reads() -> None:
    doc = _preset_doc("CRV1SourceIdentityRegionApply")
    try:
        before = _names(list_v1_region_models(doc))
        region_obj = find_v1_region_model(doc, alignment_id=PRIMARY)
        label = region_obj.Label
        model = to_region_model(region_obj)

        applied = apply_v1_region_model(document=doc, region_model=model)

        assert applied is region_obj
        assert applied.Label == label
        assert _names(list_v1_region_models(doc)) == before
    finally:
        App.closeDocument(doc.Name)


def test_region_editor_opens_the_selected_road_source() -> None:
    _ensure_qapp()
    doc = _preset_doc("CRV1SourceIdentityRegionPanel")
    try:
        panel = V1RegionEditorTaskPanel(document=doc, alignment=find_v1_alignment(doc, alignment_id=SECONDARY))

        assert panel.region_obj is find_v1_region_model(doc, alignment_id=SECONDARY)
        assert panel._model_from_table().alignment_id == SECONDARY
    finally:
        App.closeDocument(doc.Name)


def test_superelevation_editor_writes_the_selected_road_source() -> None:
    _ensure_qapp()
    doc = _preset_doc("CRV1SourceIdentitySuperelevationPanel")
    try:
        before = _names(list_v1_superelevation_sources(doc))
        panel = V1SuperelevationEditorTaskPanel(document=doc, alignment=find_v1_alignment(doc, alignment_id=SECONDARY))
        assert to_superelevation_model(panel.superelevation_obj).alignment_id == SECONDARY
        panel._add_control_row()

        assert panel._apply(close_after=False) is True

        assert _names(list_v1_superelevation_sources(doc)) == before
        model = to_superelevation_model(panel.superelevation_obj)
        assert model.alignment_id == SECONDARY
        assert len(model.control_rows) == 1
    finally:
        App.closeDocument(doc.Name)


def test_generating_stations_again_resamples_the_road_stationing() -> None:
    doc = _preset_doc("CRV1SourceIdentityStationing")
    try:
        before = _names(list_v1_stationings(doc))
        alignment = find_v1_alignment(doc, alignment_id=SECONDARY)

        again = create_v1_stationing(doc, alignment=alignment, interval=5.0)

        assert again is find_v1_stationing(doc, alignment_id=SECONDARY)
        assert float(again.Interval) == 5.0
        assert _names(list_v1_stationings(doc)) == before
    finally:
        App.closeDocument(doc.Name)


def test_stations_panel_pairs_a_stationing_with_its_own_alignment() -> None:
    _ensure_qapp()
    doc = _preset_doc("CRV1SourceIdentityStationsPanel")
    try:
        secondary_alignment = find_v1_alignment(doc, alignment_id=SECONDARY)
        secondary_stationing = find_v1_stationing(doc, alignment_id=SECONDARY)

        by_alignment = V1StationingReviewTaskPanel(document=doc, preferred_alignment=secondary_alignment)
        # a selected Stationing names its Alignment, whatever Alignment is also preferred
        by_stationing = V1StationingReviewTaskPanel(
            document=doc,
            stationing=secondary_stationing,
            preferred_alignment=find_v1_alignment(doc, alignment_id=PRIMARY),
        )

        assert by_alignment.stationing is secondary_stationing
        assert by_stationing.preferred_alignment is secondary_alignment
    finally:
        App.closeDocument(doc.Name)


def test_a_project_has_one_drainage_object() -> None:
    doc = App.newDocument("CRV1SourceIdentityDrainage")
    try:
        first = create_or_update_v1_drainage_model_object(
            doc, drainage_model=DrainageModel(schema_version=1, project_id="p", drainage_model_id="drainage:main")
        )
        second = create_or_update_v1_drainage_model_object(
            doc,
            drainage_model=DrainageModel(schema_version=1, project_id="p", drainage_model_id="drainage:other"),
            object_name="V1OtherDrainage",
        )

        assert second is first
        assert list_v1_drainage_models(doc) == [first]
        assert first.DrainageModelId == "drainage:other"
    finally:
        App.closeDocument(doc.Name)


def test_a_duplicate_source_stops_the_build_and_names_both_objects() -> None:
    doc = _preset_doc("CRV1SourceIdentityDuplicate")
    try:
        original = find_v1_region_model(doc, alignment_id=PRIMARY)
        # a second Region object for the same road, as an older editor would have written
        extra = doc.addObject("App::FeaturePython", "V1RegionModel")
        V1RegionModelObject(extra)
        update_v1_region_model_object(extra, to_region_model(original), label="Extra Regions")

        rows = duplicate_source_rows(doc)

        assert [(row["source_kind"], row["alignment_id"]) for row in rows] == [("Regions", PRIMARY)]
        assert sorted(rows[0]["object_names"]) == sorted([original.Name, extra.Name])
        with pytest.raises(RuntimeError, match="Regions for alignment:intersection-primary"):
            build_document_applied_section_set(doc, project=find_project(doc))
    finally:
        App.closeDocument(doc.Name)
