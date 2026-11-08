"""Drainage flow tree for the Drainage editor.

Pure Python: the panel passes the points and links of its tables (and, when the stored result is
current, its checks and measured links) and gets back the network as a forest. Nothing here reads
the document, touches FreeCAD or Qt, or writes source: the tree is a view of the Points and Links.

A point drains into at most one point (`drains_twice` otherwise) and a loop is an error
(`link_loop`), so the network is a forest. A root is a point with no outgoing link, or whose link
names a point that is not in the table. A point under a root drains into its parent. Points that
drain into a loop have no root; they are listed apart and never walked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...models.source.drainage_model import DrainageLink, DrainagePoint
from ..evaluation.drainage_evaluation_service import (
    ELEVATION_TOLERANCE_M,
    STATION_ENTRY_TOLERANCE_M,
    STATION_TOLERANCE_M,
    point_places,
    suggest_points,
)
from .drainage_editing_service import next_point_id

CHECK_ERROR = "error"
CHECK_WARNING = "warning"

# Checks that name a station on a run, not a point or a link, and still belong beside the nearest
# point of that run: the stretch they flag is covered or relieved by a point there.
CHECKS_AT_NEAREST_POINT = ("low_point_uncollected", "inlet_spacing")

# Outfalls first: they are where the water leaves, so the tree reads from there upstream.
_KIND_ORDER = {"outfall": 0, "culvert": 1, "inlet": 2}


@dataclass(frozen=True)
class FlowNode:
    """One point, with the points that drain into it."""

    point_id: str
    kind: str
    ditch_run_ref: str
    alignment_ref: str
    station: float
    drains_to: str = ""
    drains_to_missing: bool = False
    link_ref: str = ""
    link_grade_percent: float | None = None
    check_rows: tuple = ()
    children: tuple["FlowNode", ...] = ()
    # "point" for a proposed point, "link" for an existing point whose outgoing link is proposed
    pending: str = ""


@dataclass(frozen=True)
class FlowTree:
    """The network: roots with their upstream points, and the points that drain into a loop."""

    roots: tuple[FlowNode, ...] = ()
    loop_nodes: tuple[FlowNode, ...] = ()

    @property
    def node_count(self) -> int:
        return sum(1 for _node in walk_flow_nodes(self.roots)) + len(self.loop_nodes)


def build_flow_tree(
    points: list[DrainagePoint],
    links: list[DrainageLink],
    *,
    check_rows=(),
    link_rows=(),
    pending_point_ids=frozenset(),
    pending_link_ids=frozenset(),
) -> FlowTree:
    """The flow forest of `points` and `links`.

    `check_rows` are the stored Drainage result's checks and `link_rows` its measured links; pass
    them only while that result is current, since a stale one may name stations that no longer hold.
    `pending_point_ids` and `pending_link_ids` mark the rows of a proposal that is not in the tables yet.
    """

    by_id: dict[str, DrainagePoint] = {}
    for point in points:
        by_id.setdefault(point.point_id, point)

    outgoing: dict[str, DrainageLink] = {}
    for link in links:
        if link.from_ref in by_id and link.from_ref not in outgoing:
            outgoing[link.from_ref] = link

    upstream: dict[str, list[str]] = {}
    roots: list[str] = []
    for point_id in by_id:
        link = outgoing.get(point_id)
        if link is None or link.to_ref not in by_id or link.to_ref == point_id:
            roots.append(point_id)
        else:
            upstream.setdefault(link.to_ref, []).append(point_id)

    def order_key(point_id: str) -> tuple[float, str]:
        return (by_id[point_id].station, point_id)

    roots.sort(key=lambda point_id: (by_id[point_id].alignment_ref, _KIND_ORDER.get(by_id[point_id].kind, 3), *order_key(point_id)))

    checks = _checks_by_point(by_id, links, check_rows)
    grades = {row.link_ref: float(row.grade_percent) for row in link_rows}

    # Parents come before their children in `walked`, so building it backwards has every child ready.
    walked: list[str] = []
    pending = list(roots)
    while pending:
        point_id = pending.pop(0)
        walked.append(point_id)
        pending.extend(sorted(upstream.get(point_id, ()), key=order_key))
    built: dict[str, FlowNode] = {}
    for point_id in reversed(walked):
        children = tuple(built[child] for child in sorted(upstream.get(point_id, ()), key=order_key))
        built[point_id] = _node(by_id[point_id], outgoing.get(point_id), by_id, checks, grades, children, pending_point_ids, pending_link_ids)

    seen = set(walked)
    loop_ids = sorted((point_id for point_id in by_id if point_id not in seen), key=order_key)
    return FlowTree(
        roots=tuple(built[point_id] for point_id in roots),
        loop_nodes=tuple(
            _node(by_id[point_id], outgoing.get(point_id), by_id, checks, grades, (), pending_point_ids, pending_link_ids)
            for point_id in loop_ids
        ),
    )


def walk_flow_nodes(nodes):
    """Every node under `nodes`, each parent before its children."""

    stack = list(reversed(list(nodes)))
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def flow_node_severity(node: FlowNode) -> str:
    """`error` or `warning` when a check of the node has that severity, else an empty string."""

    severities = {row.severity for row in node.check_rows}
    if CHECK_ERROR in severities:
        return CHECK_ERROR
    return CHECK_WARNING if CHECK_WARNING in severities else ""


def _node(point, link, by_id, checks, grades, children, pending_point_ids=frozenset(), pending_link_ids=frozenset()) -> FlowNode:
    pending = "point" if point.point_id in pending_point_ids else "link" if link is not None and link.link_id in pending_link_ids else ""
    return FlowNode(
        pending=pending,
        point_id=point.point_id,
        kind=point.kind,
        ditch_run_ref=point.ditch_run_ref,
        alignment_ref=point.alignment_ref,
        station=float(point.station),
        drains_to=link.to_ref if link is not None else "",
        drains_to_missing=link is not None and link.to_ref not in by_id,
        link_ref=link.link_id if link is not None else "",
        link_grade_percent=grades.get(link.link_id) if link is not None else None,
        check_rows=tuple(checks.get(point.point_id, ())),
        children=children,
    )


def _checks_by_point(by_id: dict[str, DrainagePoint], links: list[DrainageLink], check_rows) -> dict[str, list]:
    """Each check beside the point it names, the From point of a link it names, or (a station
    check) the nearest point of its run.

    A check id is `kind:ref`, with the point or link id as `ref`.
    """

    link_from = {link.link_id: link.from_ref for link in links if link.from_ref in by_id}
    attached: dict[str, list] = {}
    for row in check_rows:
        reference = str(row.check_id)[len(row.kind) + 1:] if str(row.check_id).startswith(f"{row.kind}:") else ""
        target = reference if reference in by_id else link_from.get(reference, "")
        if not target and row.kind in CHECKS_AT_NEAREST_POINT:
            target = _nearest_point_on_run(by_id, row)
        if target:
            attached.setdefault(target, []).append(row)
    return attached


def _nearest_point_on_run(by_id: dict[str, DrainagePoint], check) -> str:
    middle = (float(check.station_start) + float(check.station_end)) / 2.0
    on_run = [point for point in by_id.values() if point.ditch_run_ref and point.ditch_run_ref == check.ditch_run_ref]
    if not on_run:
        return ""
    return min(on_run, key=lambda point: (abs(point.station - middle), point.point_id)).point_id


@dataclass(frozen=True)
class FlowContinuation:
    """What Add Upstream or Add Downstream adds to the tables, or why it adds nothing.

    `select_point_id` is the node the panel selects next, so pressing again walks on from it.
    """

    points: tuple[DrainagePoint, ...] = ()
    links: tuple[DrainageLink, ...] = ()
    select_point_id: str = ""
    message: str = ""

    @property
    def added(self) -> bool:
        return bool(self.points or self.links)


def add_upstream(
    node_id: str,
    points: list[DrainagePoint],
    links: list[DrainageLink],
    flowlines: list,
    max_inlet_spacing_m: float,
) -> FlowContinuation:
    """A new inlet one equal step up the ditch from `node_id`, linked into it.

    The step is taken from the stretch between the node and the next point, high point or run end
    that way, split into equal parts so the Policy's maximum spacing holds; pressing again from the
    new inlet walks on to the crest. Where both sides rise (a low point) the longer stretch goes
    first. `flowlines` are the stored current Drainage result's.
    """

    node = _point_named(points, node_id)
    if node is None:
        return FlowContinuation(message="Select a point in the tree first.")
    if not node.ditch_run_ref:
        return FlowContinuation(
            message=f"{node.point_id} crosses the road and has no ditch of its own; add the inlet on a ditch in the Points tab."
        )
    line = _flowline_of(flowlines, node.ditch_run_ref)
    if line is None:
        return FlowContinuation(message=f"{node.ditch_run_ref} has no flowline in the Drainage result; run Rebuild Downstream.")
    if not float(max_inlet_spacing_m) > 0.0:
        return FlowContinuation(message="The Policy's maximum inlet spacing must be above 0 m.")
    geometry = _Flowline(line.station_rows)
    marks = sorted(
        {
            geometry.stations[0],
            geometry.stations[-1],
            *[float(value) for value in line.high_point_stations],
            *[
                other.station
                for other in points
                if other.point_id != node.point_id
                and (other.ditch_run_ref == node.ditch_run_ref or (other.kind == "culvert" and not other.ditch_run_ref))
            ],
        }
    )
    here = geometry.length_at(node.station)
    rising = []
    for direction in (-1, 1):
        if not geometry.rises(node.station, direction):
            continue
        beyond = [mark for mark in marks if (mark - node.station) * direction > STATION_TOLERANCE_M]
        if not beyond:
            continue
        boundary = min(beyond, key=lambda mark: abs(mark - node.station))
        stretch = abs(geometry.length_at(boundary) - here)
        rising.append((stretch, direction, boundary))
    if not rising:
        return FlowContinuation(
            message=f"{node.point_id}: the ditch does not rise on either side of STA {node.station:.3f}, so nothing drains into it from upstream."
        )
    # the longer stretch first; on a tie the one toward the run start
    stretch, direction, boundary = max(rising, key=lambda row: (row[0], -row[1]))
    parts = math.ceil(stretch / float(max_inlet_spacing_m) - STATION_TOLERANCE_M)
    if parts <= 1:
        return FlowContinuation(
            message=(
                f"{node.point_id}: the ditch up to STA {boundary:.3f} is {stretch:.1f} m, within the "
                f"{float(max_inlet_spacing_m):.1f} m maximum spacing; nothing more is needed upstream."
            )
        )
    station = round(geometry.station_at(here + direction * stretch / parts), 3)
    inlet = DrainagePoint(
        next_point_id("inlet", {point.point_id for point in points}),
        "inlet",
        station,
        side=node.side,
        ditch_run_ref=node.ditch_run_ref,
        alignment_ref=node.alignment_ref,
    )
    link = DrainageLink(next_point_id("link", {link.link_id for link in links}), inlet.point_id, node.point_id)
    return FlowContinuation(
        points=(inlet,),
        links=(link,),
        select_point_id=inlet.point_id,
        message=f"Added {inlet.point_id} at STA {station:.3f}, draining into {node.point_id}.",
    )


def add_downstream(
    node_id: str,
    points: list[DrainagePoint],
    links: list[DrainageLink],
    flowlines: list,
) -> FlowContinuation:
    """A link from `node_id`, which drains nowhere, to the nearest lower point, or to a new outfall.

    The nearest lower point is on the node's run (or a culvert crossing its road). With none, the
    outfall goes at the run end the ditch falls toward all the way; a ditch that rises again before
    its end has a low point to collect first, so nothing is added.
    """

    node = _point_named(points, node_id)
    if node is None:
        return FlowContinuation(message="Select a point in the tree first.")
    if node.kind == "outfall":
        return FlowContinuation(message=f"{node.point_id} is an outfall: the water leaves the network here.")
    target = next((link.to_ref for link in links if link.from_ref == node.point_id), "")
    if target:
        return FlowContinuation(message=f"{node.point_id} already drains into {target}; delete that link first to send it elsewhere.")
    places = point_places(points, flowlines)
    here = places.get(node.point_id)
    if here is None:
        return FlowContinuation(
            message=f"{node.point_id} lies on no flowline of the Drainage result, so its way down cannot be found; run Rebuild Downstream."
        )
    used = {link.link_id for link in links}
    lower = _lower_points(node, points, places, here)
    if lower:
        nearest = min(lower, key=lambda point: (abs(point.station - node.station), point.point_id))
        link = DrainageLink(next_point_id("link", used), node.point_id, nearest.point_id)
        return FlowContinuation(links=(link,), select_point_id=nearest.point_id, message=f"Linked {node.point_id} into {nearest.point_id}.")
    if not node.ditch_run_ref:
        return FlowContinuation(message=f"{node.point_id} crosses the road and no lower point is on its road; link it to an outfall in the Links tab.")
    line = _flowline_of(flowlines, node.ditch_run_ref)
    if line is None:
        return FlowContinuation(message=f"{node.ditch_run_ref} has no flowline in the Drainage result; run Rebuild Downstream.")
    geometry = _Flowline(line.station_rows)
    ends = [direction for direction in (-1, 1) if geometry.falls_to_end(node.station, direction)]
    if not ends:
        return FlowContinuation(
            message=(
                f"{node.point_id}: the ditch does not fall to either end of {node.ditch_run_ref} from STA {node.station:.3f}; "
                "water collects at a low point first. Add an inlet at that low point."
            )
        )
    direction = min(ends, key=lambda value: (geometry.z_at(geometry.end_station(value)), -value))
    station = round(geometry.end_station(direction), 3)
    outfall = DrainagePoint(
        next_point_id("outfall", {point.point_id for point in points}),
        "outfall",
        station,
        side=node.side,
        ditch_run_ref=node.ditch_run_ref,
        alignment_ref=node.alignment_ref,
    )
    link = DrainageLink(next_point_id("link", used), node.point_id, outfall.point_id)
    return FlowContinuation(
        points=(outfall,),
        links=(link,),
        select_point_id=outfall.point_id,
        message=f"Added {outfall.point_id} at the run end STA {station:.3f}, and linked {node.point_id} into it.",
    )


def _point_named(points: list[DrainagePoint], point_id: str) -> DrainagePoint | None:
    return next((point for point in points if point.point_id == point_id), None)


def _flowline_of(flowlines: list, ditch_run_ref: str):
    return next((row for row in flowlines if row.ditch_run_ref == ditch_run_ref and len(row.station_rows) >= 2), None)


class _Flowline:
    """A run's flowline stations with plan length along them, for stepping up and down the ditch."""

    def __init__(self, station_rows) -> None:
        self.stations = [float(row.station) for row in station_rows]
        self.elevations = [float(row.z) for row in station_rows]
        self.lengths = [0.0]
        for first, second in zip(station_rows, station_rows[1:]):
            self.lengths.append(self.lengths[-1] + math.hypot(second.x - first.x, second.y - first.y))

    def length_at(self, station: float) -> float:
        return self._interpolate(self.lengths, station)

    def z_at(self, station: float) -> float:
        return self._interpolate(self.elevations, station)

    def station_at(self, length: float) -> float:
        for index in range(1, len(self.lengths)):
            if length <= self.lengths[index] + STATION_TOLERANCE_M:
                span = self.lengths[index] - self.lengths[index - 1]
                ratio = 0.0 if span <= 0.0 else (length - self.lengths[index - 1]) / span
                return self.stations[index - 1] + (self.stations[index] - self.stations[index - 1]) * min(max(ratio, 0.0), 1.0)
        return self.stations[-1]

    def end_station(self, direction: int) -> float:
        return self.stations[-1] if direction > 0 else self.stations[0]

    def rises(self, station: float, direction: int) -> bool:
        """True when the ditch is higher at the next section beyond `station` in `direction`."""

        beyond = self._next_vertex(station, direction)
        return beyond is not None and self.elevations[beyond] - self.z_at(station) > ELEVATION_TOLERANCE_M

    def falls_to_end(self, station: float, direction: int) -> bool:
        """True when the ditch falls (or stays level) from `station` all the way to the run end."""

        vertex = self._next_vertex(station, direction)
        if vertex is None or not self.z_at(station) - self.elevations[vertex] > ELEVATION_TOLERANCE_M:
            return False
        step = 1 if direction > 0 else -1
        while 0 <= vertex + step < len(self.stations):
            if self.elevations[vertex + step] - self.elevations[vertex] > ELEVATION_TOLERANCE_M:
                return False
            vertex += step
        return True

    def _next_vertex(self, station: float, direction: int) -> int | None:
        indexes = range(len(self.stations)) if direction > 0 else reversed(range(len(self.stations)))
        return next((index for index in indexes if (self.stations[index] - station) * direction > STATION_TOLERANCE_M), None)

    def _interpolate(self, values: list[float], station: float) -> float:
        if station <= self.stations[0]:
            return values[0]
        for index in range(1, len(self.stations)):
            if station <= self.stations[index] + STATION_TOLERANCE_M:
                span = self.stations[index] - self.stations[index - 1]
                ratio = 0.0 if span <= 0.0 else (station - self.stations[index - 1]) / span
                return values[index - 1] + (values[index] - values[index - 1]) * min(max(ratio, 0.0), 1.0)
        return values[-1]


@dataclass(frozen=True)
class NetworkProposal:
    """The points and links Trace Network would add, and the inlets it could not drain.

    A proposal is never stored: the panel shows it as pending and the user accepts or discards it.
    """

    points: tuple[DrainagePoint, ...] = ()
    links: tuple[DrainageLink, ...] = ()
    undrained: tuple[str, ...] = ()
    message: str = ""

    @property
    def found(self) -> bool:
        return bool(self.points or self.links)


def trace_network(
    points: list[DrainagePoint],
    links: list[DrainageLink],
    flowlines: list,
    *,
    low_point_rule: str,
    max_inlet_spacing_m: float,
) -> NetworkProposal:
    """The missing network: the points the checks would suggest, then a way down for every inlet.

    Points come first (an outfall at a low point that falls to a run end, inlets at other low points
    and where the spacing needs them), computed from `points` as they stand and the stored
    flowlines. Then each inlet that drains nowhere, lowest first, is linked to the nearest lower
    point or to a new outfall at the run end it falls toward (`add_downstream`). Existing points and
    links are never moved or removed, so tracing again after hand edits fills only what is left.
    """

    working_points = list(points)
    working_links = list(links)
    new_points: list[DrainagePoint] = []
    new_links: list[DrainageLink] = []
    for flowline in sorted(flowlines, key=lambda row: (row.alignment_ref, row.ditch_run_ref)):
        for suggestion in suggest_points(flowline, working_points, low_point_rule=low_point_rule, max_inlet_spacing_m=max_inlet_spacing_m):
            point = DrainagePoint(
                next_point_id(suggestion.kind, {row.point_id for row in working_points}),
                suggestion.kind,
                float(suggestion.station),
                side=flowline.side,
                ditch_run_ref=flowline.ditch_run_ref,
                alignment_ref=flowline.alignment_ref,
            )
            working_points.append(point)
            new_points.append(point)
    places = point_places(working_points, flowlines)
    draining = {link.from_ref for link in working_links}
    waiting = sorted(
        (point for point in working_points if point.kind == "inlet" and point.point_id not in draining),
        key=lambda point: (places[point.point_id][2] if point.point_id in places else float("inf"), point.point_id),
    )
    undrained: list[str] = []
    notes: list[str] = []
    for inlet in waiting:
        step = add_downstream(inlet.point_id, working_points, working_links, flowlines)
        if not step.added:
            undrained.append(inlet.point_id)
            notes.append(step.message)
            continue
        working_points.extend(step.points)
        working_links.extend(step.links)
        new_points.extend(step.points)
        new_links.extend(step.links)
    if new_points or new_links:
        text = f"Proposed {len(new_points)} point(s) and {len(new_links)} link(s). Accept to add them to the tables, or Discard."
    else:
        text = "Nothing to add: the points and links already cover every low point, the inlet spacing and every inlet's way down."
    if notes:
        text += "\n" + "\n".join(notes)
    return NetworkProposal(tuple(new_points), tuple(new_links), tuple(undrained), text)


# What each check offers as a fix. A fix is an action the panel can run on the check's point.
_FIXES_BY_CHECK_KIND = {
    "drains_nowhere": (("add_downstream", "Add Downstream"),),
    "low_point_uncollected": (("add_suggested", "Add Suggested Point"),),
    "inlet_spacing": (("add_suggested", "Add Suggested Points"),),
    "link_uphill": (("reconnect", "Reconnect To"), ("delete_link", "Delete Link")),
    "link_flat": (("reconnect", "Reconnect To"), ("delete_link", "Delete Link")),
    "link_loop": (("delete_link", "Delete Link"),),
    "drains_twice": (("delete_extra_links", "Delete Extra Links"),),
    "reverse_flow": (("delete_point", "Delete Point"),),
    "point_off_run": (("delete_point", "Delete Point"),),
}


@dataclass(frozen=True)
class FlowFix:
    """One action that fixes a check: `action` is the key, `label` the button text."""

    action: str
    label: str


@dataclass(frozen=True)
class FlowEdit:
    """The table changes of a fix, or why there are none. Nothing is written until Apply."""

    add_points: tuple[DrainagePoint, ...] = ()
    add_links: tuple[DrainageLink, ...] = ()
    remove_point_ids: tuple[str, ...] = ()
    remove_link_ids: tuple[str, ...] = ()
    relink: tuple[tuple[str, str], ...] = ()  # (link id, the point it now drains into)
    message: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.add_points or self.add_links or self.remove_point_ids or self.remove_link_ids or self.relink)


def fixes_for_check(check) -> tuple[FlowFix, ...]:
    """The fixes a check offers; empty for a check the Flow tab has no action for."""

    return tuple(FlowFix(action, label) for action, label in _FIXES_BY_CHECK_KIND.get(str(check.kind), ()))


def reconnect_targets(node_id: str, points: list[DrainagePoint], flowlines: list) -> list[str]:
    """The points the node could drain into instead: the lower ones, nearest first."""

    node = _point_named(points, node_id)
    places = point_places(points, flowlines)
    if node is None or node.point_id not in places:
        return []
    lower = _lower_points(node, points, places, places[node.point_id])
    return [point.point_id for point in sorted(lower, key=lambda point: (abs(point.station - node.station), point.point_id))]


def edit_for_fix(
    action: str,
    check,
    node_id: str,
    points: list[DrainagePoint],
    links: list[DrainageLink],
    flowlines: list,
    *,
    low_point_rule: str,
    max_inlet_spacing_m: float,
    target: str = "",
) -> FlowEdit:
    """The table changes that fix `check` on the point `node_id`, by `action` (see `fixes_for_check`)."""

    node = _point_named(points, node_id)
    if node is None:
        return FlowEdit(message="Select a point in the tree first.")
    if action == "add_downstream":
        step = add_downstream(node_id, points, links, flowlines)
        return FlowEdit(add_points=step.points, add_links=step.links, message=step.message)
    if action == "add_suggested":
        return _add_suggested_edit(check, points, flowlines, low_point_rule, max_inlet_spacing_m)
    if action == "delete_point":
        touching = tuple(link.link_id for link in links if node_id in (link.from_ref, link.to_ref))
        text = f"Deleted {node_id}" + (f" and the {len(touching)} link(s) that touched it." if touching else ".")
        return FlowEdit(remove_point_ids=(node_id,), remove_link_ids=touching, message=text)
    outgoing = [link for link in links if link.from_ref == node_id]
    if action == "delete_extra_links":
        extra = tuple(link.link_id for link in outgoing[1:])
        if not extra:
            return FlowEdit(message=f"{node_id} has only one link out.")
        return FlowEdit(remove_link_ids=extra, message=f"Deleted {', '.join(extra)}; {node_id} keeps {outgoing[0].link_id}.")
    link = _link_of_check(check, outgoing)
    if link is None:
        return FlowEdit(message=f"The link of this check is not in the Links table; {node_id} has no link out.")
    if action == "delete_link":
        return FlowEdit(remove_link_ids=(link.link_id,), message=f"Deleted {link.link_id}.")
    if action == "reconnect":
        if target not in reconnect_targets(node_id, points, flowlines):
            return FlowEdit(message=f"{target or 'That point'} is not a lower point {node_id} can drain into.")
        return FlowEdit(relink=((link.link_id, target),), message=f"{link.link_id} now drains {node_id} into {target}.")
    return FlowEdit(message=f"There is no fix '{action}'.")


def _lower_points(node: DrainagePoint, points: list[DrainagePoint], places: dict, here) -> list[DrainagePoint]:
    """The points lower than `node` that it may drain into: on its run, or a culvert crossing its road."""

    return [
        point
        for point in points
        if point.point_id != node.point_id
        and point.point_id in places
        and places[point.point_id][2] < here[2]
        and (node.kind == "culvert" or point.ditch_run_ref == node.ditch_run_ref or (point.kind == "culvert" and not point.ditch_run_ref))
    ]


def _link_of_check(check, outgoing: list[DrainageLink]):
    """The link a link check names (`link_uphill:link:1`), else the point's first link out (a loop)."""

    prefix = f"{check.kind}:"
    named = str(check.check_id)[len(prefix):] if str(check.check_id).startswith(prefix) else ""
    return next((link for link in outgoing if link.link_id == named), outgoing[0] if outgoing and check.kind == "link_loop" else None)


def _add_suggested_edit(check, points, flowlines, low_point_rule: str, max_inlet_spacing_m: float) -> FlowEdit:
    line = _flowline_of(flowlines, check.ditch_run_ref)
    if line is None:
        return FlowEdit(message=f"{check.ditch_run_ref or 'The run'} has no flowline in the Drainage result; run Rebuild Downstream.")
    start, end = sorted((float(check.station_start), float(check.station_end)))
    working = list(points)
    added: list[DrainagePoint] = []
    for suggestion in suggest_points(line, working, low_point_rule=low_point_rule, max_inlet_spacing_m=max_inlet_spacing_m):
        if not start - STATION_ENTRY_TOLERANCE_M <= suggestion.station <= end + STATION_ENTRY_TOLERANCE_M:
            continue
        point = DrainagePoint(
            next_point_id(suggestion.kind, {row.point_id for row in working}),
            suggestion.kind,
            float(suggestion.station),
            side=line.side,
            ditch_run_ref=line.ditch_run_ref,
            alignment_ref=line.alignment_ref,
        )
        working.append(point)
        added.append(point)
    if not added:
        return FlowEdit(message=f"No suggested point falls within STA {start:.3f} to {end:.3f} of {check.ditch_run_ref}.")
    names = ", ".join(f"{point.point_id} at STA {point.station:.3f}" for point in added)
    return FlowEdit(add_points=tuple(added), message=f"Added {names}.")
