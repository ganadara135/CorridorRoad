import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    CmdV1IntersectionEditor,
    INTERSECTION_COMMAND_ID,
    INTERSECTION_SOURCE_MODES,
    NEXT_INTERSECTION_WORKFLOW_TEXT,
    alignment_model_by_ref,
    starter_intersection_source_specs,
    list_v1_alignment_choices,
    validate_existing_alignment_selection,
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
    assert model.region_rows[0].region_id == "region:secondary-intersection"


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
