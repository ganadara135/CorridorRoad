"""Solid edge-network builder and topology validator for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...models.result.applied_section_solid_profile import AppliedSectionSolidProfile, AppliedSectionSolidProfileSet
from ...models.result.solid_edge_network import (
    SolidEdgeNetwork,
    SolidFaceRow,
    SolidTopologyEdgeRow,
)


COORDINATE_MATCH_TOLERANCE_M = 1.0e-6
SHORT_EDGE_WARNING_THRESHOLD_M = 1.0e-4
TINY_FACE_AREA_WARNING_THRESHOLD_M2 = 1.0e-8

_FOUR_NODE_FACE_KIND_BY_ROLES = {
    ("top_left", "top_right"): "top",
    ("top_right", "bottom_right"): "right_side",
    ("bottom_right", "bottom_left"): "bottom",
    ("bottom_left", "top_left"): "left_side",
}


@dataclass(frozen=True)
class SolidEdgeNetworkBuildRequest:
    """Input bundle for building topology edges and faces from solid profiles."""

    project_id: str
    profile_set: AppliedSectionSolidProfileSet
    edge_network_id: str = ""


class SolidEdgeNetworkService:
    """Build and validate a topology-first shell network from closed profiles."""

    def build(self, request: SolidEdgeNetworkBuildRequest) -> SolidEdgeNetwork:
        profile_set = request.profile_set
        profiles = sorted(
            list(getattr(profile_set, "profile_rows", []) or []),
            key=lambda profile: float(getattr(profile, "station", 0.0) or 0.0),
        )
        target_id = str(getattr(profile_set, "target_ref", "") or "")
        diagnostics = _profile_diagnostics(profiles, target_id=target_id)
        face_rows: list[SolidFaceRow] = []
        node_points = _node_points(profiles)

        if not any(row.severity == "error" for row in diagnostics):
            face_rows = _face_rows_for_profiles(profiles, target_id=target_id)
            diagnostics.extend(_face_geometry_diagnostics(face_rows, node_points=node_points, target_id=target_id))

        edge_rows = _edge_rows_for_faces(face_rows, profiles_by_node=_profiles_by_node(profiles))
        diagnostics.extend(_edge_usage_diagnostics(edge_rows, target_id=target_id))
        diagnostics.extend(_edge_geometry_diagnostics(edge_rows, node_points=node_points, target_id=target_id))
        is_shell_closed = bool(face_rows) and bool(edge_rows) and all(row.usage_count == 2 for row in edge_rows)
        validation_status = "ok" if is_shell_closed and not any(row.severity == "error" for row in diagnostics) else "error"

        return SolidEdgeNetwork(
            schema_version=1,
            project_id=str(request.project_id or getattr(profile_set, "project_id", "") or "corridorroad-v1"),
            edge_network_id=str(request.edge_network_id or f"solid-edge-network:{_safe_id(target_id)}"),
            target_ref=target_id,
            profile_set_ref=str(getattr(profile_set, "profile_set_id", "") or ""),
            station_start=float(getattr(profile_set, "station_start", 0.0) or 0.0),
            station_end=float(getattr(profile_set, "station_end", 0.0) or 0.0),
            validation_status=validation_status,
            is_shell_closed=is_shell_closed,
            face_count=len(face_rows),
            edge_count=len(edge_rows),
            profile_count=len(profiles),
            label=f"Solid Edge Network - {target_id}",
            source_refs=_unique_refs(
                [
                    target_id,
                    str(getattr(profile_set, "profile_set_id", "") or ""),
                    *list(getattr(profile_set, "source_refs", []) or []),
                ]
            ),
            diagnostic_rows=diagnostics,
            edge_rows=edge_rows,
            face_rows=face_rows,
        )


def _profile_diagnostics(profiles: list[AppliedSectionSolidProfile], *, target_id: str) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    if len(profiles) < 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="insufficient_profiles",
                message="At least two closed profiles are required to build a solid edge network.",
                notes=target_id,
            )
        )
        return diagnostics
    last_station = None
    expected_roles: list[str] = []
    expected_orientation = ""
    for profile in profiles:
        profile_id = str(getattr(profile, "profile_id", "") or "")
        station = float(getattr(profile, "station", 0.0) or 0.0)
        nodes = list(getattr(profile, "node_rows", []) or [])
        roles = [str(getattr(node, "semantic_role", "") or "") for node in nodes]
        if last_station is not None and station <= last_station:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="invalid_profile_station_order",
                    message="Solid profiles must be ordered by strictly increasing station.",
                    notes=f"{target_id};profile={profile_id};station={station:g}",
                )
            )
        last_station = station
        if not expected_roles:
            expected_roles = roles
            expected_orientation = str(getattr(profile, "orientation", "") or "")
        if not bool(getattr(profile, "is_closed", False)):
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="profile_not_closed",
                    message="Every profile must be closed before edge-network generation.",
                    notes=f"{target_id};profile={profile_id}",
                )
            )
        if len(nodes) < 4:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="insufficient_profile_nodes",
                    message="Solid profile requires at least four nodes.",
                    notes=f"{target_id};profile={profile_id};node_count={len(nodes)}",
                )
            )
        if len(set(roles)) != len(roles):
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="duplicate_profile_node_roles",
                    message="Solid profile semantic node roles must be unique inside one profile.",
                    notes=f"{target_id};profile={profile_id};roles={','.join(roles)}",
                )
            )
        if str(getattr(profile, "orientation", "") or "") != expected_orientation:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="invalid_profile_orientation",
                    message="Profile orientation does not match the first profile in this target.",
                    notes=f"{target_id};profile={profile_id}",
                )
            )
        if roles != expected_roles:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="invalid_profile_node_order",
                    message="Profile semantic node order must match the first profile in this target.",
                    notes=f"{target_id};profile={profile_id};roles={','.join(roles)}",
                )
            )
    return diagnostics


def _face_rows_for_profiles(profiles: list[AppliedSectionSolidProfile], *, target_id: str) -> list[SolidFaceRow]:
    rows: list[SolidFaceRow] = []
    for index, (start, end) in enumerate(zip(profiles, profiles[1:]), start=1):
        start_nodes = list(getattr(start, "node_rows", []) or [])
        end_nodes = list(getattr(end, "node_rows", []) or [])
        for edge_index, (start_a, start_b, end_a, end_b) in enumerate(
            zip(start_nodes, start_nodes[1:] + start_nodes[:1], end_nodes, end_nodes[1:] + end_nodes[:1]),
            start=1,
        ):
            node_ids = [
                start_a.node_id,
                start_b.node_id,
                end_b.node_id,
                end_a.node_id,
            ]
            face_kind = _profile_edge_face_kind(start_a, start_b, len(start_nodes))
            rows.append(
                _face_row(
                    face_id=f"solid-face:{_safe_id(target_id)}:span:{index}:{edge_index}:{face_kind}",
                    target_id=target_id,
                    face_kind=face_kind,
                    node_ids=node_ids,
                    station_start=float(getattr(start, "station", 0.0) or 0.0),
                    station_end=float(getattr(end, "station", 0.0) or 0.0),
                    source_refs=[str(getattr(start, "profile_id", "") or ""), str(getattr(end, "profile_id", "") or "")],
                )
            )
    start_profile = profiles[0]
    end_profile = profiles[-1]
    rows.append(
        _face_row(
            face_id=f"solid-face:{_safe_id(target_id)}:start-cap",
            target_id=target_id,
            face_kind="start_cap",
            node_ids=[node.node_id for node in list(getattr(start_profile, "node_rows", []) or [])],
            station_start=float(getattr(start_profile, "station", 0.0) or 0.0),
            station_end=float(getattr(start_profile, "station", 0.0) or 0.0),
            source_refs=[str(getattr(start_profile, "profile_id", "") or "")],
        )
    )
    rows.append(
        _face_row(
            face_id=f"solid-face:{_safe_id(target_id)}:end-cap",
            target_id=target_id,
            face_kind="end_cap",
            node_ids=[node.node_id for node in list(getattr(end_profile, "node_rows", []) or [])],
            station_start=float(getattr(end_profile, "station", 0.0) or 0.0),
            station_end=float(getattr(end_profile, "station", 0.0) or 0.0),
            source_refs=[str(getattr(end_profile, "profile_id", "") or "")],
        )
    )
    return rows


def _profile_edge_face_kind(start_node, end_node, node_count: int) -> str:
    start_role = str(getattr(start_node, "semantic_role", "") or "")
    end_role = str(getattr(end_node, "semantic_role", "") or "")
    if int(node_count or 0) == 4:
        return _FOUR_NODE_FACE_KIND_BY_ROLES.get((start_role, end_role), "transition")
    return "transition"


def _face_row(
    *,
    face_id: str,
    target_id: str,
    face_kind: str,
    node_ids: list[str],
    station_start: float,
    station_end: float,
    source_refs: list[str],
) -> SolidFaceRow:
    return SolidFaceRow(
        face_id=face_id,
        target_id=target_id,
        face_kind=face_kind,
        node_ids=list(node_ids),
        edge_ids=_face_edge_ids(node_ids),
        station_start=float(station_start),
        station_end=float(station_end),
        source_refs=_unique_refs(source_refs),
    )


def _edge_rows_for_faces(
    face_rows: list[SolidFaceRow],
    *,
    profiles_by_node: dict[str, AppliedSectionSolidProfile],
) -> list[SolidTopologyEdgeRow]:
    by_edge: dict[str, dict[str, object]] = {}
    for face in face_rows:
        node_ids = list(getattr(face, "node_ids", []) or [])
        for start, end in zip(node_ids, node_ids[1:] + node_ids[:1]):
            edge_id = _canonical_edge_id(start, end)
            data = by_edge.setdefault(
                edge_id,
                {
                    "start_node_id": start,
                    "end_node_id": end,
                    "face_refs": [],
                    "source_refs": [],
                    "stations": [],
                    "edge_kind": _edge_kind(start, end, profiles_by_node),
                },
            )
            data["face_refs"].append(str(getattr(face, "face_id", "") or ""))
            data["source_refs"].extend(list(getattr(face, "source_refs", []) or []))
            data["stations"].extend([float(getattr(face, "station_start", 0.0) or 0.0), float(getattr(face, "station_end", 0.0) or 0.0)])
    rows: list[SolidTopologyEdgeRow] = []
    for edge_id in sorted(by_edge):
        data = by_edge[edge_id]
        stations = [float(value) for value in list(data.get("stations", []) or [])]
        rows.append(
            SolidTopologyEdgeRow(
                edge_id=edge_id,
                start_node_id=str(data["start_node_id"]),
                end_node_id=str(data["end_node_id"]),
                edge_kind=str(data.get("edge_kind", "") or "profile"),
                station_start=min(stations) if stations else 0.0,
                station_end=max(stations) if stations else 0.0,
                usage_count=len(list(data.get("face_refs", []) or [])),
                face_refs=_unique_refs(list(data.get("face_refs", []) or [])),
                source_refs=_unique_refs(list(data.get("source_refs", []) or [])),
            )
        )
    return rows


def _edge_usage_diagnostics(edge_rows: list[SolidTopologyEdgeRow], *, target_id: str) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    if not edge_rows:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_topology_edges",
                message="No topology edges were generated for shell validation.",
                notes=target_id,
            )
        )
        return diagnostics
    for row in edge_rows:
        if row.usage_count == 1:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="dangling_edge",
                    message="A watertight shell edge must be shared by exactly two faces.",
                    notes=f"{target_id};edge={row.edge_id};usage=1",
                )
            )
        elif row.usage_count > 2:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="non_manifold_edge",
                    message="A topology edge is used by more than two faces.",
                    notes=f"{target_id};edge={row.edge_id};usage={row.usage_count}",
                )
            )
    return diagnostics


def _edge_geometry_diagnostics(
    edge_rows: list[SolidTopologyEdgeRow],
    *,
    node_points: dict[str, tuple[float, float, float]],
    target_id: str,
) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for row in edge_rows:
        start = node_points.get(str(getattr(row, "start_node_id", "") or ""))
        end = node_points.get(str(getattr(row, "end_node_id", "") or ""))
        if start is None or end is None:
            continue
        length = _distance(start, end)
        if length < SHORT_EDGE_WARNING_THRESHOLD_M:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="short_topology_edge",
                    message="A topology edge is shorter than the solid quality warning threshold.",
                    notes=(
                        f"{target_id};edge={row.edge_id};"
                        f"length={length:.12g};threshold={SHORT_EDGE_WARNING_THRESHOLD_M:.12g}"
                    ),
                )
            )
    return diagnostics


def _face_geometry_diagnostics(
    face_rows: list[SolidFaceRow],
    *,
    node_points: dict[str, tuple[float, float, float]],
    target_id: str,
) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for face in face_rows:
        points = [
            node_points[node_id]
            for node_id in list(getattr(face, "node_ids", []) or [])
            if node_id in node_points
        ]
        if len(points) < 3:
            continue
        area = _polygon_area_3d(points)
        if area < TINY_FACE_AREA_WARNING_THRESHOLD_M2:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="tiny_topology_face_area",
                    message="A topology face area is below the solid quality warning threshold.",
                    notes=(
                        f"{target_id};face={getattr(face, 'face_id', '')};"
                        f"area={area:.12g};threshold={TINY_FACE_AREA_WARNING_THRESHOLD_M2:.12g}"
                    ),
                )
            )
    return diagnostics


def _node_points(profiles: list[AppliedSectionSolidProfile]) -> dict[str, tuple[float, float, float]]:
    output: dict[str, tuple[float, float, float]] = {}
    for profile in profiles:
        for node in list(getattr(profile, "node_rows", []) or []):
            node_id = str(getattr(node, "node_id", "") or "")
            if not node_id:
                continue
            output[node_id] = (
                float(getattr(node, "x", 0.0) or 0.0),
                float(getattr(node, "y", 0.0) or 0.0),
                float(getattr(node, "z", 0.0) or 0.0),
            )
    return output


def _distance(start: tuple[float, float, float], end: tuple[float, float, float]) -> float:
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(start, end)))


def _polygon_area_3d(points: list[tuple[float, float, float]]) -> float:
    cross_x = 0.0
    cross_y = 0.0
    cross_z = 0.0
    for start, end in zip(points, points[1:] + points[:1]):
        cross_x += start[1] * end[2] - start[2] * end[1]
        cross_y += start[2] * end[0] - start[0] * end[2]
        cross_z += start[0] * end[1] - start[1] * end[0]
    return 0.5 * math.sqrt(cross_x * cross_x + cross_y * cross_y + cross_z * cross_z)


def _profiles_by_node(profiles: list[AppliedSectionSolidProfile]) -> dict[str, AppliedSectionSolidProfile]:
    output: dict[str, AppliedSectionSolidProfile] = {}
    for profile in profiles:
        for node in list(getattr(profile, "node_rows", []) or []):
            output[str(getattr(node, "node_id", "") or "")] = profile
    return output


def _nodes_by_role(profile: AppliedSectionSolidProfile) -> dict[str, object]:
    return {
        str(getattr(node, "semantic_role", "") or ""): node
        for node in list(getattr(profile, "node_rows", []) or [])
    }


def _face_edge_ids(node_ids: list[str]) -> list[str]:
    return [_canonical_edge_id(start, end) for start, end in zip(node_ids, node_ids[1:] + node_ids[:1])]


def _canonical_edge_id(start_node_id: str, end_node_id: str) -> str:
    start = str(start_node_id or "")
    end = str(end_node_id or "")
    first, second = sorted([start, end])
    return f"solid-edge:{_safe_id(first)}--{_safe_id(second)}"


def _edge_kind(start_node_id: str, end_node_id: str, profiles_by_node: dict[str, AppliedSectionSolidProfile]) -> str:
    start_profile = profiles_by_node.get(str(start_node_id or ""))
    end_profile = profiles_by_node.get(str(end_node_id or ""))
    if start_profile is not None and end_profile is not None and start_profile.profile_id == end_profile.profile_id:
        return "profile"
    return "longitudinal"


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _safe_id(value: str) -> str:
    return str(value or "").strip().replace(" ", "-").replace(":", "-").replace("/", "-").replace("\\", "-") or "unknown"
