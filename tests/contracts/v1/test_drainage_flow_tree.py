"""The Drainage flow tree and its text (DR-6a): the Points and Links seen as a forest."""

from freecad.Corridor_Road.v1.models.result.drainage_result import DrainageCheck, DrainageLinkRow
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageLink, DrainagePoint
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import (
    build_flow_tree,
    flow_node_severity,
    walk_flow_nodes,
)
from freecad.Corridor_Road.v1.ui.presentation.drainage_flow_tree_presentation import (
    flow_group_title,
    flow_node_text,
    flow_tree_note,
)

RUN = "ditch-run:ditch:left"


def _point(point_id: str, kind: str, station: float, *, run: str = RUN, road: str = "alignment:main") -> DrainagePoint:
    return DrainagePoint(point_id, kind, station, side="left", ditch_run_ref=run, alignment_ref=road)


def _check(kind: str, ref: str, severity: str = "warning", *, run: str = RUN, station: float = 0.0) -> DrainageCheck:
    return DrainageCheck(f"{kind}:{ref}" if ref else kind, kind, severity, run, station, station, f"{kind} {ref}")


def _chain():
    points = [
        _point("inlet:2", "inlet", 80.0),
        _point("outfall:1", "outfall", 40.0),
        _point("inlet:1", "inlet", 60.0),
        _point("inlet:3", "inlet", 20.0),
    ]
    links = [
        DrainageLink("link:1", "inlet:1", "outfall:1"),
        DrainageLink("link:2", "inlet:2", "inlet:1"),
        DrainageLink("link:3", "inlet:3", "outfall:1"),
    ]
    return points, links


def test_each_point_sits_under_the_point_it_drains_into_in_station_order() -> None:
    tree = build_flow_tree(*_chain())

    (root,) = tree.roots
    assert root.point_id == "outfall:1" and root.drains_to == ""
    assert [child.point_id for child in root.children] == ["inlet:3", "inlet:1"]
    assert [child.point_id for child in root.children[1].children] == ["inlet:2"]
    assert root.children[1].children[0].drains_to == "inlet:1"
    assert root.children[1].children[0].link_ref == "link:2"
    assert tree.loop_nodes == ()
    assert tree.node_count == 4
    assert [node.point_id for node in walk_flow_nodes(tree.roots)] == ["outfall:1", "inlet:3", "inlet:1", "inlet:2"]


def test_a_point_that_drains_nowhere_is_a_root_and_outfalls_come_first() -> None:
    points = [_point("inlet:1", "inlet", 10.0), _point("outfall:1", "outfall", 90.0), _point("culvert:1", "culvert", 50.0, run="")]

    tree = build_flow_tree(points, [])

    assert [node.point_id for node in tree.roots] == ["outfall:1", "culvert:1", "inlet:1"]


def test_roads_keep_their_points_together() -> None:
    points = [
        _point("outfall:2", "outfall", 10.0, road="alignment:b"),
        _point("outfall:1", "outfall", 90.0, road="alignment:a"),
    ]

    tree = build_flow_tree(points, [])

    assert [node.alignment_ref for node in tree.roots] == ["alignment:a", "alignment:b"]


def test_a_loop_and_its_feeders_are_listed_apart_and_never_walked() -> None:
    points = [_point("a", "inlet", 10.0), _point("b", "inlet", 20.0), _point("c", "inlet", 30.0), _point("out", "outfall", 90.0)]
    links = [DrainageLink("l1", "a", "b"), DrainageLink("l2", "b", "a"), DrainageLink("l3", "c", "a")]

    tree = build_flow_tree(points, links)

    assert [node.point_id for node in tree.roots] == ["out"]
    assert [node.point_id for node in tree.loop_nodes] == ["a", "b", "c"]
    assert all(node.children == () for node in tree.loop_nodes)
    assert tree.node_count == 4


def test_a_link_to_a_missing_point_or_to_itself_leaves_a_root_that_says_so() -> None:
    points = [_point("inlet:1", "inlet", 10.0), _point("inlet:2", "inlet", 20.0)]
    links = [DrainageLink("l1", "inlet:1", "outfall:9"), DrainageLink("l2", "inlet:2", "inlet:2"), DrainageLink("l3", "ghost", "inlet:1")]

    tree = build_flow_tree(points, links)

    first, second = tree.roots
    assert (first.point_id, first.drains_to, first.drains_to_missing) == ("inlet:1", "outfall:9", True)
    assert second.point_id == "inlet:2" and second.children == ()
    assert "outfall:9, which is not in the Points table" in flow_node_text(first)


def test_a_point_with_two_outgoing_links_follows_the_first() -> None:
    points = [_point("inlet:1", "inlet", 10.0), _point("outfall:1", "outfall", 30.0), _point("outfall:2", "outfall", 50.0)]
    links = [DrainageLink("l1", "inlet:1", "outfall:2"), DrainageLink("l2", "inlet:1", "outfall:1")]

    tree = build_flow_tree(points, links)

    parents = {child.point_id: root.point_id for root in tree.roots for child in root.children}
    assert parents == {"inlet:1": "outfall:2"}
    assert tree.node_count == 3


def test_duplicate_point_ids_make_one_node() -> None:
    tree = build_flow_tree([_point("inlet:1", "inlet", 10.0), _point("inlet:1", "inlet", 20.0)], [])

    assert [(node.point_id, node.station) for node in tree.roots] == [("inlet:1", 10.0)]


def test_checks_sit_beside_the_point_or_the_link_they_name_or_the_nearest_point_of_their_run() -> None:
    points, links = _chain()
    checks = [
        _check("drains_nowhere", "inlet:2"),
        _check("link_uphill", "link:3", "warning"),
        _check("reverse_flow", "inlet:1", "error"),
        _check("inlet_spacing", "", station=75.0),
        _check("low_point_uncollected", "", station=22.0),
        _check("flat_grade", "", station=60.0),
        _check("inlet_spacing", "", run="ditch-run:other", station=60.0),
    ]

    tree = build_flow_tree(points, links, check_rows=checks)

    by_id = {node.point_id: node for node in walk_flow_nodes(tree.roots)}
    assert [row.kind for row in by_id["inlet:2"].check_rows] == ["drains_nowhere", "inlet_spacing"]
    assert [row.kind for row in by_id["inlet:3"].check_rows] == ["link_uphill", "low_point_uncollected"]
    assert [row.kind for row in by_id["inlet:1"].check_rows] == ["reverse_flow"]
    assert by_id["outfall:1"].check_rows == ()
    assert flow_node_severity(by_id["inlet:1"]) == "error"
    assert flow_node_severity(by_id["inlet:2"]) == "warning"
    assert flow_node_severity(by_id["outfall:1"]) == ""


def test_links_carry_their_measured_grade() -> None:
    points, links = _chain()
    measured = [DrainageLinkRow("link:1", "inlet:1", "outfall:1", 20.0, 9.8, 9.7, -0.5)]

    tree = build_flow_tree(points, links, link_rows=measured)

    by_id = {node.point_id: node for node in walk_flow_nodes(tree.roots)}
    assert by_id["inlet:1"].link_grade_percent == -0.5
    assert by_id["inlet:2"].link_grade_percent is None


def test_a_long_chain_does_not_hit_the_recursion_limit() -> None:
    count = 1500
    points = [_point("outfall", "outfall", 0.0)] + [_point(f"inlet:{index}", "inlet", float(index)) for index in range(1, count)]
    links = [DrainageLink(f"link:{index}", f"inlet:{index}", "outfall" if index == 1 else f"inlet:{index - 1}") for index in range(1, count)]

    tree = build_flow_tree(points, links)

    assert tree.node_count == count
    assert sum(1 for _node in walk_flow_nodes(tree.roots)) == count


def test_the_node_text_names_the_pipe_a_link_carries() -> None:
    points = [DrainagePoint("outfall:1", "outfall", 100.0, ditch_run_ref="r"), DrainagePoint("inlet:1", "inlet", 60.0, ditch_run_ref="r")]
    piped = build_flow_tree(points, [DrainageLink("link:1", "inlet:1", "outfall:1", pipe_diameter_m=0.6)]).roots[0].children[0]
    open_flow = build_flow_tree(points, [DrainageLink("link:1", "inlet:1", "outfall:1")]).roots[0].children[0]
    assert flow_node_text(piped).endswith("into outfall:1 via pipe 0.60 m")
    assert "pipe" not in flow_node_text(open_flow)


def test_the_node_text_reads_station_grade_target_and_checks() -> None:
    points, links = _chain()
    measured = [DrainageLinkRow("link:1", "inlet:1", "outfall:1", 20.0, 9.8, 9.7, -0.5)]
    checks = [_check("link_flat", "link:1"), _check("reverse_flow", "inlet:1", "error")]

    tree = build_flow_tree(points, links, check_rows=checks, link_rows=measured)

    by_id = {node.point_id: node for node in walk_flow_nodes(tree.roots)}
    assert flow_node_text(by_id["inlet:1"]) == "inlet:1  STA 60.000  falls 0.50 % into outfall:1  [1 error, 1 warning]"
    assert flow_node_text(by_id["inlet:2"]) == "inlet:2  STA 80.000  drains into inlet:1"
    assert flow_node_text(by_id["outfall:1"]) == "outfall:1  STA 40.000"
    assert flow_node_text(build_flow_tree([_point("inlet:9", "inlet", 5.0)], []).roots[0]) == "inlet:9  STA 5.000  drains nowhere"


def test_a_rising_or_flat_link_is_worded_as_such() -> None:
    points = [_point("a", "inlet", 10.0), _point("b", "inlet", 20.0), _point("out", "outfall", 30.0)]
    links = [DrainageLink("l1", "a", "out"), DrainageLink("l2", "b", "out")]
    measured = [DrainageLinkRow("l1", "a", "out", 10.0, 9.0, 9.1, 1.0), DrainageLinkRow("l2", "b", "out", 10.0, 9.0, 9.0, 0.0)]

    (root,) = build_flow_tree(points, links, link_rows=measured).roots

    assert [flow_node_text(child) for child in root.children] == [
        "a  STA 10.000  rises 1.00 % into out",
        "b  STA 20.000  drains flat into out",
    ]


def test_the_titles_and_the_note() -> None:
    assert flow_group_title("alignment:a", 3) == "alignment:a  (3 point(s))"
    assert flow_tree_note(point_count=0, root_count=0, loop_count=0).startswith("No points yet.")
    note = flow_tree_note(point_count=4, root_count=1, loop_count=2, result_note="Stale.")
    assert note == "4 point(s) in 1 flow(s). 2 point(s) drain into a loop.\nStale."
