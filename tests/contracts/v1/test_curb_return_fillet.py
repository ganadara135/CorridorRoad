"""Curb return arcs are fillets tangent to the pavement edges, where the arms allow it.

The corner arcs used to be circles of the curb return radius about the intersection centre,
whose end points lay on the arms' centre lines. A Cross now gets, for each of its four corners,
the arc of radius R tangent to the pavement edges of the two arms either side of the corner.
The edge it is tangent to is the one the leg edge rows use (`_intersection_edge_lateral_offset`),
so the boundary loop and the arcs share it. A corner with a through leg, as a T has, and an
arm without a pavement edge policy row keep the earlier arc.
"""

import math
from dataclasses import replace

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)

PAVEMENT_HALF_WIDTH = 4.5  # the starter arm: 2 lanes of 3.5 m and a 1.0 m shoulder, half plus shoulder


def _model(doc, label):
    create_intersection_preset_sources(doc, preset_label=label)
    return to_intersection_model(find_v1_intersection_model(doc))


def _radius(model):
    return float(model.curb_return_policy_rows[0].radius)


def test_each_cross_corner_is_a_fillet_tangent_to_both_pavement_edges() -> None:
    doc = App.newDocument("CRV1FilletCross")
    try:
        model = _model(doc, "Cross Intersection - Basic")
        radius = _radius(model)
        topology = IntersectionEvaluationService().evaluate_topology(model)
        assert len(topology.corner_rows) == 4
        centers = set()
        for corner in topology.corner_rows:
            start, end = corner.start_xyz, corner.end_xyz
            # each end is on a pavement edge line, the other coordinate out at half width + R
            for point in (start, end):
                assert min(abs(point[0]), abs(point[1])) == PAVEMENT_HALF_WIDTH
                assert max(abs(point[0]), abs(point[1])) == PAVEMENT_HALF_WIDTH + radius
            # every arc point is R from one centre, in the corner's quadrant
            sx = 1.0 if (start[0] + end[0]) > 0 else -1.0
            sy = 1.0 if (start[1] + end[1]) > 0 else -1.0
            center = (sx * (PAVEMENT_HALF_WIDTH + radius), sy * (PAVEMENT_HALF_WIDTH + radius))
            centers.add(center)
            for point in corner.arc_points_xyz:
                assert abs(math.hypot(point[0] - center[0], point[1] - center[1]) - radius) < 1.0e-9
            assert corner.arc_points_xyz[0] == start and corner.arc_points_xyz[-1] == end
            # tangent: the radius to each end is perpendicular to its edge line
            assert abs(start[1] - center[1]) == radius or abs(start[0] - center[0]) == radius
            assert abs(end[1] - center[1]) == radius or abs(end[0] - center[0]) == radius
        assert len(centers) == 4
    finally:
        App.closeDocument(doc.Name)


def test_the_cross_boundary_loop_closes_around_the_arm_mouths_with_evenly_cut_connectors() -> None:
    doc = App.newDocument("CRV1FilletCrossLoop")
    try:
        model = _model(doc, "Cross Intersection - Basic")
        service = IntersectionEvaluationService()
        edges = service.evaluate_edge_network(model)
        zones = service.evaluate_surface_zones(model, edges)
        loops = service.evaluate_boundary_loops(model, zones, edges)
        outer = next(row for row in loops.loop_rows if row.loop_role == "outer_intersection_boundary")
        assert outer.status == "ready" and outer.closed
        segments = [row for row in loops.segment_rows if row.loop_ref == outer.loop_id]
        lengths = [
            math.hypot(row.to_xyz[0] - row.from_xyz[0], row.to_xyz[1] - row.from_xyz[1])
            for row in segments
        ]
        # the corners reach out to half width + R, so the loop spans past the arm mouths, not R
        xs = [row.from_xyz[0] for row in segments]
        assert max(xs) == PAVEMENT_HALF_WIDTH + _radius(model)
        # the connectors are cut to the arc spacing, so no edge is several times the average
        assert max(lengths) < 2.5 * (sum(lengths) / len(lengths))
        assert any(row.source_refs and any(ref.endswith(":connector") for ref in row.source_refs) for row in segments)
    finally:
        App.closeDocument(doc.Name)


def test_a_t_keeps_its_earlier_arcs_because_its_primary_leg_is_a_through_leg() -> None:
    doc = App.newDocument("CRV1FilletT")
    try:
        model = _model(doc, "T Intersection - Basic")
        radius = _radius(model)
        topology = IntersectionEvaluationService().evaluate_topology(model)
        starts = sorted(tuple(round(v, 6) for v in corner.start_xyz[:2]) for corner in topology.corner_rows)
        # the arcs about the intersection centre, ends on the centre lines
        assert all(abs(math.hypot(*point) - radius) < 1.0e-6 for point in starts)
    finally:
        App.closeDocument(doc.Name)


def test_an_arm_without_a_pavement_edge_policy_keeps_the_earlier_arc() -> None:
    doc = App.newDocument("CRV1FilletNoEdgePolicy")
    try:
        model = _model(doc, "Cross Intersection - Basic")
        radius = _radius(model)
        without = replace(model, edge_policy_rows=[row for row in model.edge_policy_rows if row.edge_role != "pavement_edge"])
        topology = IntersectionEvaluationService().evaluate_topology(without)
        assert len(topology.corner_rows) == 4
        for corner in topology.corner_rows:
            assert abs(math.hypot(corner.start_xyz[0], corner.start_xyz[1]) - radius) < 1.0e-6
            assert abs(math.hypot(corner.end_xyz[0], corner.end_xyz[1]) - radius) < 1.0e-6
    finally:
        App.closeDocument(doc.Name)
