"""Fix from the flow: the actions a Drainage check offers on its point in the Flow tab."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.result.drainage_result import DrainageCheck
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageLink
from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import edit_for_fix, fixes_for_check, reconnect_targets

from test_drainage_flow_continue import RUN, _falls_to_end, _flowline, _point, _valley


def _check(kind: str, check_id: str, *, start: float = 0.0, end: float = 0.0) -> DrainageCheck:
    return DrainageCheck(check_id, kind, "warning", RUN, start, end, f"{kind} message")


def _edit(action, check, node, points, links, flowlines, **kwargs):
    return edit_for_fix(action, check, node, points, links, flowlines, low_point_rule="require_inlet", max_inlet_spacing_m=60.0, **kwargs)


def test_each_check_kind_offers_its_fixes():
    offered = {
        kind: [fix.action for fix in fixes_for_check(_check(kind, f"{kind}:x"))]
        for kind in (
            "drains_nowhere",
            "low_point_uncollected",
            "inlet_spacing",
            "link_uphill",
            "link_flat",
            "link_loop",
            "drains_twice",
            "reverse_flow",
            "point_off_run",
            "flat_grade",
            "link_unplaced",
        )
    }
    assert offered == {
        "drains_nowhere": ["add_downstream"],
        "low_point_uncollected": ["add_suggested"],
        "inlet_spacing": ["add_suggested"],
        "link_uphill": ["reconnect", "delete_link"],
        "link_flat": ["reconnect", "delete_link"],
        "link_loop": ["delete_link"],
        "drains_twice": ["delete_extra_links"],
        "reverse_flow": ["delete_point"],
        "point_off_run": ["delete_point"],
        "flat_grade": [],
        "link_unplaced": [],
    }


def test_delete_point_removes_the_point_and_every_link_that_touched_it():
    points = [_point("inlet:1", "inlet", 10.0), _point("inlet:2", "inlet", 50.0), _point("outfall:1", "outfall", 200.0)]
    links = [DrainageLink("link:1", "inlet:1", "inlet:2"), DrainageLink("link:2", "inlet:2", "outfall:1"), DrainageLink("link:3", "inlet:1", "outfall:1")]
    edit = _edit("delete_point", _check("reverse_flow", "reverse_flow:inlet:2"), "inlet:2", points, links, [_flowline(_falls_to_end)])
    assert edit.remove_point_ids == ("inlet:2",) and edit.remove_link_ids == ("link:1", "link:2")
    assert "2 link(s)" in edit.message


def test_delete_link_takes_the_link_the_check_names_or_a_loops_first_link():
    points = [_point("inlet:1", "inlet", 10.0), _point("inlet:2", "inlet", 50.0)]
    links = [DrainageLink("link:1", "inlet:1", "inlet:2"), DrainageLink("link:2", "inlet:2", "inlet:1")]
    uphill = _edit("delete_link", _check("link_uphill", "link_uphill:link:1"), "inlet:1", points, links, [_flowline(_falls_to_end)])
    assert uphill.remove_link_ids == ("link:1",)
    loop = _edit("delete_link", _check("link_loop", "link_loop:inlet:2"), "inlet:2", points, links, [_flowline(_falls_to_end)])
    assert loop.remove_link_ids == ("link:2",)
    missing = _edit("delete_link", _check("link_uphill", "link_uphill:link:9"), "inlet:1", points, links, [_flowline(_falls_to_end)])
    assert not missing.changed and "not in the Links table" in missing.message


def test_delete_extra_links_keeps_the_first_link_the_tree_follows():
    points = [_point("inlet:1", "inlet", 10.0), _point("inlet:2", "inlet", 50.0), _point("outfall:1", "outfall", 200.0)]
    links = [DrainageLink("link:1", "inlet:1", "inlet:2"), DrainageLink("link:2", "inlet:1", "outfall:1")]
    edit = _edit("delete_extra_links", _check("drains_twice", "drains_twice:inlet:1"), "inlet:1", points, links, [_flowline(_falls_to_end)])
    assert edit.remove_link_ids == ("link:2",) and "keeps link:1" in edit.message
    single = _edit("delete_extra_links", _check("drains_twice", "drains_twice:inlet:2"), "inlet:2", points, links[:1], [_flowline(_falls_to_end)])
    assert not single.changed


def test_reconnect_offers_only_lower_points_nearest_first_and_refuses_others():
    flowline = _flowline(_falls_to_end)
    points = [
        _point("inlet:1", "inlet", 100.0),
        _point("inlet:2", "inlet", 20.0),  # higher: uphill
        _point("inlet:3", "inlet", 150.0),
        _point("outfall:1", "outfall", 200.0),
    ]
    links = [DrainageLink("link:1", "inlet:1", "inlet:2")]
    assert reconnect_targets("inlet:1", points, [flowline]) == ["inlet:3", "outfall:1"]
    check = _check("link_uphill", "link_uphill:link:1")
    edit = _edit("reconnect", check, "inlet:1", points, links, [flowline], target="outfall:1")
    assert edit.relink == (("link:1", "outfall:1"),) and not edit.remove_link_ids
    refused = _edit("reconnect", check, "inlet:1", points, links, [flowline], target="inlet:2")
    assert not refused.changed and "not a lower point" in refused.message
    assert not _edit("reconnect", check, "inlet:1", points, links, [flowline]).changed


def test_add_suggested_adds_only_the_points_inside_the_checks_stations():
    flowline = _flowline(_valley, lows=[100.0])
    anchor = [_point("inlet:1", "inlet", 100.0)]
    # the low point is collected; the spacing between the ends and it is not
    spacing = _edit("add_suggested", _check("inlet_spacing", "inlet_spacing:r:1", start=0.0, end=100.0), "inlet:1", anchor, [], [flowline])
    assert [point.station for point in spacing.add_points] == [50.0]
    # a low point with nothing near it gets the suggestion at that station only
    low = _edit("add_suggested", _check("low_point_uncollected", "low_point_uncollected:r:1", start=100.0, end=100.0), "inlet:1", [_point("inlet:1", "inlet", 10.0)], [], [flowline])
    assert [(point.kind, point.station) for point in low.add_points] == [("inlet", 100.0)]
    none = _edit("add_suggested", _check("inlet_spacing", "inlet_spacing:r:1", start=0.0, end=10.0), "inlet:1", [_point("inlet:1", "inlet", 10.0)], [], [flowline])
    assert not none.changed and "No suggested point" in none.message


def test_add_downstream_is_a_fix_of_drains_nowhere_and_refuses_an_unknown_point():
    flowline = _flowline(_falls_to_end)
    points = [_point("inlet:1", "inlet", 100.0)]
    edit = _edit("add_downstream", _check("drains_nowhere", "drains_nowhere:inlet:1"), "inlet:1", points, [], [flowline])
    assert [point.kind for point in edit.add_points] == ["outfall"] and len(edit.add_links) == 1
    assert not _edit("add_downstream", _check("drains_nowhere", "drains_nowhere:x"), "nope", points, [], [flowline]).changed
    assert not _edit("explode", _check("drains_nowhere", "drains_nowhere:inlet:1"), "inlet:1", points, [], [flowline]).changed
