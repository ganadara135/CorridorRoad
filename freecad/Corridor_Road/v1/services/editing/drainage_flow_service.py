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

from dataclasses import dataclass

from ...models.source.drainage_model import DrainageLink, DrainagePoint

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
