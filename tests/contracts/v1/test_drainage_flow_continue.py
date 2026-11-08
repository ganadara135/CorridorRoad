"""Add Upstream and Add Downstream: continuing the Drainage network from a selected node."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.result.drainage_result import DitchRunFlowline, FlowlineStation
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageLink, DrainagePoint
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import add_downstream, add_upstream

RUN = "ditch-run:ditch:left"


def _flowline(elevation, *, highs=(), lows=(), end=200.0, step=20.0) -> DitchRunFlowline:
    """A straight run along +x: the section at station s has x = s and the elevation given."""

    stations = []
    station = 0.0
    while station <= end + 1.0e-9:
        stations.append(FlowlineStation(station, station, 0.0, float(elevation(station))))
        station += step
    return DitchRunFlowline(
        RUN, "left", "ditch:left", station_rows=stations, low_point_stations=list(lows), high_point_stations=list(highs)
    )


def _falls_to_end(station: float) -> float:
    return 10.0 - station * 0.05


def _valley(station: float) -> float:
    return abs(station - 100.0) * 0.05


def _hill(station: float) -> float:
    return 10.0 - abs(station - 100.0) * 0.05


def _point(point_id: str, kind: str, station: float, run: str = RUN) -> DrainagePoint:
    return DrainagePoint(point_id, kind, station, ditch_run_ref=run)


def test_add_upstream_walks_up_in_equal_steps_until_the_spacing_holds():
    flowline = _flowline(_falls_to_end)
    points = [_point("outfall:1", "outfall", 200.0)]
    links: list[DrainageLink] = []
    selected = "outfall:1"
    placed = []
    for _press in range(10):
        step = add_upstream(selected, points, links, [flowline], 60.0)
        if not step.added:
            assert "nothing more is needed upstream" in step.message
            break
        points += list(step.points)
        links += list(step.links)
        selected = step.select_point_id
        placed.append(step.points[0].station)
    assert placed == [150.0, 100.0, 50.0]
    # every new inlet drains into the one below it, so the chain ends at the outfall
    assert [(link.from_ref, link.to_ref) for link in links] == [
        ("inlet:1", "outfall:1"),
        ("inlet:2", "inlet:1"),
        ("inlet:3", "inlet:2"),
    ]
    marks = sorted([0.0, *[point.station for point in points]])
    assert max(second - first for first, second in zip(marks, marks[1:])) <= 60.0


def test_add_upstream_takes_the_step_from_the_stretch_to_the_next_point():
    flowline = _flowline(_falls_to_end)
    points = [_point("outfall:1", "outfall", 200.0), _point("inlet:1", "inlet", 60.0)]
    step = add_upstream("outfall:1", points, [], [flowline], 40.0)
    # 140 m between the outfall and the inlet at 60 -> 4 parts of 35 m
    assert step.points[0].station == 165.0


def test_add_upstream_at_a_low_point_goes_to_the_longer_stretch_first_then_the_other():
    flowline = _flowline(_valley, lows=[100.0])
    points = [_point("inlet:1", "inlet", 100.0), _point("inlet:2", "inlet", 160.0)]
    first = add_upstream("inlet:1", points, [], [flowline], 40.0)
    assert first.points[0].station == 66.667  # left: 100 m, the longer; the right has 60 m
    second = add_upstream("inlet:1", points + list(first.points), list(first.links), [flowline], 40.0)
    assert second.points[0].station == 130.0  # the left is now 33.3 m, within the spacing
    assert second.points[0].point_id == "inlet:4"


def test_add_upstream_on_a_tie_goes_toward_the_run_start():
    flowline = _flowline(_valley, lows=[100.0])
    step = add_upstream("inlet:1", [_point("inlet:1", "inlet", 100.0)], [], [flowline], 40.0)
    assert step.points[0].station == 66.667


def test_add_upstream_refuses_at_a_crest_a_culvert_and_an_unknown_point():
    flowline = _flowline(_hill, highs=[100.0])
    crest = add_upstream("inlet:1", [_point("inlet:1", "inlet", 100.0)], [], [flowline], 40.0)
    assert not crest.added and "does not rise" in crest.message
    culvert = add_upstream("culvert:1", [DrainagePoint("culvert:1", "culvert", 100.0)], [], [flowline], 40.0)
    assert not culvert.added and "crosses the road" in culvert.message
    assert "Select a point" in add_upstream("nope", [], [], [flowline], 40.0).message
    assert "no flowline" in add_upstream("inlet:1", [_point("inlet:1", "inlet", 100.0)], [], [], 40.0).message


def test_add_upstream_gives_unique_ids_and_the_runs_road():
    flowline = _flowline(_falls_to_end)
    node = DrainagePoint("outfall:1", "outfall", 200.0, side="left", ditch_run_ref=RUN, alignment_ref="alignment:main")
    points = [node, _point("inlet:1", "inlet", 10.0), _point("inlet:2", "inlet", 12.0)]
    links = [DrainageLink("link:1", "inlet:1", "outfall:1")]
    step = add_upstream("outfall:1", points, links, [flowline], 60.0)
    assert step.points[0].point_id == "inlet:3"
    assert step.links[0].link_id == "link:2"
    assert (step.points[0].side, step.points[0].alignment_ref) == ("left", "alignment:main")


def test_add_downstream_links_to_the_nearest_lower_point_on_its_run():
    flowline = _flowline(_falls_to_end)
    points = [_point("inlet:1", "inlet", 100.0), _point("inlet:2", "inlet", 150.0), _point("outfall:1", "outfall", 200.0)]
    step = add_downstream("inlet:1", points, [], [flowline])
    assert [(link.from_ref, link.to_ref) for link in step.links] == [("inlet:1", "inlet:2")]
    assert step.points == () and step.select_point_id == "inlet:2"


def test_add_downstream_adds_an_outfall_at_the_run_end_the_ditch_falls_toward():
    flowline = _flowline(_falls_to_end)
    points = [_point("inlet:1", "inlet", 100.0)]
    step = add_downstream("inlet:1", points, [], [flowline])
    assert [(point.point_id, point.kind, point.station) for point in step.points] == [("outfall:1", "outfall", 200.0)]
    assert [(link.from_ref, link.to_ref) for link in step.links] == [("inlet:1", "outfall:1")]
    assert step.select_point_id == "outfall:1"


def test_add_downstream_from_a_crest_takes_the_lower_run_end():
    flowline = _flowline(lambda station: 10.0 - abs(station - 100.0) * 0.05 + (0.2 if station < 100.0 else 0.0), highs=[100.0])
    step = add_downstream("inlet:1", [_point("inlet:1", "inlet", 100.0)], [], [flowline])
    assert step.points[0].station == 200.0


def test_add_downstream_refuses_a_drained_node_an_outfall_and_a_ditch_with_a_low_point_first():
    flowline = _flowline(_falls_to_end)
    points = [_point("inlet:1", "inlet", 100.0), _point("outfall:1", "outfall", 200.0)]
    links = [DrainageLink("link:1", "inlet:1", "outfall:1")]
    drained = add_downstream("inlet:1", points, links, [flowline])
    assert not drained.added and "already drains into outfall:1" in drained.message
    outfall = add_downstream("outfall:1", points, links, [flowline])
    assert not outfall.added and "outfall" in outfall.message
    valley = _flowline(_valley, lows=[100.0])
    low = add_downstream("inlet:1", [_point("inlet:1", "inlet", 100.0)], [], [valley])
    assert not low.added and "low point" in low.message
    # falls to a low point at 150 and rises again to the end: the water collects there first
    pocket = _flowline(lambda station: abs(station - 150.0) * 0.05 + 2.0 * (station < 150.0))
    blocked = add_downstream("inlet:1", [_point("inlet:1", "inlet", 50.0)], [], [pocket])
    assert not blocked.added and "low point" in blocked.message


def test_add_downstream_never_makes_a_second_outgoing_link_or_a_loop():
    flowline = _flowline(_falls_to_end)
    points = [_point("inlet:1", "inlet", 100.0), _point("inlet:2", "inlet", 150.0)]
    links: list[DrainageLink] = []
    for _press in range(3):
        for node in ("inlet:1", "inlet:2"):
            step = add_downstream(node, points, links, [flowline])
            points += list(step.points)
            links += list(step.links)
    outgoing = [link.from_ref for link in links]
    assert len(outgoing) == len(set(outgoing)) == 2
    assert {point.point_id for point in points} == {"inlet:1", "inlet:2", "outfall:1"}
