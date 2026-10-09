"""The patch boundary's curb returns are fillets tangent to the real pavement edges.

`IntersectionBoundarySegmentEvaluationService` builds the curb return arcs that the patch, the
intersection exclusion, the curb return slope face strip and the build preview draw. It used to
sweep each arc about the intersection centre from the primary centre line to the secondary one.
Each arc is now the fillet of the curb return radius tangent to the two roads' pavement edges, taken
from the left and right tie-in edges of each road in their own directions, so a rotated intersection
gets rotated fillets. A road without both tie-in edges keeps the earlier arc, with a warning.
"""

import math
from types import SimpleNamespace

from freecad.Corridor_Road.v1.services.evaluation.intersection_boundary_segment_evaluation_service import (
    IntersectionBoundarySegmentEvaluationRequest,
    IntersectionBoundarySegmentEvaluationService,
)

ANGLE = math.radians(30.0)
ORIGIN = (100.0, 200.0)
HALF_WIDTH = 5.0
RADIUS = 10.0
U = (math.cos(ANGLE), math.sin(ANGLE))  # primary road direction
V = (-math.sin(ANGLE), math.cos(ANGLE))  # secondary road direction


def _point(along_u, along_v):
    return (ORIGIN[0] + U[0] * along_u + V[0] * along_v, ORIGIN[1] + U[1] * along_u + V[1] * along_v, 50.0)


def _edges(drop=()):
    # each road's left edge lies a half width to its left, the right edge to its right
    rows = [
        ("primary:left", "primary", "left", _point(-6.0, HALF_WIDTH), _point(6.0, HALF_WIDTH)),
        ("primary:right", "primary", "right", _point(-6.0, -HALF_WIDTH), _point(6.0, -HALF_WIDTH)),
        ("secondary:left", "secondary", "left", _point(-HALF_WIDTH, -6.0), _point(-HALF_WIDTH, 6.0)),
        ("secondary:right", "secondary", "right", _point(HALF_WIDTH, -6.0), _point(HALF_WIDTH, 6.0)),
    ]
    return [
        SimpleNamespace(tie_in_edge_id=edge_id, alignment_ref=ref, side=side, start_xyz=start, end_xyz=end, status="ready", notes="")
        for edge_id, ref, side, start, end in rows
        if edge_id not in drop
    ]


def _evaluate(drop=()):
    model = SimpleNamespace(
        intersection_rows=[
            SimpleNamespace(
                intersection_id="x",
                intersection_kind="cross_intersection",
                primary_alignment_ref="primary",
                secondary_alignment_refs=["secondary"],
                intersection_point_x=ORIGIN[0],
                intersection_point_y=ORIGIN[1],
                intersection_point_z=50.0,
            )
        ],
        curb_return_policy_rows=[SimpleNamespace(intersection_id="x", radius=RADIUS, status="active", policy_id="policy")],
    )
    tie_in = SimpleNamespace(intersection_id="x", project_id="p", edge_rows=_edges(drop))
    return IntersectionBoundarySegmentEvaluationService().evaluate(
        IntersectionBoundarySegmentEvaluationRequest(tie_in_result=tie_in, intersection_model=model)
    )


def _arcs(result):
    return [row for row in result.segment_rows if row.segment_kind == "arc" and row.segment_role == "curb_return"]


def test_a_rotated_cross_gets_fillets_tangent_to_its_rotated_pavement_edges() -> None:
    arcs = _arcs(_evaluate())
    assert len(arcs) == 4
    # the first quadrant is between the primary road ahead and the secondary road ahead
    first = arcs[0]
    centre = _point(HALF_WIDTH + RADIUS, HALF_WIDTH + RADIUS)
    expected_start = _point(HALF_WIDTH + RADIUS, HALF_WIDTH)  # on the primary road's left edge
    expected_end = _point(HALF_WIDTH, HALF_WIDTH + RADIUS)  # on the secondary road's right edge
    assert math.dist(first.start_xyz[:2], expected_start[:2]) < 1.0e-9
    assert math.dist(first.end_xyz[:2], expected_end[:2]) < 1.0e-9
    for point in first.chord_points_xyz:
        assert abs(math.dist(point[:2], centre[:2]) - RADIUS) < 1.0e-9
    assert "arc_kind=fillet" in first.notes
    # the centre the consumers fan towards is still the intersection's, not the fillet's
    assert first.center_xyz[:2] == ORIGIN
    for arc in arcs:
        assert "arc_kind=fillet" in arc.notes
        # every fillet stays outside both roads' pavement: its points are at least a half width
        # from each centre line
        for point in arc.chord_points_xyz:
            dx, dy = point[0] - ORIGIN[0], point[1] - ORIGIN[1]
            assert abs(dx * V[0] + dy * V[1]) >= HALF_WIDTH - 1.0e-9
            assert abs(dx * U[0] + dy * U[1]) >= HALF_WIDTH - 1.0e-9


def test_a_road_without_both_tie_in_edges_keeps_the_arc_about_the_centre_with_a_warning() -> None:
    result = _evaluate(drop=("secondary:right",))
    arcs = _arcs(result)
    assert arcs and all("arc_kind=centre_arc" in arc.notes for arc in arcs)
    assert any("intersection_curb_return_fillet_unavailable" in text for text in result.diagnostic_rows)
