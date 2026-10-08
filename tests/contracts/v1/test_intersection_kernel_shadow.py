"""Shadow mode of the parametric intersection kernel in Build Parametric (plan phases R3 and R4).

The kernel runs on the document's Alignments and Applied Sections beside the current pipeline
and only records how it compares:

- its curb return fillets coincide with the arcs the build draws from the Applied Sections'
  tie-in edges (both use the 5 m pavement edge);
- its envelope differs from the evaluation chain's outer boundary loop by exactly the arm
  policy's error (problem P2, decision D1 of the plan): the loop's sides are 4.5 m from the
  centreline instead of 5.0 m, and its mouths, 4.5 m + R from the anchor, are 0.5 m short too,
  so its mouth corners are 0.5 m off in both directions: 0.5 sqrt(2) = 0.707 m, plus up to the
  11 mm chord sag of the kernel's 5 degree arc sampling, where the two arcs' vertices do not line up.
"""

import math

import FreeCAD as App
import pytest

from freecad.Corridor_Road.v1.commands import cmd_intersection_editor as editor
from freecad.Corridor_Road.v1.services.builders.intersection_kernel_context_service import (
    road_context_from_models,
    spec_from_intersection_model,
)

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    build_document_corridor_model,
    build_document_corridor_surface_model,
    create_corridor_intersection_surface_preview,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)

from test_intersection_policy_family_review import _reviewed_model, _store


def _shadow(doc):
    preview = doc.getObject("V1CorridorIntersectionSurfacePreview")
    assert preview is not None
    rows = list(getattr(preview, "IntersectionKernelShadowRows", []) or [])
    return (
        str(getattr(preview, "IntersectionKernelShadowStatus", "") or ""),
        float(getattr(preview, "IntersectionKernelShadowFilletDeviationM", -1.0)),
        float(getattr(preview, "IntersectionKernelShadowEnvelopeDeviationM", -1.0)),
        rows,
    )


def _build(label):
    doc = App.newDocument("CRV1KernelShadow")
    _store(doc, _reviewed_model(doc, label))
    project = find_project(doc)
    applied = build_document_applied_section_set(doc, project=project)
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
    corridor_model = build_document_corridor_model(doc, project=project)
    surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
    create_corridor_intersection_surface_preview(
        document=doc, project=project, corridor_model=corridor_model, surface_model=surface_model
    )
    return doc


@pytest.fixture
def turned_starters(monkeypatch):
    original = editor.starter_intersection_source_specs
    turn = math.radians(30.0)

    def turned(kind):
        specs = original(kind)
        for spec in specs["alignments"]:
            spec["points"] = [
                (x * math.cos(turn) - y * math.sin(turn), x * math.sin(turn) + y * math.cos(turn)) for x, y in spec["points"]
            ]
        return specs

    monkeypatch.setattr(editor, "starter_intersection_source_specs", turned)


@pytest.mark.parametrize("label", ["T Intersection - Basic", "Cross Intersection - Basic"])
def test_the_kernel_fillets_are_the_build_fillets_and_the_envelope_shows_the_arm_policy_error(label) -> None:
    doc = _build(label)
    try:
        status, fillet, envelope, rows = _shadow(doc)
        assert "kernel_status|ready" in rows, rows
        assert fillet <= 0.05, rows
        # the evaluation chain's loop is 4.5 m from each centreline, the Applied Sections' edge 5.0 m
        assert envelope == pytest.approx(0.5 * math.sqrt(2.0), abs=0.015), rows
        assert status == "differ"
    finally:
        App.closeDocument(doc.Name)


def test_the_shadow_follows_turned_roads(turned_starters) -> None:
    doc = _build("T Intersection - Basic")
    try:
        status, fillet, envelope, rows = _shadow(doc)
        assert "kernel_status|ready" in rows, rows
        assert fillet <= 0.05, rows
        assert envelope == pytest.approx(0.5 * math.sqrt(2.0), abs=0.015), rows
    finally:
        App.closeDocument(doc.Name)


def test_a_roundabout_is_skipped_until_the_kernel_builds_one() -> None:
    doc = _build("Roundabout - Single Lane")
    try:
        preview = doc.getObject("V1CorridorIntersectionSurfacePreview")
        if preview is None:
            pytest.skip("this roundabout build creates no intersection surface preview")
        status, _fillet, _envelope, rows = _shadow(doc)
        assert status == "skipped", rows
    finally:
        App.closeDocument(doc.Name)


def test_the_road_context_takes_the_pavement_width_from_the_applied_sections_only() -> None:
    from freecad.Corridor_Road.v1.objects.obj_alignment import to_alignment_model
    from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
    from freecad.Corridor_Road.v1.objects.obj_intersection import find_v1_intersection_model, to_intersection_model

    doc = _build("T Intersection - Basic")
    try:
        spec = spec_from_intersection_model(to_intersection_model(find_v1_intersection_model(doc)))
        assert spec.kind == "t" and spec.anchor.method == "manual"
        alignments = [model for model in (to_alignment_model(obj) for obj in doc.Objects) if model is not None]
        context = road_context_from_models(alignments, to_applied_section_set(find_v1_applied_section_set(doc)))
        for ref in spec.road_refs:
            low, high = context.station_range(ref)
            assert context.pavement_half_width(ref, (low + high) / 2.0, "left") == pytest.approx(5.0)
            assert context.pavement_half_width(ref, (low + high) / 2.0, "right") == pytest.approx(5.0)
        # without Applied Sections there is no width at all, not a guessed one
        bare = road_context_from_models(alignments, None)
        assert bare.pavement_half_width(spec.road_refs[0], 10.0, "left") is None
    finally:
        App.closeDocument(doc.Name)


def _row(rows, prefix):
    return {
        part.split("=", 1)[0]: part.split("=", 1)[1]
        for part in next(row for row in rows if row.startswith(prefix + "|")).split("|")[1:]
        if "=" in part
    }


@pytest.mark.parametrize(
    "label, current_skinny, current_beyond",
    [
        # measured 2026-10-08: the current patch has 125 of 164 and 160 of 207 triangles skinny, and
        # clips the corridor 14 m + 18 m (T) and 2 x 18 m (Cross) further than the mouths
        ("T Intersection - Basic", 125, {"alignment:intersection-primary": 14.0, "alignment:intersection-secondary": 18.0}),
        ("Cross Intersection - Basic", 160, {"alignment:intersection-primary": 18.0, "alignment:intersection-secondary": 18.0}),
    ],
)
def test_the_shadow_records_the_kernel_surfaces_next_to_the_current_ones(label, current_skinny, current_beyond) -> None:
    doc = _build(label)
    try:
        _status, _fillet, _envelope, rows = _shadow(doc)
        patch = _row(rows, "patch")
        assert patch["kernel_skinny"] == "0" and float(patch["kernel_min_quality"]) > 0.08, patch
        assert int(patch["current_skinny"]) == current_skinny, patch
        slope = _row(rows, "slope")
        assert slope["vertices_without_daylight"] == "0" and int(slope["kernel_triangles"]) > 0, slope
        assert int(slope["arc_vertices"]) > 0
        for ref, beyond in current_beyond.items():
            compare = next(row for row in rows if row.startswith(f"clip_compare|{ref}|"))
            assert compare.endswith(f"current_beyond_kernel_m={beyond:.3f}"), compare
    finally:
        App.closeDocument(doc.Name)
