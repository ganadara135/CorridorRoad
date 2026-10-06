"""Item 5.8: `Use Existing Alignments` creates the source set a preset does.

Before this the mode wrote only the IntersectionModel and refused unless the user had
already authored intersection-tagged Regions by hand. A real route has its own Region
model, so the control Region is added as an overlay row and the user's rows are left
exactly as they were.
"""

import pytest

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    create_starter_intersection_sources,
    intersection_ref_for_kind,
    list_intersection_control_region_choices,
    list_v1_alignment_choices,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_from_existing_alignments,
    ensure_existing_alignment_control_regions,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.superelevation_model import SuperelevationModel
from freecad.Corridor_Road.v1.objects.obj_intersection import find_v1_intersection_model, to_intersection_model
from freecad.Corridor_Road.v1.objects.obj_region import to_region_model, update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_superelevation import (
    create_or_update_v1_superelevation_source_object,
    to_superelevation_model,
)
from freecad.Corridor_Road.v1.services.editing import build_control_region_overlay
from freecad.Corridor_Road.v1.services.evaluation.region_resolution_service import RegionResolutionService

LABEL = "T Intersection - Basic"
KIND = "t_intersection"


def _user_route(doc):
    """Alignments, Profiles and Assembly from the starter, with one hand-written Region row each."""

    create_starter_intersection_sources(doc, KIND)
    user_rows = {}
    for obj in list(doc.Objects):
        model = to_region_model(obj)
        if model is None:
            continue
        length = max(float(row.station_end) for row in model.region_rows)
        template = next(row for row in model.region_rows if row.assembly_ref)
        user_row = RegionRow(
            region_id="region:user-whole-road",
            region_index=1,
            station_start=0.0,
            station_end=length,
            assembly_ref=template.assembly_ref,
            template_ref=template.template_ref,
            priority=10,
            notes="Written by the user.",
        )
        update_v1_region_model_object(
            obj,
            RegionModel(
                schema_version=1,
                project_id=model.project_id,
                region_model_id=model.region_model_id,
                alignment_id=model.alignment_id,
                label=model.label,
                region_rows=[user_row],
            ),
            label=str(obj.Label),
        )
        user_rows[model.alignment_id] = user_row
    doc.recompute()
    refs = [ref for ref, _label in list_v1_alignment_choices(doc)]
    assert len(refs) == 2
    assert list_intersection_control_region_choices(doc, intersection_ref_for_kind(KIND)) == []
    return refs[0], refs[1], user_rows


def _region_model_for(doc, alignment_ref):
    return next(
        model
        for model in (to_region_model(obj) for obj in doc.Objects)
        if model is not None and model.alignment_id == alignment_ref
    )


def test_a_real_route_gets_overlay_control_regions_and_the_rest_of_the_preset_source_set() -> None:
    doc = App.newDocument("CRV1ExistingAlignmentSources")
    try:
        primary, secondary, user_rows = _user_route(doc)
        details: list[str] = []

        obj, control_region_count = create_intersection_from_existing_alignments(
            doc,
            preset_label=LABEL,
            primary_alignment_ref=primary,
            secondary_alignment_ref=secondary,
            control_length=30.0,
            details=details,
        )

        assert control_region_count == 2
        stored = to_intersection_model(obj)
        assert stored.intersection_rows[0].source_mode == "use_existing_alignments"
        for ref in (primary, secondary):
            model = _region_model_for(doc, ref)
            original, overlay = model.region_rows
            # the user's row is exactly what the user wrote
            assert original == user_rows[ref]
            assert overlay.intersection_ref == intersection_ref_for_kind(KIND)
            assert overlay.priority > original.priority
            length = overlay.station_end - overlay.station_start
            # centred on the crossing, so a full control length unless the road ends first
            assert 0.0 < length <= 30.0 + 1e-9
            if overlay.station_end < original.station_end - 1e-9:
                assert length == pytest.approx(30.0)
            assert overlay.assembly_ref == original.assembly_ref
            assert overlay.template_ref == original.template_ref
            service = RegionResolutionService()
            middle = (overlay.station_start + overlay.station_end) / 2.0
            assert service.resolve_station(model, middle).active_region_id == overlay.region_id
            assert service.resolve_station(model, middle).resolved_intersection_ref == overlay.intersection_ref
            assert service.resolve_station(model, overlay.station_start - 1.0).active_region_id == original.region_id
        # one handoff source per road, and the drainage source the preset also writes
        handoffs = [
            to_superelevation_model(item)
            for item in doc.Objects
            if to_superelevation_model(item) is not None
        ]
        assert sorted(model.alignment_id for model in handoffs) == sorted([primary, secondary])
        assert doc.getObject("V1IntersectionPresetDrainage") is not None
        assert any(line.startswith("Control Region:") for line in details)
        assert any(line.startswith("Drainage:") for line in details)
        # the Region overlay is what Applied Sections reads, so it must still build
        assert len(build_document_applied_section_set(doc).sections) > 0
    finally:
        App.closeDocument(doc.Name)


def test_applying_twice_adds_no_second_control_region() -> None:
    doc = App.newDocument("CRV1ExistingAlignmentTwice")
    try:
        primary, secondary, _rows = _user_route(doc)
        for _ in range(2):
            create_intersection_from_existing_alignments(
                doc,
                preset_label=LABEL,
                primary_alignment_ref=primary,
                secondary_alignment_ref=secondary,
            )

        assert [len(_region_model_for(doc, ref).region_rows) for ref in (primary, secondary)] == [2, 2]
    finally:
        App.closeDocument(doc.Name)


def test_hand_authored_control_regions_are_kept_and_nothing_is_added() -> None:
    doc = App.newDocument("CRV1ExistingAlignmentHandAuthored")
    try:
        create_starter_intersection_sources(doc, KIND)
        refs = [ref for ref, _label in list_v1_alignment_choices(doc)]
        before = [len(_region_model_for(doc, ref).region_rows) for ref in refs]

        lines = ensure_existing_alignment_control_regions(
            doc,
            preset_label=LABEL,
            primary_alignment_ref=refs[0],
            secondary_alignment_ref=refs[1],
        )

        assert lines and "kept" in lines[0]
        assert [len(_region_model_for(doc, ref).region_rows) for ref in refs] == before
    finally:
        App.closeDocument(doc.Name)


def test_a_road_with_its_own_superelevation_source_keeps_it() -> None:
    doc = App.newDocument("CRV1ExistingAlignmentSuperelevation")
    try:
        primary, secondary, _rows = _user_route(doc)
        create_or_update_v1_superelevation_source_object(
            document=doc,
            superelevation_model=SuperelevationModel(
                schema_version=1,
                project_id="project:test",
                label="User Superelevation",
                superelevation_id="superelevation:user-main",
                alignment_id=primary,
            ),
            object_name="V1UserSuperelevation",
            label="User Superelevation",
        )

        create_intersection_from_existing_alignments(
            doc,
            preset_label=LABEL,
            primary_alignment_ref=primary,
            secondary_alignment_ref=secondary,
        )

        by_alignment = {}
        for item in doc.Objects:
            model = to_superelevation_model(item)
            if model is not None:
                by_alignment.setdefault(model.alignment_id, []).append(model.superelevation_id)
        assert by_alignment[primary] == ["superelevation:user-main"]
        assert len(by_alignment[secondary]) == 1
        assert by_alignment[secondary][0].startswith("superelevation:intersection-preset-")
    finally:
        App.closeDocument(doc.Name)


def test_a_road_without_a_region_model_is_refused_and_nothing_is_written() -> None:
    doc = App.newDocument("CRV1ExistingAlignmentNoRegion")
    try:
        primary, secondary, _rows = _user_route(doc)
        secondary_regions = next(
            obj for obj in doc.Objects
            if to_region_model(obj) is not None and to_region_model(obj).alignment_id == secondary
        )
        doc.removeObject(secondary_regions.Name)

        with pytest.raises(ValueError, match="has no Region model"):
            create_intersection_from_existing_alignments(
                doc,
                preset_label=LABEL,
                primary_alignment_ref=primary,
                secondary_alignment_ref=secondary,
            )

        # the primary Region was built first and must not have been written
        assert len(_region_model_for(doc, primary).region_rows) == 1
        assert find_v1_intersection_model(doc) is None
    finally:
        App.closeDocument(doc.Name)


def _model(*rows):
    return RegionModel(
        schema_version=1,
        project_id="project:test",
        region_model_id="regions:test",
        alignment_id="alignment:test",
        region_rows=list(rows),
    )


def _row(region_id, start, end, *, priority=10, assembly="assembly:a"):
    return RegionRow(
        region_id=region_id,
        region_index=1,
        station_start=start,
        station_end=end,
        assembly_ref=assembly,
        priority=priority,
    )


def test_the_overlay_inherits_from_the_row_active_at_the_crossing_and_is_clipped_to_the_span() -> None:
    model = _model(
        _row("region:a", 0.0, 50.0, assembly="assembly:a"),
        _row("region:b", 50.0, 120.0, assembly="assembly:b", priority=95),
    )

    overlay = build_control_region_overlay(
        model, station=110.0, control_length=40.0, intersection_ref="intersection:x", role="primary", kind=KIND
    )

    assert overlay.base_region_id == "region:b"
    assert overlay.row.assembly_ref == "assembly:b"
    # clipped at the end of the covered span, not extended past it
    assert (overlay.row.station_start, overlay.row.station_end) == (90.0, 120.0)
    # above the highest existing priority, including one already above the default
    assert overlay.row.priority == 105
    assert overlay.model.region_rows[:2] == model.region_rows
    assert RegionResolutionService().resolve_station(overlay.model, 100.0).active_region_id == overlay.row.region_id


def test_the_overlay_refuses_what_it_would_have_to_invent() -> None:
    covered = _model(_row("region:a", 0.0, 100.0))
    kwargs = dict(intersection_ref="intersection:x", role="primary", kind=KIND)

    with pytest.raises(ValueError, match="outside the Regions"):
        build_control_region_overlay(covered, station=150.0, control_length=20.0, **kwargs)
    with pytest.raises(ValueError, match="no Region rows"):
        build_control_region_overlay(_model(), station=10.0, control_length=20.0, **kwargs)
    with pytest.raises(ValueError, match="greater than zero"):
        build_control_region_overlay(covered, station=10.0, control_length=0.0, **kwargs)
    # an id already used is not reused
    taken = build_control_region_overlay(covered, station=50.0, control_length=10.0, **kwargs).model
    second = build_control_region_overlay(taken, station=50.0, control_length=10.0, **kwargs)
    assert len({row.region_id for row in second.model.region_rows}) == 3


def test_the_panel_reports_what_applying_existing_alignments_created(monkeypatch) -> None:
    from freecad.Corridor_Road.qt_compat import QtWidgets
    from freecad.Corridor_Road.v1.commands import cmd_intersection_presets
    from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import V1IntersectionPresetsTaskPanel

    messages: list[str] = []
    # a real QMessageBox is modal and would wait for a click that never comes
    monkeypatch.setattr(cmd_intersection_presets, "_show_message", lambda parent, title, text: messages.append(text))
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    doc = App.newDocument("CRV1ExistingAlignmentPanel")
    try:
        _user_route(doc)
        panel = V1IntersectionPresetsTaskPanel(document=doc)
        panel._refresh_alignment_choices()
        # index 0 of each combo is the empty entry, so the user picks one road in each
        panel._primary_alignment_combo.setCurrentIndex(1)
        panel._secondary_alignment_combo.setCurrentIndex(2)
        assert panel._selected_primary_alignment_ref() != panel._selected_secondary_alignment_ref()

        panel._apply_existing_alignment_intersection()

        assert len(messages) == 1
        assert "Control Regions: 2" in messages[0]
        assert "Control Region:" in messages[0]
        assert "Drainage:" in messages[0]
        assert "not applied" not in messages[0]
    finally:
        App.closeDocument(doc.Name)
