"""Trace Network: proposing the missing outfalls, inlets and links of the whole Drainage network."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageLink
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import build_flow_tree, trace_network, walk_flow_nodes
from freecad.Corridor_Road.v1.ui.presentation.drainage_flow_tree_presentation import flow_node_text

from test_drainage_flow_continue import RUN, _falls_to_end, _flowline, _point, _valley


def _trace(points, links, flowlines, *, rule="require_inlet", spacing=60.0):
    return trace_network(points, links, flowlines, low_point_rule=rule, max_inlet_spacing_m=spacing)


def test_trace_builds_the_whole_network_of_a_ditch_that_falls_to_its_end():
    proposal = _trace([], [], [_flowline(_falls_to_end)])
    assert [(point.point_id, point.kind, point.station) for point in proposal.points] == [
        ("inlet:1", "inlet", 50.0),
        ("inlet:2", "inlet", 100.0),
        ("inlet:3", "inlet", 150.0),
        ("outfall:1", "outfall", 200.0),
    ]
    # each inlet drains into the nearest lower point; the chain ends at the outfall
    assert sorted((link.from_ref, link.to_ref) for link in proposal.links) == [
        ("inlet:1", "inlet:2"),
        ("inlet:2", "inlet:3"),
        ("inlet:3", "outfall:1"),
    ]
    assert proposal.undrained == () and proposal.found
    assert "Proposed 4 point(s) and 3 link(s)" in proposal.message


def test_a_second_trace_proposes_nothing_and_a_hand_edited_network_only_gets_its_gaps_filled():
    flowline = _flowline(_falls_to_end)
    first = _trace([], [], [flowline])
    again = _trace(list(first.points), list(first.links), [flowline])
    assert not again.found and again.message.startswith("Nothing to add")

    # a hand-placed outfall and an inlet near the top, drained by hand to the outfall
    points = [_point("outfall:1", "outfall", 200.0), _point("inlet:1", "inlet", 30.0)]
    links = [DrainageLink("link:1", "inlet:1", "outfall:1")]
    partial = _trace(points, links, [flowline])
    assert {point.point_id for point in partial.points}.isdisjoint({"outfall:1", "inlet:1"})
    assert {link.link_id for link in partial.links}.isdisjoint({"link:1"})
    assert all(link.from_ref != "inlet:1" for link in partial.links), "an existing link is never replaced"
    accepted = _trace(points + list(partial.points), links + list(partial.links), [flowline])
    assert not accepted.found


def test_trace_leaves_the_inlet_at_a_low_point_that_has_nowhere_lower_to_drain():
    proposal = _trace([], [], [_flowline(_valley, lows=[100.0])])
    assert [(point.point_id, point.kind, point.station) for point in proposal.points] == [
        ("inlet:1", "inlet", 50.0),
        ("inlet:2", "inlet", 100.0),
        ("inlet:3", "inlet", 150.0),
    ]
    assert sorted((link.from_ref, link.to_ref) for link in proposal.links) == [("inlet:1", "inlet:2"), ("inlet:3", "inlet:2")]
    assert proposal.undrained == ("inlet:2",)
    assert "low point" in proposal.message


def test_trace_does_not_add_a_collector_where_the_policy_lets_water_pond():
    proposal = _trace([], [], [_flowline(_valley, lows=[100.0])], rule="allow_ponding", spacing=1000.0)
    assert not proposal.found


def test_trace_adds_nothing_without_flowlines():
    assert not _trace([_point("inlet:1", "inlet", 10.0)], [], []).found


def test_proposed_rows_are_marked_pending_in_the_tree_and_its_text():
    points = [_point("outfall:1", "outfall", 200.0), _point("inlet:1", "inlet", 100.0), _point("inlet:2", "inlet", 50.0)]
    links = [DrainageLink("link:1", "inlet:1", "outfall:1"), DrainageLink("link:2", "inlet:2", "inlet:1")]
    tree = build_flow_tree(points, links, pending_point_ids=frozenset({"inlet:1"}), pending_link_ids=frozenset({"link:1", "link:2"}))
    nodes = {node.point_id: node for node in walk_flow_nodes(tree.roots)}
    assert (nodes["outfall:1"].pending, nodes["inlet:1"].pending, nodes["inlet:2"].pending) == ("", "point", "link")
    assert flow_node_text(nodes["inlet:1"]).startswith("+  inlet:1") and flow_node_text(nodes["inlet:1"]).endswith("(proposed)")
    assert flow_node_text(nodes["inlet:2"]).endswith("(proposed link)")
    assert "proposed" not in flow_node_text(nodes["outfall:1"])
    assert RUN in {node.ditch_run_ref for node in nodes.values()}
