"""GR-3: result freshness and Rebuild Downstream.

Stations, 3D Centerline, Applied Sections and Build Parametric record the content fingerprint of each input they
consumed. A freshness check compares the record with the inputs now, and Rebuild Downstream
rebuilds the stale stages in workflow order with their recorded options.
"""

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import apply_alignment_ip_rows
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import apply_v1_corridor_model
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_rebuild_downstream import (
    document_has_stale_results,
    rebuild_downstream,
)
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.commands.cmd_view_sections import _build_v1_applied_section_set_preview
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set
from freecad.Corridor_Road.v1.objects.obj_corridor import find_v1_corridor_model
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile, find_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing, find_v1_stationing
from freecad.Corridor_Road.v1.objects.result_freshness import document_result_freshness
from freecad.Corridor_Road.v1.objects.stage_inputs import read_stage_inputs, read_stage_options
from freecad.Corridor_Road.v1.services.evaluation.result_freshness_service import (
    APPLIED_SECTIONS,
    NOT_RECORDED,
    StageFreshness,
    changed_input_keys,
    freshness_text,
    stage_freshness,
)

APPLIED_OPTIONS = {"supplemental_sections_enabled": False}


def _built_doc(name: str):
    doc = App.newDocument(name)
    project = create_corridorroad_project(doc)
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=20.0)
    show_v1_centerline3d_preview_object(doc, project=project, display_mode="polyline")
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    apply_v1_region_model(
        document=doc,
        project=project,
        region_model=region_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    applied = build_document_applied_section_set(doc, project=project, **APPLIED_OPTIONS)
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied, build_options=APPLIED_OPTIONS)
    apply_v1_corridor_model(document=doc, project=project)
    return doc, alignment


def _status(doc) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {row.stage: (row.status, row.changed_inputs) for row in document_result_freshness(doc)}


def _raise_profile(doc) -> None:
    profile = find_v1_profile(doc)
    elevations = list(profile.ControlElevations)
    elevations[1] += 1.5
    profile.ControlElevations = elevations


def _records(doc) -> list[object]:
    objects = (
        find_v1_stationing(doc),
        doc.getObject("V1Centerline3DPreview"),
        find_v1_applied_section_set(doc),
        find_v1_corridor_model(doc),
    )
    return [list(getattr(obj, "StageInputRows", [])) for obj in objects]


def test_the_freshness_rules() -> None:
    assert changed_input_keys({"a": "1", "b": "2"}, {"a": "1", "b": "3", "c": "4"}) == ("b", "c")
    assert changed_input_keys(None, {"a": "1"}) == (NOT_RECORDED,)
    upstream = StageFreshness("stationing", "stale", ("S",), ("alignment@a",))
    row = stage_freshness(APPLIED_SECTIONS, object_names=("A",), recorded={"x": "1"}, current={"x": "1"}, upstream=upstream)
    assert (row.status, row.changed_inputs) == ("stale", ("alignment@a",))
    assert stage_freshness(APPLIED_SECTIONS, object_names=(), recorded=None, current={}).status == "missing"
    assert "Run Rebuild Downstream" in freshness_text([row])


def test_a_full_build_is_current_and_records_its_options() -> None:
    doc, _alignment = _built_doc("CRV1FreshnessBuilt")
    try:
        assert {stage: value[0] for stage, value in _status(doc).items()} == {
            "stationing": "current",
            "centerline3d": "current",
            "applied_sections": "current",
            # the document has no Drainage source, so there is nothing to evaluate
            "drainage": "missing",
            "build_parametric": "current",
        }
        assert read_stage_options(find_v1_applied_section_set(doc)) == APPLIED_OPTIONS
        assert read_stage_options(find_v1_stationing(doc)) == {"interval": 20.0}
        assert read_stage_options(doc.getObject("V1Centerline3DPreview"))["display_mode"] == "polyline"
        assert read_stage_options(find_v1_corridor_model(doc))["build_surfaces"] is True
        assert document_has_stale_results(doc) is False
    finally:
        App.closeDocument(doc.Name)


def test_a_profile_edit_makes_applied_sections_and_corridor_stale_and_rebuild_makes_them_current() -> None:
    doc, alignment = _built_doc("CRV1FreshnessProfile")
    try:
        stationing = find_v1_stationing(doc)
        stationing_record = list(stationing.StageInputRows)
        centerline = doc.getObject("V1Centerline3DPreview")
        z_max_before = centerline.Shape.BoundBox.ZMax
        _raise_profile(doc)
        profile_key = f"profile@{alignment.AlignmentId}"

        status = _status(doc)
        assert status["stationing"] == ("current", ())
        assert status["centerline3d"] == ("stale", (profile_key,))
        assert status["applied_sections"] == ("stale", (profile_key,))
        assert status["build_parametric"] == ("stale", (profile_key,))

        report = rebuild_downstream(doc)

        assert report.rebuilt_stages == ("centerline3d", "applied_sections", "build_parametric")
        # the 3D Centerline follows the raised profile, with its recorded display options
        assert centerline.Shape.BoundBox.ZMax != z_max_before
        assert read_stage_options(centerline)["display_mode"] == "polyline"
        assert {stage: value[0] for stage, value in _status(doc).items() if stage != "drainage"} == dict.fromkeys(
            ("stationing", "centerline3d", "applied_sections", "build_parametric"), "current"
        )
        assert list(stationing.StageInputRows) == stationing_record
        # the recorded options were reused
        assert read_stage_options(find_v1_applied_section_set(doc)) == APPLIED_OPTIONS
        assert rebuild_downstream(doc).rebuilt_stages == ()
    finally:
        App.closeDocument(doc.Name)


def test_the_applied_sections_scope_does_not_rebuild_the_corridor() -> None:
    doc, _alignment = _built_doc("CRV1FreshnessScope")
    try:
        _raise_profile(doc)

        report = rebuild_downstream(doc, through=APPLIED_SECTIONS)

        assert report.rebuilt_stages == ("centerline3d", "applied_sections")
        status = _status(doc)
        assert status["applied_sections"][0] == "current"
        assert status["build_parametric"] == ("stale", ("applied_sections",))
    finally:
        App.closeDocument(doc.Name)


def test_an_alignment_edit_resamples_the_stations_first() -> None:
    doc, alignment = _built_doc("CRV1FreshnessAlignment")
    try:
        apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 90.0, "y": 0.0, "radius": 60.0, "transition_length": 0.0},
                {"x": 170.0, "y": 30.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=False,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )
        alignment_key = f"alignment@{alignment.AlignmentId}"
        assert _status(doc)["stationing"] == ("stale", (alignment_key,))

        report = rebuild_downstream(doc)

        assert report.rebuilt_stages == ("stationing", "centerline3d", "applied_sections", "build_parametric")
        assert {stage: value[0] for stage, value in _status(doc).items() if stage != "drainage"} == dict.fromkeys(
            ("stationing", "centerline3d", "applied_sections", "build_parametric"), "current"
        )
    finally:
        App.closeDocument(doc.Name)


def test_a_failing_stage_stops_the_run() -> None:
    doc, alignment = _built_doc("CRV1FreshnessFailure")
    try:
        doc.removeObject(alignment.Name)

        report = rebuild_downstream(doc)

        assert report.failed
        assert [(row.stage, row.outcome) for row in report.outcomes] == [("stationing", "failed")]
        assert "no longer exists" in report.outcomes[0].message
    finally:
        App.closeDocument(doc.Name)


def test_reading_freshness_and_opening_the_section_viewer_change_nothing() -> None:
    doc, _alignment = _built_doc("CRV1FreshnessReadOnly")
    try:
        _raise_profile(doc)
        before = _records(doc)
        applied_fingerprint = str(find_v1_applied_section_set(doc).SourceFingerprint)

        document_result_freshness(doc)
        preview = _build_v1_applied_section_set_preview(doc)

        assert preview["result_state"]["state"] == "stale"
        assert "Run Rebuild Downstream" in preview["result_state"]["reason"]
        assert _records(doc) == before
        assert str(find_v1_applied_section_set(doc).SourceFingerprint) == applied_fingerprint
    finally:
        App.closeDocument(doc.Name)


def test_a_result_built_before_inputs_were_recorded_is_stale() -> None:
    doc, _alignment = _built_doc("CRV1FreshnessUnrecorded")
    try:
        applied = find_v1_applied_section_set(doc)
        applied.removeProperty("StageInputRows")

        assert read_stage_inputs(applied) is None
        assert _status(doc)["applied_sections"] == ("stale", (NOT_RECORDED,))
    finally:
        App.closeDocument(doc.Name)
