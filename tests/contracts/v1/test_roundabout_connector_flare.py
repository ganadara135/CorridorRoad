"""Item 5.4, second part: a roundabout approach can flare its connector mouth.

An approach takes an entry radius and an exit radius from edge policy rows of the roundabout
intent, with the rules `roundabout_approach_entry_radius` and `roundabout_approach_exit_radius`,
keyed by `leg_ref` and `side` like the per-approach apron. The flare is the arc tangent to the
connector's edge line and to the circulatory outer circle. For right-hand traffic circulating
counter-clockwise the entry side is the side `p` points to, `p` being the outward direction
turned a quarter turn counter-clockwise. Without a radius the connector is the rectangle it was.
"""

import math
from dataclasses import replace

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import IntersectionEdgePolicyRow
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)

ROUNDABOUT = "Roundabout - Single Lane"


def _model(doc):
    create_intersection_preset_sources(doc, preset_label=ROUNDABOUT)
    return to_intersection_model(find_v1_intersection_model(doc))


def _value(model, rule):
    return next(float(row.offset_value) for row in model.edge_policy_rows if row.offset_rule == rule)


def _flare_row(model, leg_ref, rule, value, *, side="both"):
    return IntersectionEdgePolicyRow(
        policy_id=f"roundabout-policy:test:{rule}:{leg_ref}:{side}",
        intersection_id=model.intersection_rows[0].intersection_id,
        leg_ref=leg_ref,
        edge_role="entry_exit_edge",
        side=side,
        offset_rule=rule,
        offset_value=value,
        edge_family_intent="roundabout",
        source_method="preset_explicit",
        approval_status="accepted",
    )


def _evaluate(model):
    service = IntersectionEvaluationService()
    legs = service.evaluate_roundabout_approach_legs(model)
    edges = service.evaluate_edge_network(model)
    zones = service.evaluate_surface_zones(model, edges)
    loops = service.evaluate_boundary_loops(model, zones, edges)
    return legs, loops


def _connector_loop(loops, approach_leg):
    suffix = approach_leg.approach_role.replace("_", "-")
    return next(
        row
        for row in loops.loop_rows
        if row.loop_role == "roundabout_entry_exit_connector_boundary"
        and approach_leg.approach_leg_id in row.source_refs
    ), suffix


def _local(point, center, angle_deg):
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    dx, dy = point[0] - center[0], point[1] - center[1]
    return (dx * ux + dy * uy, -dx * uy + dy * ux)  # x along the approach, y along p


def test_without_a_radius_every_connector_is_the_four_point_rectangle() -> None:
    doc = App.newDocument("CRV1RoundaboutFlareNone")
    try:
        legs, loops = _evaluate(_model(doc))
        for approach in legs.approach_leg_rows:
            loop, _suffix = _connector_loop(loops, approach)
            assert loop.point_count == 4
            assert approach.entry_radius == 0.0 and approach.exit_radius == 0.0
    finally:
        App.closeDocument(doc.Name)


def test_an_entry_radius_flares_the_entry_side_only_and_is_tangent_to_both_curves() -> None:
    doc = App.newDocument("CRV1RoundaboutFlareEntry")
    try:
        model = _model(doc)
        outer = _value(model, "roundabout_circulatory_outer_radius")
        central = _value(model, "roundabout_central_island_radius")
        half_width = (outer - central) * 0.5
        legs, _loops = _evaluate(model)
        leg = legs.approach_leg_rows[0].source_leg_ref
        radius = 6.0
        flared, loops = _evaluate(
            replace(model, edge_policy_rows=[*model.edge_policy_rows, _flare_row(model, leg, "roundabout_approach_entry_radius", radius)])
        )
        center = flared.approach_leg_rows[0].roundabout_center_xyz
        for approach in flared.approach_leg_rows:
            loop, _suffix = _connector_loop(loops, approach)
            if approach.source_leg_ref != leg:
                assert loop.point_count == 4
                continue
            assert approach.entry_radius == radius and approach.entry_radius_source == "approach_policy"
            assert approach.exit_radius == 0.0
            assert loop.status == "ready" and loop.closed
            local = [_local(point, center, approach.direction_angle_deg) for point in loop.loop_points_xyz[:-1]]
            assert len(local) > 4
            # the exit side keeps its rectangle corner and nothing leaves the connector on that side
            assert min(y for _x, y in local) == -half_width or abs(min(y for _x, y in local) + half_width) < 1.0e-9
            assert max(y for _x, y in local) > half_width + 1.0e-6
            # the flare points are on the entry side, on the circle of radius R round its centre
            arc = [(x, y) for x, y in local if y > half_width + 1.0e-6]
            center_x = math.sqrt((outer + radius) ** 2 - (half_width + radius) ** 2)
            for x, y in arc:
                assert abs(math.hypot(x - center_x, y - (half_width + radius)) - radius) < 1.0e-6
            # the ring end of the flare is on the circulatory outer circle
            ring_end = min(local, key=lambda item: math.hypot(*item) - outer if item[1] > half_width else 1.0e9)
            assert abs(math.hypot(*ring_end) - outer) < 1.0e-6
    finally:
        App.closeDocument(doc.Name)


def test_an_exit_radius_flares_the_other_side_and_a_flare_that_does_not_fit_falls_back() -> None:
    doc = App.newDocument("CRV1RoundaboutFlareExit")
    try:
        model = _model(doc)
        outer = _value(model, "roundabout_circulatory_outer_radius")
        half_width = (outer - _value(model, "roundabout_central_island_radius")) * 0.5
        legs, _loops = _evaluate(model)
        leg = legs.approach_leg_rows[0].source_leg_ref

        flared, loops = _evaluate(
            replace(model, edge_policy_rows=[*model.edge_policy_rows, _flare_row(model, leg, "roundabout_approach_exit_radius", 5.0, side="start")])
        )
        center = flared.approach_leg_rows[0].roundabout_center_xyz
        widened = [row for row in flared.approach_leg_rows if row.exit_radius > 0.0]
        assert [row.approach_role.rsplit("_", 1)[-1] for row in widened] == ["start"]
        loop, _suffix = _connector_loop(loops, widened[0])
        local = [_local(point, center, widened[0].direction_angle_deg) for point in loop.loop_points_xyz[:-1]]
        assert min(y for _x, y in local) < -half_width - 1.0e-6
        assert max(y for _x, y in local) <= half_width + 1.0e-9

        # a flare whose tangent point lies beyond the connector is refused, not drawn
        huge, loops = _evaluate(
            replace(model, edge_policy_rows=[*model.edge_policy_rows, _flare_row(model, leg, "roundabout_approach_entry_radius", 500.0)])
        )
        assert any("roundabout_connector_flare_unavailable" in text for text in loops.diagnostic_rows)
        for approach in huge.approach_leg_rows:
            loop, _suffix = _connector_loop(loops, approach)
            assert loop.point_count == 4
    finally:
        App.closeDocument(doc.Name)
