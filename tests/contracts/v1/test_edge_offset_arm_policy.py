"""The pavement edge rule `lane_width_from_arm_policy` reads the arm policy.

It used to carry the name and fall back to a constant 4.5 m. The offset is now half the lane
count times the lane width, plus the shoulder, plus half the median. The starter arm (2 lanes of
3.5 m, 1.0 m shoulder, no median) gives 4.5 m, so the starter documents do not move. An explicit
`offset_value` still wins, and an arm without a usable width keeps the default with a diagnostic.
"""

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
    _intersection_arm_pavement_half_width,
)

CROSS = "Cross Intersection - Basic"


def _model(doc):
    create_intersection_preset_sources(doc, preset_label=CROSS)
    return to_intersection_model(find_v1_intersection_model(doc))


def _pavement_edge_lines(model):
    edges = IntersectionEvaluationService().evaluate_edge_network(model)
    return edges, {
        row.leg_ref: (row.start_xyz[:2], row.end_xyz[:2])
        for row in edges.edge_rows
        if row.edge_role == "pavement_edge" and row.edge_family == "leg_edge"
    }


def test_the_width_is_half_the_lanes_plus_the_shoulder_plus_half_the_median() -> None:
    doc = App.newDocument("CRV1EdgeOffsetFormula")
    try:
        arm = _model(doc).arm_policy_rows[0]
        assert (arm.lane_count, arm.lane_width, arm.shoulder_width, arm.median_width) == (2, 3.5, 1.0, 0.0)
        assert _intersection_arm_pavement_half_width(arm) == 4.5
        assert _intersection_arm_pavement_half_width(replace(arm, lane_count=4, median_width=2.0)) == 4 * 3.5 / 2 + 1.0 + 1.0
        assert _intersection_arm_pavement_half_width(replace(arm, lane_count=0)) == 0.0
        assert _intersection_arm_pavement_half_width(None) == 0.0
    finally:
        App.closeDocument(doc.Name)


def test_the_starter_edges_do_not_move_and_a_changed_arm_moves_only_its_own_edge() -> None:
    doc = App.newDocument("CRV1EdgeOffsetArm")
    try:
        model = _model(doc)
        _edges, starter = _pavement_edge_lines(model)
        assert {round(abs(value), 6) for start, end in starter.values() for value in (*start, *end)} == {4.5, 24.0}

        widened_leg = model.arm_policy_rows[0].leg_ref
        arms = [replace(row, lane_count=4) if row.leg_ref == widened_leg else row for row in model.arm_policy_rows]
        _edges, widened = _pavement_edge_lines(replace(model, arm_policy_rows=arms))
        assert widened[widened_leg] != starter[widened_leg]
        # 4 lanes of 3.5 m is 7.0 m from the centre line, plus the 1.0 m shoulder
        assert {abs(value) for value in widened[widened_leg][0]} == {8.0, 24.0}
        for leg_ref, line in starter.items():
            if leg_ref != widened_leg:
                assert widened[leg_ref] == line
    finally:
        App.closeDocument(doc.Name)


def test_an_explicit_offset_wins_and_an_arm_without_a_width_keeps_the_default_with_a_note() -> None:
    doc = App.newDocument("CRV1EdgeOffsetFallback")
    try:
        model = _model(doc)
        leg = model.arm_policy_rows[0].leg_ref

        explicit_rows = [
            replace(row, offset_value=6.0) if row.leg_ref == leg and row.edge_role == "pavement_edge" else row
            for row in model.edge_policy_rows
        ]
        _edges, lines = _pavement_edge_lines(replace(model, edge_policy_rows=explicit_rows))
        assert {abs(value) for value in lines[leg][0]} == {6.0, 24.0}

        no_width = [replace(row, lane_count=0) if row.leg_ref == leg else row for row in model.arm_policy_rows]
        edges, lines = _pavement_edge_lines(replace(model, arm_policy_rows=no_width))
        assert {abs(value) for value in lines[leg][0]} == {4.5, 24.0}
        assert any("edge_network_arm_policy_width_missing_default_offset_used" in text for text in edges.diagnostic_rows)
    finally:
        App.closeDocument(doc.Name)


def test_the_curb_return_fillet_follows_the_arm_policy_through_the_edge_offset() -> None:
    doc = App.newDocument("CRV1EdgeOffsetFillet")
    try:
        model = _model(doc)
        arms = [replace(row, shoulder_width=2.0) for row in model.arm_policy_rows]  # 5.5 m on every arm
        topology = IntersectionEvaluationService().evaluate_topology(replace(model, arm_policy_rows=arms))
        radius = float(model.curb_return_policy_rows[0].radius)
        for corner in topology.corner_rows:
            for point in (corner.start_xyz, corner.end_xyz):
                assert min(abs(point[0]), abs(point[1])) == 5.5
                assert max(abs(point[0]), abs(point[1])) == 5.5 + radius
    finally:
        App.closeDocument(doc.Name)
