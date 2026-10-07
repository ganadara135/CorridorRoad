"""Item 5.4: a roundabout approach can carry its own apron width.

The source carried one apron width for the whole roundabout. A per-approach row is an edge
policy row of the roundabout intent with the rule `roundabout_approach_apron_width`, keyed by
`leg_ref` and by `side` ("start", "end" or "both"). It reaches the approach leg row, and the
outer ownership loop follows it, smoothly between approaches. Without such a row nothing
changes: the loop is the circle it has always been.
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
    update_v1_intersection_model_object,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
    _roundabout_circle_points,
)

ROUNDABOUT = "Roundabout - Single Lane"


def _model(doc):
    create_intersection_preset_sources(doc, preset_label=ROUNDABOUT)
    return to_intersection_model(find_v1_intersection_model(doc))


def _default_apron(model):
    return next(
        float(row.offset_value)
        for row in model.edge_policy_rows
        if row.offset_rule == "roundabout_outer_apron_width"
    )


def _outer_radius(model):
    return next(
        float(row.offset_value)
        for row in model.edge_policy_rows
        if row.offset_rule == "roundabout_circulatory_outer_radius"
    )


def _approach_row(model, leg_ref, value, *, side="both", policy_id=""):
    return IntersectionEdgePolicyRow(
        policy_id=policy_id or f"roundabout-policy:test:approach-apron:{leg_ref}:{side}",
        intersection_id=model.intersection_rows[0].intersection_id,
        leg_ref=leg_ref,
        edge_role="outer_apron_edge",
        side=side,
        offset_rule="roundabout_approach_apron_width",
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


def _ownership_loop(loops):
    return next(row for row in loops.loop_rows if row.loop_role == "roundabout_outer_ownership_boundary")


def _radius_at(loop_points, center, angle_deg):
    best = min(
        loop_points[:-1],
        key=lambda p: abs(((math.degrees(math.atan2(p[1] - center[1], p[0] - center[0])) - angle_deg + 180.0) % 360.0) - 180.0),
    )
    return math.hypot(best[0] - center[0], best[1] - center[1])


def test_without_per_approach_rows_every_approach_uses_the_default_and_the_loop_is_the_circle() -> None:
    doc = App.newDocument("CRV1RoundaboutApronDefault")
    try:
        model = _model(doc)
        legs, loops = _evaluate(model)
        assert len(legs.approach_leg_rows) == 4
        assert {row.apron_width_source for row in legs.approach_leg_rows} == {"roundabout_default"}
        assert {row.apron_width for row in legs.approach_leg_rows} == {_default_apron(model)}

        ownership = _ownership_loop(loops)
        center = legs.approach_leg_rows[0].roundabout_center_xyz
        expected = _roundabout_circle_points(center, _outer_radius(model) + _default_apron(model), segment_count=32)
        assert list(ownership.loop_points_xyz[:-1]) == expected
    finally:
        App.closeDocument(doc.Name)


def test_a_leg_row_widens_that_legs_two_approaches_and_the_loop_follows_smoothly() -> None:
    doc = App.newDocument("CRV1RoundaboutApronLeg")
    try:
        model = _model(doc)
        default = _default_apron(model)
        outer = _outer_radius(model)
        legs, _loops = _evaluate(model)
        target_leg = legs.approach_leg_rows[0].source_leg_ref
        wide = default * 4.0

        widened = replace(model, edge_policy_rows=[*model.edge_policy_rows, _approach_row(model, target_leg, wide)])
        legs, loops = _evaluate(widened)
        by_source = {}
        for row in legs.approach_leg_rows:
            by_source.setdefault(row.apron_width_source, []).append(row)
        assert sorted(row.source_leg_ref for row in by_source["approach_policy"]) == [target_leg, target_leg]
        assert {row.apron_width for row in by_source["approach_policy"]} == {wide}
        assert {row.apron_width for row in by_source["roundabout_default"]} == {default}

        ownership = _ownership_loop(loops)
        assert ownership.status == "ready" and ownership.closed
        points = ownership.loop_points_xyz
        center = legs.approach_leg_rows[0].roundabout_center_xyz
        for row in legs.approach_leg_rows:
            expected = outer + (wide if row.apron_width_source == "approach_policy" else default)
            assert abs(_radius_at(points, center, row.direction_angle_deg) - expected) < 0.2, row.approach_role
        radii = [math.hypot(p[0] - center[0], p[1] - center[1]) for p in points[:-1]]
        assert min(radii) >= outer + default - 1.0e-9
        assert max(radii) <= outer + wide + 1.0e-9
        # it never steps: neighbouring samples differ by less than the whole widening
        assert max(abs(a - b) for a, b in zip(radii, radii[1:] + radii[:1])) < (wide - default)

        # the apron builder pairs the circulatory outer loop and this loop point by point, so
        # the two must share their angles for the ring between them to stay a ring
        inner = next(row for row in loops.loop_rows if row.loop_role == "roundabout_circulatory_outer_boundary")
        for first, second in zip(inner.loop_points_xyz[:-1], points[:-1]):
            angle_first = math.atan2(first[1] - center[1], first[0] - center[0])
            angle_second = math.atan2(second[1] - center[1], second[0] - center[0])
            assert abs(math.remainder(angle_first - angle_second, 2.0 * math.pi)) < 1.0e-9
        assert ownership.area_xy > inner.area_xy
    finally:
        App.closeDocument(doc.Name)


def test_an_endpoint_row_beats_a_both_row_and_a_bad_value_falls_back_with_a_warning() -> None:
    doc = App.newDocument("CRV1RoundaboutApronEndpoint")
    try:
        model = _model(doc)
        default = _default_apron(model)
        legs, _loops = _evaluate(model)
        leg = legs.approach_leg_rows[0].source_leg_ref

        rows = [
            _approach_row(model, leg, default * 2.0, side="both"),
            _approach_row(model, leg, default * 3.0, side="start"),
        ]
        legs, _loops = _evaluate(replace(model, edge_policy_rows=[*model.edge_policy_rows, *rows]))
        widths = {row.approach_role.rsplit("_", 1)[-1]: row.apron_width for row in legs.approach_leg_rows if row.source_leg_ref == leg}
        assert widths == {"start": default * 3.0, "end": default * 2.0}

        legs, _loops = _evaluate(
            replace(model, edge_policy_rows=[*model.edge_policy_rows, _approach_row(model, leg, -1.0)])
        )
        fallen_back = [row for row in legs.approach_leg_rows if row.source_leg_ref == leg]
        assert {row.apron_width for row in fallen_back} == {default}
        assert {row.apron_width_source for row in fallen_back} == {"roundabout_default"}
        assert any("roundabout_approach_apron_width_invalid" in text for text in legs.diagnostic_rows)
        assert all(row.source_status == "warning" for row in fallen_back)
    finally:
        App.closeDocument(doc.Name)


def test_the_per_approach_row_survives_the_document_round_trip() -> None:
    doc = App.newDocument("CRV1RoundaboutApronPersist")
    try:
        model = _model(doc)
        legs, _loops = _evaluate(model)
        leg = legs.approach_leg_rows[0].source_leg_ref
        row = _approach_row(model, leg, 5.0, side="end", policy_id="roundabout-policy:test:approach-apron:persist")
        update_v1_intersection_model_object(
            find_v1_intersection_model(doc),
            replace(model, edge_policy_rows=[*model.edge_policy_rows, row]),
            label="Intersections",
        )
        stored = to_intersection_model(find_v1_intersection_model(doc))
        kept = next(item for item in stored.edge_policy_rows if item.policy_id == row.policy_id)
        assert (kept.leg_ref, kept.side, kept.offset_rule, kept.offset_value) == (leg, "end", "roundabout_approach_apron_width", 5.0)
    finally:
        App.closeDocument(doc.Name)
