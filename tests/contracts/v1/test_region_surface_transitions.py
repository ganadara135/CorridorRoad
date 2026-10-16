"""GR-5: Surface Transitions are authored in the Regions panel.

The Region editor edits each transition's station, half length, spacing and enabled state next to
the Region rows and stores them on Apply. From and To follow from the Region rows at Apply time.
Build Parametric only reviews them.
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import apply_v1_corridor_model
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import apply_v1_applied_section_set
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_region_editor import V1RegionEditorTaskPanel, apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionRow
from freecad.Corridor_Road.v1.models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_surface_transition import find_v1_surface_transition_model, to_surface_transition_model
from freecad.Corridor_Road.v1.services.editing.surface_transition_editing_service import (
    TransitionRowDraft,
    merged_transition_model,
    region_boundary_stations,
    region_refs_at_station,
    transition_draft_problems,
)

_QAPP = None
ROWS = [
    RegionRow(region_id="region:1", region_index=1, station_start=0.0, station_end=20.0),
    RegionRow(region_id="region:2", region_index=2, station_start=20.0, station_end=40.0),
]


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _source_doc(name: str):
    doc = App.newDocument(name)
    project = create_corridorroad_project(doc)
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    # the Bridge Segment boundaries, STA 63 and 117, are stations at a 9 m interval
    create_v1_stationing(doc, project=project, alignment=alignment, interval=9.0)
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    apply_v1_region_model(
        document=doc,
        project=project,
        region_model=region_preset_model_from_document("Bridge Segment", doc, project=project, alignment=alignment),
    )
    return doc, project, alignment


def _stored_ranges(doc) -> list[SurfaceTransitionRange]:
    model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    return list(model.transition_ranges) if model is not None else []


def test_the_regions_at_a_station() -> None:
    assert region_refs_at_station(ROWS, 20.0) == ("region:1", "region:2")
    assert region_refs_at_station(ROWS, 10.0) == ("region:1", "region:1")
    assert region_refs_at_station(ROWS, 0.0) == ("region:1", "region:1")
    assert region_refs_at_station(ROWS, 40.0) == ("region:2", "region:2")
    assert region_refs_at_station(ROWS, 55.0) == ("", "")
    assert region_boundary_stations(ROWS) == [20.0]
    assert transition_draft_problems([TransitionRowDraft(55.0), TransitionRowDraft(20.0), TransitionRowDraft(20.0)], ROWS) == [
        "Transition row 1: STA 55.000 is outside every Region.",
        "Transition row 3: another row is at STA 20.000.",
    ]


def test_a_road_replaces_only_its_own_ranges_and_keeps_the_mode_of_a_kept_station() -> None:
    other_road = SurfaceTransitionRange(
        transition_id="surface-transition:a->b@5.000",
        station_start=0.0,
        station_end=10.0,
        source_ref="region-editor:alignment:other",
    )
    previous = SurfaceTransitionRange(
        transition_id="surface-transition:region:1->region:2@20.000",
        station_start=15.0,
        station_end=25.0,
        transition_mode="interpolate_width",
        source_ref="region-editor:alignment:main",
    )
    existing = SurfaceTransitionModel(
        schema_version=1,
        project_id="p",
        transition_model_id="surface-transitions:main",
        transition_ranges=[other_road, previous],
    )

    merged = merged_transition_model(
        existing,
        [TransitionRowDraft(station=20.0, half_length=2.0, sample_interval=1.0, enabled=False)],
        ROWS,
        alignment_id="alignment:main",
        single_road=False,
        project_id="p",
    )

    by_id = {row.transition_id: row for row in merged.transition_ranges}
    assert set(by_id) == {"surface-transition:a->b@5.000", "surface-transition:region:1->region:2@20.000"}
    edited = by_id["surface-transition:region:1->region:2@20.000"]
    assert (edited.station_start, edited.station_end, edited.sample_interval, edited.enabled) == (18.0, 22.0, 1.0, False)
    assert edited.transition_mode == "interpolate_width"


def test_the_regions_panel_round_trips_transition_rows() -> None:
    _ensure_qapp()
    doc, _project, alignment = _source_doc("CRV1RegionTransitions")
    try:
        panel = V1RegionEditorTaskPanel(document=doc, alignment=alignment)
        assert panel._transition_table.rowCount() == 0

        panel._add_boundary_transitions()
        assert panel._transition_table.rowCount() == 2
        assert panel._transition_table.item(0, 4).text() == "region:1 -> region:2"
        panel._transition_table.item(0, 2).setText("1.0")
        panel._transition_table.item(1, 3).setCheckState(QtCore.Qt.Unchecked)
        assert panel._apply(close_after=False) is True

        ranges = _stored_ranges(doc)
        assert [(row.from_region_ref, row.to_region_ref) for row in ranges] == [("region:1", "region:2"), ("region:2", "region:3")]
        assert [row.sample_interval for row in ranges] == [1.0, 2.5]
        assert [row.enabled for row in ranges] == [True, False]

        reopened = V1RegionEditorTaskPanel(document=doc, alignment=alignment)
        assert reopened._transition_drafts() == panel._transition_drafts()

        reopened._transition_table.selectRow(1)
        reopened._delete_selected_transition()
        assert reopened._apply(close_after=False) is True
        assert len(_stored_ranges(doc)) == 1
    finally:
        App.closeDocument(doc.Name)


def test_a_transition_follows_its_station_when_regions_are_renumbered() -> None:
    _ensure_qapp()
    doc, _project, alignment = _source_doc("CRV1RegionTransitionsRenumber")
    try:
        panel = V1RegionEditorTaskPanel(document=doc, alignment=alignment)
        panel._add_boundary_transitions()
        second_boundary = panel._transition_drafts()[1].station
        panel._transition_table.selectRow(0)
        panel._delete_selected_transition()
        # deleting the middle Region renumbers the last one, region:3 -> region:2
        panel._table.selectRow(1)
        panel._delete_selected_rows()
        assert panel._apply(close_after=False) is True

        (row,) = _stored_ranges(doc)
        assert round(0.5 * (row.station_start + row.station_end), 3) == round(second_boundary, 3)
        assert (row.from_region_ref, row.to_region_ref) == ("region:1", "region:2")
    finally:
        App.closeDocument(doc.Name)


def test_building_the_corridor_writes_no_surface_transition_source() -> None:
    doc, project, _alignment = _source_doc("CRV1RegionTransitionsBuild")
    try:
        show_v1_centerline3d_preview_object(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project)
        apply_v1_corridor_model(document=doc, project=project)

        assert find_v1_surface_transition_model(doc) is None
    finally:
        App.closeDocument(doc.Name)
