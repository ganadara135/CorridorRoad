"""The starter T with its roads turned 30 degrees about the intersection.

The patch boundary (the arc the build draws, the exclusion, the curb return slope face strip) is built
from the tie-in edges in the alignments' real directions, so it turns with the roads. The topology,
edge network and boundary loop used a fixed frame whose axes are X and Y: measured on 2026-10-07 the
loop's straight sides stayed on the axes, off the road by exactly the turn, its arcs 9.36 m from the
real fillets at 30 degrees. The anchor now keeps each alignment's direction where they meet, as the
detection finds it, and `_intersection_alignment_axis` uses it, so the loop turns with the roads. An
anchor without directions, as in an older document, keeps the fixed frame.
"""

import math

import FreeCAD as App
import pytest

from freecad.Corridor_Road.v1.commands import cmd_intersection_editor as editor
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    intersection_boundary_segment_evaluation_service as boundary_segments,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)

from test_intersection_policy_family_review import _owner_status, _reviewed_model, _store

TURN = math.radians(30.0)
PRIMARY = (math.cos(TURN), math.sin(TURN))
SECONDARY = (-math.sin(TURN), math.cos(TURN))


@pytest.fixture
def turned_t(monkeypatch):
    original = editor.starter_intersection_source_specs

    def turned(kind):
        specs = original(kind)
        for spec in specs["alignments"]:
            spec["points"] = [
                (x * PRIMARY[0] + y * SECONDARY[0], x * PRIMARY[1] + y * SECONDARY[1]) for x, y in spec["points"]
            ]
        return specs

    monkeypatch.setattr(editor, "starter_intersection_source_specs", turned)
    captured = []
    evaluate = boundary_segments.IntersectionBoundarySegmentEvaluationService.evaluate

    def spy(self, request):
        result = evaluate(self, request)
        captured.append(result)
        return result

    monkeypatch.setattr(boundary_segments.IntersectionBoundarySegmentEvaluationService, "evaluate", spy)
    doc = App.newDocument("CRV1TurnedT")
    try:
        _store(doc, _reviewed_model(doc, "T Intersection - Basic"))
        _owner_status(doc)
        yield to_intersection_model(find_v1_intersection_model(doc)), captured[-1]
    finally:
        App.closeDocument(doc.Name)


def _local(point):
    # into the roads' own frame: u along the primary road, v along the secondary road
    return (point[0] * PRIMARY[0] + point[1] * PRIMARY[1], point[0] * SECONDARY[0] + point[1] * SECONDARY[1])


def test_the_patch_boundary_fillets_turn_with_the_roads(turned_t) -> None:
    _model, boundary = turned_t
    arcs = [row for row in boundary.segment_rows if row.segment_kind == "arc" and row.segment_role == "curb_return"]
    assert len(arcs) == 2 and all("arc_kind=fillet" in row.notes for row in arcs)
    # in the roads' frame each arc starts on the primary road's stem-side edge (v = -5) and ends on
    # one of the stem's edges (u = +-5), as the unturned T's arcs do in X and Y. The edges come from
    # Applied Sections sampled on the turned alignments, a few micrometres off, hence the 1 mm tolerance.
    for row in arcs:
        start, end = _local(row.start_xyz), _local(row.end_xyz)
        assert abs(start[1] + 5.0) < 1.0e-3
        assert abs(abs(end[0]) - 5.0) < 1.0e-3


def test_the_boundary_loop_straight_sides_follow_the_roads(turned_t) -> None:
    model, _boundary = turned_t
    service = IntersectionEvaluationService()
    edges = service.evaluate_edge_network(model)
    zones = service.evaluate_surface_zones(model, edges)
    loops = service.evaluate_boundary_loops(model, zones, edges)
    outer = next(row for row in loops.loop_rows if row.loop_role == "outer_intersection_boundary")
    for row in loops.segment_rows:
        if row.loop_ref != outer.loop_id or not any(ref.endswith((":closure", ":connector")) for ref in row.source_refs):
            continue
        du, dv = (b - a for a, b in zip(_local(row.from_xyz), _local(row.to_xyz)))
        # a straight side runs along one road or across it
        assert min(abs(du), abs(dv)) < 1.0e-3, (row.segment_id, du, dv)


def test_the_anchor_keeps_both_directions_through_the_document_round_trip(turned_t) -> None:
    model, _boundary = turned_t
    anchor = model.anchor_rows[0]
    directions = dict(anchor.alignment_direction_refs)
    assert set(directions) == {anchor.primary_alignment_ref, *anchor.secondary_station_refs}
    # along increasing station: the primary road runs along the turned X, the stem along the turned Y.
    # The directions come from the sampled alignment points, up to a few 1e-6 off (0.0006 degrees).
    assert math.dist(directions[anchor.primary_alignment_ref], PRIMARY) < 1.0e-5
    (secondary_ref,) = anchor.secondary_station_refs
    assert math.dist(directions[secondary_ref], SECONDARY) < 1.0e-5


def test_an_anchor_without_directions_keeps_the_fixed_frame(turned_t) -> None:
    # an older document's anchor has no directions: the loop is the axis-aligned one it always was
    from dataclasses import replace

    model, _boundary = turned_t
    older = replace(model, anchor_rows=[replace(row, alignment_direction_refs={}) for row in model.anchor_rows])
    service = IntersectionEvaluationService()
    edges = service.evaluate_edge_network(older)
    zones = service.evaluate_surface_zones(older, edges)
    loops = service.evaluate_boundary_loops(older, zones, edges)
    outer = next(row for row in loops.loop_rows if row.loop_role == "outer_intersection_boundary")
    for row in loops.segment_rows:
        if row.loop_ref != outer.loop_id or not any(ref.endswith((":closure", ":connector")) for ref in row.source_refs):
            continue
        dx, dy = row.to_xyz[0] - row.from_xyz[0], row.to_xyz[1] - row.from_xyz[1]
        assert min(abs(dx), abs(dy)) < 1.0e-6
