import FreeCAD as App
from types import SimpleNamespace

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    CmdV1IntersectionEditor,
    INTERSECTION_COMMAND_ID,
    INTERSECTION_SOURCE_MODES,
    NEXT_INTERSECTION_WORKFLOW_TEXT,
    alignment_model_by_ref,
    show_intersection_review_overlay,
    starter_intersection_source_specs,
    list_v1_alignment_choices,
    validate_existing_alignment_selection,
    INTERSECTION_REVIEW_MAX_REGION_SPAN,
    _starter_region_model_for_alignment,
    _unique_alignment_id,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment


def test_intersection_command_resources_are_specific() -> None:
    resources = CmdV1IntersectionEditor().GetResources()

    assert resources["MenuText"] == "Intersections"
    assert "intersection" in resources["ToolTip"].lower()
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("intersections.svg")


def test_intersection_command_is_between_regions_and_structures() -> None:
    commands = corridorroad_workflow_command_groups()["assembly_region"]

    assert INTERSECTION_COMMAND_ID in commands
    assert commands.index("CorridorRoad_V1EditRegions") < commands.index(INTERSECTION_COMMAND_ID)
    assert commands.index(INTERSECTION_COMMAND_ID) < commands.index("CorridorRoad_V1EditStructures")


def test_intersection_panel_constants_expose_first_slice_modes() -> None:
    assert INTERSECTION_SOURCE_MODES == ("Use Existing Alignments", "Create Starter Sources")
    assert NEXT_INTERSECTION_WORKFLOW_TEXT.endswith("Build Sections")


def test_intersection_starter_source_specs_cover_first_slice_types() -> None:
    for kind in ("t_intersection", "cross_intersection", "y_intersection"):
        spec = starter_intersection_source_specs(kind)
        alignments = list(spec["alignments"])

        assert spec["kind"] == kind
        assert len(alignments) == 2
        assert {row["role"] for row in alignments} == {"primary", "secondary"}
        assert all(len(row["points"]) >= 2 for row in alignments)


def test_intersection_starter_region_model_omits_zero_length_rows() -> None:
    model = _starter_region_model_for_alignment(
        alignment_id="alignment:intersection-secondary",
        intersection_kind="t_intersection",
        role="secondary",
        length=100.0,
        project_id="project:test",
    )

    assert all(row.station_end > row.station_start for row in model.region_rows)
    assert [row.region_index for row in model.region_rows] == [1, 2]
    assert model.region_rows[0].region_id == "region:secondary-approach"
    assert model.region_rows[0].station_start == 0.0
    assert model.region_rows[0].station_end == 65.0
    assert model.region_rows[1].region_id == "region:secondary-intersection"
    assert model.region_rows[1].station_start == 65.0
    assert model.region_rows[1].station_end == 100.0


def test_intersection_existing_alignment_validation_requires_two_different_refs() -> None:
    assert validate_existing_alignment_selection("", "") == [
        "Primary Alignment is required.",
        "Secondary Alignment is required.",
    ]
    assert validate_existing_alignment_selection("alignment:main", "alignment:main") == [
        "Primary and Secondary Alignment must be different."
    ]
    assert validate_existing_alignment_selection("alignment:main", "alignment:side") == []


def test_intersection_alignment_choices_list_v1_alignments() -> None:
    doc = App.newDocument("CRV1IntersectionAlignmentChoices")
    try:
        main = create_sample_v1_alignment(doc, label="Main Road")
        side = create_sample_v1_alignment(doc, label="Side Road")
        side.AlignmentId = "alignment:side-road"

        choices = list_v1_alignment_choices(doc)

        assert (main.AlignmentId, "Main Road") in choices
        assert ("alignment:side-road", "Side Road") in choices
    finally:
        App.closeDocument(doc.Name)


def test_intersection_alignment_model_by_ref_returns_selected_alignment_model() -> None:
    doc = App.newDocument("CRV1IntersectionAlignmentByRef")
    try:
        alignment = create_sample_v1_alignment(doc, label="Main Road")
        model = alignment_model_by_ref(doc, alignment.AlignmentId)

        assert model is not None
        assert model.alignment_id == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_intersection_review_overlay_includes_curb_return_preview_arcs() -> None:
    doc = App.newDocument("CRV1IntersectionCurbReturnOverlay")
    try:
        primary = create_sample_v1_alignment(doc, label="Primary Road")
        secondary = create_sample_v1_alignment(doc, label="Side Road")
        secondary.AlignmentId = "alignment:side-road"
        detection = SimpleNamespace(x=10.0, y=0.0, primary_station=10.0, secondary_station=10.0)

        obj = show_intersection_review_overlay(
            doc,
            intersection_kind="t_intersection",
            primary_alignment_ref=primary.AlignmentId,
            secondary_alignment_ref=secondary.AlignmentId,
            control_region_choices=[
                {
                    "control_region_ref": "regions:primary/region:primary-intersection",
                    "alignment_ref": primary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 20.0,
                },
                {
                    "control_region_ref": "regions:side/region:side-intersection",
                    "alignment_ref": secondary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 20.0,
                },
            ],
            detection_result=detection,
        )

        assert obj.Name == "V1IntersectionReviewOverlay"
        assert obj.CurbReturnPolicyRef == "curb-return:starter-t_intersection:default"
        assert obj.CurbReturnRadius == "12.000"
        assert int(obj.CurbReturnArcCount) == 2
        assert list(obj.CurbReturnDiagnostics) == []
        assert int(obj.ShapePartCount) >= 2
    finally:
        App.closeDocument(doc.Name)


def test_intersection_review_overlay_clips_long_control_region_highlight() -> None:
    doc = App.newDocument("CRV1IntersectionOverlayClipsLongRegion")
    try:
        primary = create_sample_v1_alignment(doc, label="Primary Road")
        secondary = create_sample_v1_alignment(doc, label="Side Road")
        secondary.AlignmentId = "alignment:side-road"
        detection = SimpleNamespace(x=10.0, y=0.0, primary_station=10.0, secondary_station=10.0)

        obj = show_intersection_review_overlay(
            doc,
            intersection_kind="t_intersection",
            primary_alignment_ref=primary.AlignmentId,
            secondary_alignment_ref=secondary.AlignmentId,
            control_region_choices=[
                {
                    "control_region_ref": "regions:primary/region:primary-intersection",
                    "alignment_ref": primary.AlignmentId,
                    "station_start": 0.0,
                    "station_end": 180.0,
                },
            ],
            detection_result=detection,
        )

        bound_box = obj.Shape.BoundBox
        assert float(bound_box.XLength) <= INTERSECTION_REVIEW_MAX_REGION_SPAN + 7.0
    finally:
        App.closeDocument(doc.Name)


def test_intersection_starter_alignment_ids_are_unique() -> None:
    doc = App.newDocument("CRV1IntersectionUniqueAlignmentId")
    try:
        alignment = create_sample_v1_alignment(doc, label="Intersection Main Road")
        alignment.AlignmentId = "alignment:intersection-primary"

        assert _unique_alignment_id(doc, "alignment:intersection-primary") == "alignment:intersection-primary-2"
        assert _unique_alignment_id(doc, "alignment:intersection-secondary") == "alignment:intersection-secondary"
    finally:
        App.closeDocument(doc.Name)


def test_intersection_command_is_active_only_with_document() -> None:
    command = CmdV1IntersectionEditor()
    doc = App.newDocument("CRV1IntersectionCommand")
    try:
        assert command.IsActive() is True
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] intersection command tests completed.")
