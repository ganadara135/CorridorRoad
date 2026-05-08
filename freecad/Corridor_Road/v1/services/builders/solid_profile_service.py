"""Closed solid profile builder for CorridorRoad v1 watertight solids."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.applied_section_solid_profile import (
    AppliedSectionSolidProfile,
    AppliedSectionSolidProfileSet,
    SOLID_PROFILE_ORIENTATION,
    SolidProfileEdge,
    SolidProfileNode,
)
from ...models.source.solid_target_model import SolidTargetRow


@dataclass(frozen=True)
class SolidProfileBuildRequest:
    """Input bundle for building closed profiles for one solid target."""

    project_id: str
    solid_target: SolidTargetRow
    applied_section_set: AppliedSectionSet
    corridor_ref: str = ""
    profile_set_id: str = ""
    fallback_depth: float = 0.5


class AppliedSectionSolidProfileService:
    """Build semantic closed profiles before edge-network and shell generation."""

    def build(self, request: SolidProfileBuildRequest) -> AppliedSectionSolidProfileSet:
        """Build one ordered profile set for one solid target."""

        target = request.solid_target
        target_id = str(getattr(target, "target_id", "") or "solid-target:unknown")
        station_start, station_end = _target_range(target, request.applied_section_set)
        sections = _ordered_sections(request.applied_section_set)
        diagnostics: list[DiagnosticMessage] = []
        basis_by_station: dict[float, _ProfileBasis] = {}
        for section in sections:
            if _is_component_target(target):
                basis, section_diagnostics = _basis_from_component_section(section, target=target)
            else:
                basis, section_diagnostics = _basis_from_section(
                    section,
                    target_id=target_id,
                    fallback_depth=float(request.fallback_depth or 0.0),
                )
            diagnostics.extend(section_diagnostics)
            if basis is not None:
                basis_by_station[round(basis.station, 9)] = basis

        stations, station_diagnostics = _profile_stations(
            sections,
            station_start=station_start,
            station_end=station_end,
            target_region_ref=str(getattr(target, "region_ref", "") or ""),
            is_region_target=_is_region_target(target),
            target_component_ref=str(getattr(target, "component_ref", "") or ""),
            is_component_target=_is_component_target(target),
            target_id=target_id,
        )
        diagnostics.extend(station_diagnostics)
        profile_rows: list[AppliedSectionSolidProfile] = []
        for station in stations:
            basis, profile_diagnostics = _basis_at_station(
                station,
                basis_by_station,
                target_id=target_id,
                target_region_ref=str(getattr(target, "region_ref", "") or ""),
            )
            diagnostics.extend(profile_diagnostics)
            if basis is None:
                continue
            profile_rows.append(_profile_from_basis(basis, target=target))

        if len(profile_rows) < 2:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="insufficient_closed_profiles",
                    message="At least two closed profiles are required for watertight solid edge-network generation.",
                    notes=target_id,
                )
            )

        return AppliedSectionSolidProfileSet(
            schema_version=1,
            project_id=str(request.project_id or getattr(request.applied_section_set, "project_id", "") or "corridorroad-v1"),
            profile_set_id=str(request.profile_set_id or f"solid-profiles:{_safe_id(target_id)}"),
            corridor_ref=str(request.corridor_ref or getattr(request.applied_section_set, "corridor_id", "") or ""),
            target_ref=target_id,
            applied_section_set_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
            station_start=station_start,
            station_end=station_end,
            label=f"Solid Profiles - {target_id}",
            source_refs=_unique_refs(
                [
                    target_id,
                    str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                    *list(getattr(target, "source_refs", []) or []),
                ]
            ),
            diagnostic_rows=diagnostics,
            profile_rows=profile_rows,
        )


@dataclass(frozen=True)
class _ProfileBasisNode:
    semantic_role: str
    x: float
    y: float
    z: float
    lateral_offset: float
    vertical_offset: float
    source_point_ref: str = ""


@dataclass(frozen=True)
class _ProfileBasis:
    station: float
    applied_section_ref: str
    region_ref: str
    profile_role: str
    nodes: tuple[_ProfileBasisNode, _ProfileBasisNode, _ProfileBasisNode, _ProfileBasisNode]
    notes: str = ""


def _target_range(target: SolidTargetRow, applied: AppliedSectionSet) -> tuple[float, float]:
    start = float(getattr(target, "station_start", 0.0) or 0.0)
    end = float(getattr(target, "station_end", 0.0) or 0.0)
    if end > start:
        return start, end
    stations = [float(getattr(section, "station", 0.0) or 0.0) for section in _ordered_sections(applied)]
    if not stations:
        return start, end
    return min(stations), max(stations)


def _ordered_sections(applied: AppliedSectionSet) -> list[AppliedSection]:
    sections = list(getattr(applied, "sections", []) or [])
    return sorted(sections, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))


def _basis_from_section(
    section: AppliedSection,
    *,
    target_id: str,
    fallback_depth: float,
) -> tuple[_ProfileBasis | None, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    station = float(getattr(section, "station", 0.0) or 0.0)
    top_points = _role_points(section, {"fg_surface", "design_surface", "top_surface"})
    if len(top_points) < 2:
        top_points = _derived_top_points(section)
        if len(top_points) >= 2:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="derived_top_profile_points",
                    message="Solid profile top nodes were derived from Applied Section width and frame because semantic top points were incomplete.",
                    notes=f"{target_id};station={station:g}",
                )
            )
    if len(top_points) < 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_top_profile_points",
                message="Solid profile requires at least two top points.",
                notes=f"{target_id};station={station:g}",
            )
        )
        return None, diagnostics

    top_left = max(top_points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    top_right = min(top_points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    if abs(float(getattr(top_left, "lateral_offset", 0.0) or 0.0) - float(getattr(top_right, "lateral_offset", 0.0) or 0.0)) <= 1.0e-9:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="degenerate_top_profile_width",
                message="Solid profile top-left and top-right nodes resolve to the same lateral offset.",
                notes=f"{target_id};station={station:g}",
            )
        )
        return None, diagnostics

    bottom_points = _role_points(section, {"subgrade_surface", "bottom_surface"})
    bottom_left = _nearest_offset_point(bottom_points, float(getattr(top_left, "lateral_offset", 0.0) or 0.0))
    bottom_right = _nearest_offset_point(bottom_points, float(getattr(top_right, "lateral_offset", 0.0) or 0.0))
    notes = ""
    if bottom_left is None or bottom_right is None:
        depth = max(float(fallback_depth or 0.0), 0.0)
        bottom_left = _offset_point_from(top_left, z_delta=-depth, point_id="fallback:bottom-left")
        bottom_right = _offset_point_from(top_right, z_delta=-depth, point_id="fallback:bottom-right")
        notes = f"fallback_depth={depth:g}"
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="fallback_profile_depth",
                message="Solid profile bottom nodes used fallback depth because subgrade_surface points were not available.",
                notes=f"{target_id};station={station:g};fallback_depth={depth:g}",
            )
        )

    frame_z = float(getattr(getattr(section, "frame", None), "z", 0.0) or 0.0)
    nodes = (
        _basis_node("top_left", top_left, frame_z),
        _basis_node("top_right", top_right, frame_z),
        _basis_node("bottom_right", bottom_right, frame_z),
        _basis_node("bottom_left", bottom_left, frame_z),
    )
    return (
        _ProfileBasis(
            station=station,
            applied_section_ref=str(getattr(section, "applied_section_id", "") or f"station:{station:g}"),
            region_ref=str(getattr(section, "region_id", "") or ""),
            profile_role="road_body_envelope",
            nodes=nodes,
            notes=notes,
        ),
        diagnostics,
    )


def _basis_from_component_section(
    section: AppliedSection,
    *,
    target: SolidTargetRow,
) -> tuple[_ProfileBasis | None, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    target_id = str(getattr(target, "target_id", "") or "solid-target:component")
    component_ref = str(getattr(target, "component_ref", "") or "").strip()
    station = float(getattr(section, "station", 0.0) or 0.0)
    component = _section_component(section, component_ref)
    if component is None:
        return None, diagnostics
    frame = getattr(section, "frame", None)
    if frame is None:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_component_profile_frame",
                message="Component solid profile requires an Applied Section frame.",
                notes=f"{target_id};component={component_ref};station={station:g}",
            )
        )
        return None, diagnostics
    width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
    thickness = max(float(getattr(component, "thickness", 0.0) or 0.0), 0.0)
    if width <= 0.0 or thickness <= 0.0:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="invalid_component_profile_dimensions",
                message="Component solid profile requires positive width and thickness.",
                notes=f"{target_id};component={component_ref};station={station:g};width={width:g};thickness={thickness:g}",
            )
        )
        return None, diagnostics
    left_offset, right_offset = _component_offsets(component)
    top_left = _point_at_offset(frame, left_offset, point_id=f"{component_ref}:top-left")
    top_right = _point_at_offset(frame, right_offset, point_id=f"{component_ref}:top-right")
    bottom_left = _offset_point_from(top_left, z_delta=-thickness, point_id=f"{component_ref}:bottom-left")
    bottom_right = _offset_point_from(top_right, z_delta=-thickness, point_id=f"{component_ref}:bottom-right")
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    return (
        _ProfileBasis(
            station=station,
            applied_section_ref=str(getattr(section, "applied_section_id", "") or f"station:{station:g}"),
            region_ref=str(getattr(component, "region_id", "") or getattr(section, "region_id", "") or ""),
            profile_role=str(getattr(target, "target_family", "") or "pavement_layer_body"),
            nodes=(
                _basis_node("top_left", top_left, frame_z),
                _basis_node("top_right", top_right, frame_z),
                _basis_node("bottom_right", bottom_right, frame_z),
                _basis_node("bottom_left", bottom_left, frame_z),
            ),
            notes=f"component_ref={component_ref};material={str(getattr(component, 'material', '') or '')}",
        ),
        diagnostics,
    )


def _basis_at_station(
    station: float,
    basis_by_station: dict[float, _ProfileBasis],
    *,
    target_id: str,
    target_region_ref: str,
) -> tuple[_ProfileBasis | None, list[DiagnosticMessage]]:
    key = round(float(station), 9)
    exact = basis_by_station.get(key)
    if exact is not None:
        if target_region_ref:
            exact = _basis_with_region(exact, target_region_ref)
        return exact, []
    ordered = sorted(basis_by_station.values(), key=lambda basis: basis.station)
    if not ordered:
        return None, [
            DiagnosticMessage(
                severity="error",
                kind="no_profile_basis",
                message="No Applied Section profiles were available for interpolation.",
                notes=target_id,
            )
        ]
    left = None
    right = None
    for before, after in zip(ordered, ordered[1:]):
        if before.station <= station <= after.station:
            left = before
            right = after
            break
    if left is None or right is None:
        return None, [
            DiagnosticMessage(
                severity="error",
                kind="station_outside_profile_basis",
                message="Requested solid profile station is outside the available Applied Section profile range.",
                notes=f"{target_id};station={station:g}",
            )
        ]
    span = right.station - left.station
    ratio = 0.0 if abs(span) <= 1.0e-12 else (float(station) - left.station) / span
    nodes = tuple(
        _interpolated_node(left_node, right_node, ratio)
        for left_node, right_node in zip(left.nodes, right.nodes)
    )
    return (
        _ProfileBasis(
            station=float(station),
            applied_section_ref=f"interpolated:{left.applied_section_ref}:{right.applied_section_ref}",
            region_ref=target_region_ref or left.region_ref or right.region_ref,
            profile_role=left.profile_role,
            nodes=nodes,  # type: ignore[arg-type]
            notes=f"interpolated_from={left.station:g},{right.station:g}",
        ),
        [
            DiagnosticMessage(
                severity="info",
                kind="interpolated_boundary_profile",
                message="Solid profile was interpolated at a target boundary station without modifying Applied Sections.",
                notes=f"{target_id};station={station:g};from={left.station:g},{right.station:g}",
            )
        ],
    )


def _profile_from_basis(basis: _ProfileBasis, *, target: SolidTargetRow) -> AppliedSectionSolidProfile:
    target_id = str(getattr(target, "target_id", "") or "solid-target:unknown")
    safe_profile = f"solid-profile:{_safe_id(target_id)}:{_safe_station(basis.station)}"
    node_rows = [
        SolidProfileNode(
            node_id=f"{safe_profile}:node:{node.semantic_role}",
            semantic_role=node.semantic_role,
            x=node.x,
            y=node.y,
            z=node.z,
            lateral_offset=node.lateral_offset,
            vertical_offset=node.vertical_offset,
            source_point_ref=node.source_point_ref,
        )
        for node in basis.nodes
    ]
    edge_specs = [
        ("top_edge", "top_left", "top_right"),
        ("right_side_edge", "top_right", "bottom_right"),
        ("bottom_edge", "bottom_right", "bottom_left"),
        ("left_side_edge", "bottom_left", "top_left"),
    ]
    node_by_role = {node.semantic_role: node.node_id for node in node_rows}
    edge_rows = [
        SolidProfileEdge(
            edge_id=f"{safe_profile}:edge:{role}",
            start_node_id=node_by_role[start_role],
            end_node_id=node_by_role[end_role],
            semantic_role=role,
            source_ref=basis.applied_section_ref,
        )
        for role, start_role, end_role in edge_specs
    ]
    return AppliedSectionSolidProfile(
        profile_id=safe_profile,
        target_id=target_id,
        station=float(basis.station),
        applied_section_ref=basis.applied_section_ref,
        region_ref=str(getattr(target, "region_ref", "") or basis.region_ref),
        profile_role=str(getattr(target, "target_family", "") or basis.profile_role),
        node_rows=node_rows,
        edge_rows=edge_rows,
        is_closed=True,
        orientation=SOLID_PROFILE_ORIENTATION,
        notes=basis.notes,
    )


def _profile_stations(
    sections: list[AppliedSection],
    *,
    station_start: float,
    station_end: float,
    target_region_ref: str = "",
    is_region_target: bool = False,
    target_component_ref: str = "",
    is_component_target: bool = False,
    target_id: str = "",
) -> tuple[list[float], list[DiagnosticMessage]]:
    if station_end < station_start:
        station_start, station_end = station_end, station_start
    diagnostics: list[DiagnosticMessage] = []
    region_ref = str(target_region_ref or "").strip()
    component_ref = str(target_component_ref or "").strip()
    values = [float(station_start), float(station_end)]
    matching_region_count = 0
    matching_component_count = 0
    for section in list(sections or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        if station < station_start or station > station_end:
            continue
        if is_component_target and component_ref and _section_component(section, component_ref) is None:
            diagnostics.append(
                DiagnosticMessage(
                    severity="info",
                    kind="skipped_missing_component_profile",
                    message="A station profile inside the target range was skipped because the target component is not active.",
                    notes=f"{target_id};station={station:g};component={component_ref}",
                )
            )
            continue
        section_region = str(getattr(section, "region_id", "") or "").strip()
        if is_region_target and region_ref and section_region != region_ref:
            diagnostics.append(
                DiagnosticMessage(
                    severity="info",
                    kind="skipped_non_region_profile",
                    message="A station profile inside the target range was skipped because it belongs to another Region.",
                    notes=f"{target_id};station={station:g};section_region={section_region};target_region={region_ref}",
                )
            )
            continue
        if is_region_target and region_ref:
            matching_region_count += 1
        if is_component_target and component_ref:
            matching_component_count += 1
        values.append(station)
    if is_region_target and region_ref and matching_region_count == 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="region_target_no_matching_source_profiles",
                message="Region solid target has no Applied Section profiles explicitly tagged with the target Region inside its range.",
                notes=f"{target_id};region={region_ref};range={station_start:g}->{station_end:g}",
            )
        )
    if is_component_target and component_ref and matching_component_count == 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="component_target_no_matching_source_profiles",
                message="Component solid target has no Applied Section profiles explicitly carrying the target component inside its range.",
                notes=f"{target_id};component={component_ref};range={station_start:g}->{station_end:g}",
            )
        )
    ordered = _unique_sorted_floats(values)
    if is_region_target and len(ordered) >= 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="region_boundary_cap_profiles",
                message="Region solid target uses target start/end stations as capped boundary profiles.",
                notes=f"{target_id};start={ordered[0]:g};end={ordered[-1]:g};profile_count={len(ordered)}",
            )
        )
    if is_component_target and len(ordered) >= 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="component_boundary_cap_profiles",
                message="Component solid target uses target start/end stations as capped boundary profiles.",
                notes=f"{target_id};start={ordered[0]:g};end={ordered[-1]:g};profile_count={len(ordered)}",
            )
        )
    return ordered, diagnostics


def _role_points(section: AppliedSection, roles: set[str]) -> list[AppliedSectionPoint]:
    expected = {str(role or "").strip().lower() for role in roles}
    return [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "").strip().lower() in expected
    ]


def _derived_top_points(section: AppliedSection) -> list[AppliedSectionPoint]:
    frame = getattr(section, "frame", None)
    if frame is None:
        return []
    left = max(float(getattr(section, "surface_left_width", 0.0) or 0.0), 0.0)
    right = -max(float(getattr(section, "surface_right_width", 0.0) or 0.0), 0.0)
    if abs(left - right) <= 1.0e-9:
        return []
    return [
        _point_at_offset(frame, left, point_id="derived:top-left"),
        _point_at_offset(frame, right, point_id="derived:top-right"),
    ]


def _point_at_offset(frame: AppliedSectionFrame, offset: float, *, point_id: str) -> AppliedSectionPoint:
    theta = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(theta)
    normal_y = math.cos(theta)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    z = float(getattr(frame, "z", 0.0) or 0.0)
    return AppliedSectionPoint(
        point_id=point_id,
        x=base_x + normal_x * float(offset),
        y=base_y + normal_y * float(offset),
        z=z,
        point_role="derived_top_surface",
        lateral_offset=float(offset),
    )


def _nearest_offset_point(points: list[AppliedSectionPoint], offset: float) -> AppliedSectionPoint | None:
    if not points:
        return None
    return min(points, key=lambda point: abs(float(getattr(point, "lateral_offset", 0.0) or 0.0) - float(offset)))


def _offset_point_from(point: AppliedSectionPoint, *, z_delta: float, point_id: str) -> AppliedSectionPoint:
    return AppliedSectionPoint(
        point_id=point_id,
        x=float(getattr(point, "x", 0.0) or 0.0),
        y=float(getattr(point, "y", 0.0) or 0.0),
        z=float(getattr(point, "z", 0.0) or 0.0) + float(z_delta),
        point_role="fallback_bottom_surface",
        lateral_offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
    )


def _basis_node(role: str, point: AppliedSectionPoint, frame_z: float) -> _ProfileBasisNode:
    z = float(getattr(point, "z", 0.0) or 0.0)
    return _ProfileBasisNode(
        semantic_role=role,
        x=float(getattr(point, "x", 0.0) or 0.0),
        y=float(getattr(point, "y", 0.0) or 0.0),
        z=z,
        lateral_offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
        vertical_offset=z - float(frame_z),
        source_point_ref=str(getattr(point, "point_id", "") or ""),
    )


def _interpolated_node(left: _ProfileBasisNode, right: _ProfileBasisNode, ratio: float) -> _ProfileBasisNode:
    return _ProfileBasisNode(
        semantic_role=left.semantic_role,
        x=_lerp(left.x, right.x, ratio),
        y=_lerp(left.y, right.y, ratio),
        z=_lerp(left.z, right.z, ratio),
        lateral_offset=_lerp(left.lateral_offset, right.lateral_offset, ratio),
        vertical_offset=_lerp(left.vertical_offset, right.vertical_offset, ratio),
        source_point_ref=f"interpolated:{left.source_point_ref}:{right.source_point_ref}",
    )


def _basis_with_region(basis: _ProfileBasis, region_ref: str) -> _ProfileBasis:
    return _ProfileBasis(
        station=basis.station,
        applied_section_ref=basis.applied_section_ref,
        region_ref=region_ref,
        profile_role=basis.profile_role,
        nodes=basis.nodes,
        notes=basis.notes,
    )


def _is_region_target(target: SolidTargetRow) -> bool:
    return (
        str(getattr(target, "scope_kind", "") or "").strip().lower() == "region"
        or str(getattr(target, "target_family", "") or "").strip().lower() == "region_body"
    )


def _is_component_target(target: SolidTargetRow) -> bool:
    return (
        str(getattr(target, "scope_kind", "") or "").strip().lower() == "assembly_component"
        or str(getattr(target, "target_family", "") or "").strip().lower() == "pavement_layer_body"
    )


def _section_component(section: AppliedSection, component_ref: str):
    expected = str(component_ref or "").strip()
    if not expected:
        return None
    for component in list(getattr(section, "component_rows", []) or []):
        if str(getattr(component, "component_id", "") or "").strip() == expected:
            return component
    return None


def _component_offsets(component) -> tuple[float, float]:
    width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
    side = str(getattr(component, "side", "") or "center").strip().lower()
    if side == "left":
        return width, 0.0
    if side == "right":
        return 0.0, -width
    return width * 0.5, -width * 0.5


def _unique_sorted_floats(values: list[float]) -> list[float]:
    output: list[float] = []
    seen: set[float] = set()
    for value in sorted(float(item) for item in list(values or [])):
        key = round(value, 9)
        if key in seen:
            continue
        seen.add(key)
        output.append(float(value))
    return output


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


def _safe_station(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p") or "0"


def _lerp(start: float, end: float, ratio: float) -> float:
    return float(start) + (float(end) - float(start)) * float(ratio)
