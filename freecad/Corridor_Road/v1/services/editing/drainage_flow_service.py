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
from ..evaluation.drainage_evaluation_service import ELEVATION_TOLERANCE_M, STATION_TOLERANCE_M, point_places
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
) -> FlowTree:
    """The flow forest of `points` and `links`.

    `check_rows` are the stored Drainage result's checks and `link_rows` its measured links; pass
    them only while that result is current, since a stale one may name stations that no longer hold.
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
        built[point_id] = _node(by_id[point_id], outgoing.get(point_id), by_id, checks, grades, children)

    seen = set(walked)
    loop_ids = sorted((point_id for point_id in by_id if point_id not in seen), key=order_key)
    return FlowTree(
        roots=tuple(built[point_id] for point_id in roots),
        loop_nodes=tuple(_node(by_id[point_id], outgoing.get(point_id), by_id, checks, grades, ()) for point_id in loop_ids),
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


def _node(point, link, by_id, checks, grades, children) -> FlowNode:
    return FlowNode(
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
    lower = [
        point
        for point in points
        if point.point_id != node.point_id
        and point.point_id in places
        and places[point.point_id][2] < here[2]
        and (node.kind == "culvert" or point.ditch_run_ref == node.ditch_run_ref or (point.kind == "culvert" and not point.ditch_run_ref))
    ]
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
