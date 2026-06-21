"""Closed solid profile builder for ParametricRoad v1 watertight solids."""

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
            if _is_lined_ditch_target(target):
                basis, section_diagnostics = _basis_from_lined_ditch_section(section, target=target)
            elif _is_subassembly_scoped_target(target):
                basis, section_diagnostics = _basis_from_subassembly_section(section, target=target)
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
            target_subassembly_ref=str(getattr(target, "subassembly_ref", "") or ""),
            is_subassembly_target=_is_subassembly_scoped_target(target),
            target_drainage_ref=str(getattr(target, "drainage_ref", "") or ""),
            is_lined_ditch_target=_is_lined_ditch_target(target),
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
    nodes: tuple[_ProfileBasisNode, ...]
    notes: str = ""


def _subassembly_note(subassembly_ref: str, compatibility_ref: str = "") -> str:
    subassembly = str(subassembly_ref or "").strip()
    if subassembly:
        return f"subassembly={subassembly}"
    return "subassembly=(none)"


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


def _basis_from_subassembly_section(
    section: AppliedSection,
    *,
    target: SolidTargetRow,
) -> tuple[_ProfileBasis | None, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    target_id = str(getattr(target, "target_id", "") or "solid-target:subassembly")
    subassembly_ref = str(getattr(target, "subassembly_ref", "") or "").strip()
    station = float(getattr(section, "station", 0.0) or 0.0)
    source_row = _section_subassembly_row(section, subassembly_ref)
    if source_row is None:
        return None, diagnostics
    frame = getattr(section, "frame", None)
    if frame is None:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_subassembly_profile_frame",
                message="Subassembly solid profile requires an Applied Section frame.",
                notes=f"{target_id};subassembly_ref={subassembly_ref};station={station:g}",
            )
        )
        return None, diagnostics
    width = max(float(getattr(source_row, "width", 0.0) or 0.0), 0.0)
    thickness = max(float(getattr(source_row, "thickness", 0.0) or 0.0), 0.0)
    if width <= 0.0 or thickness <= 0.0:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="invalid_subassembly_profile_dimensions",
                message="Subassembly solid profile requires positive width and thickness.",
                notes=f"{target_id};subassembly_ref={subassembly_ref};station={station:g};width={width:g};thickness={thickness:g}",
            )
        )
        return None, diagnostics
    left_offset, right_offset = _subassembly_dimension_offsets(source_row)
    active_ref = subassembly_ref or str(getattr(source_row, "subassembly_id", "") or "")
    top_left = _point_at_offset(frame, left_offset, point_id=f"{active_ref}:top-left")
    top_right = _point_at_offset(frame, right_offset, point_id=f"{active_ref}:top-right")
    bottom_left = _offset_point_from(top_left, z_delta=-thickness, point_id=f"{active_ref}:bottom-left")
    bottom_right = _offset_point_from(top_right, z_delta=-thickness, point_id=f"{active_ref}:bottom-right")
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    return (
        _ProfileBasis(
            station=station,
            applied_section_ref=str(getattr(section, "applied_section_id", "") or f"station:{station:g}"),
            region_ref=str(getattr(source_row, "region_id", "") or getattr(section, "region_id", "") or ""),
            profile_role=str(getattr(target, "target_family", "") or "pavement_layer_body"),
            nodes=(
                _basis_node("top_left", top_left, frame_z),
                _basis_node("top_right", top_right, frame_z),
                _basis_node("bottom_right", bottom_right, frame_z),
                _basis_node("bottom_left", bottom_left, frame_z),
            ),
            notes=(
                f"subassembly_ref={subassembly_ref};"
                f"material={str(getattr(source_row, 'material', '') or '')}"
            ),
        ),
        diagnostics,
    )


def _basis_from_lined_ditch_section(
    section: AppliedSection,
    *,
    target: SolidTargetRow,
) -> tuple[_ProfileBasis | None, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    target_id = str(getattr(target, "target_id", "") or "solid-target:lined-ditch")
    side = _lined_ditch_side(target)
    target_subassembly_ref = str(getattr(target, "subassembly_ref", "") or "").strip()
    station = float(getattr(section, "station", 0.0) or 0.0)
    frame = getattr(section, "frame", None)
    if frame is None:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_lined_ditch_profile_frame",
                message="Lined ditch solid profile requires an Applied Section frame.",
                notes=f"{target_id};station={station:g};side={side}",
            )
        )
        return None, diagnostics
    points = _ditch_surface_points(section, side)
    if len(points) < 2:
        return None, diagnostics
    source_row = _ditch_subassembly_row(
        section,
        side,
        target_ref=target_subassembly_ref,
    )
    thickness = _ditch_lining_thickness(source_row)
    if thickness <= 0.0:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="missing_lined_ditch_thickness",
                message="Lined ditch solid profile requires positive lining thickness.",
                notes=f"{target_id};station={station:g};side={side}",
            )
        )
        return None, diagnostics
    join_policy = _ditch_lining_join_policy(source_row)
    miter_limit = _ditch_lining_miter_limit(source_row)
    top_points = sorted(points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0), reverse=True)
    if abs(
        float(getattr(top_points[0], "lateral_offset", 0.0) or 0.0)
        - float(getattr(top_points[-1], "lateral_offset", 0.0) or 0.0)
    ) <= 1.0e-9:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="degenerate_lined_ditch_profile_width",
                message="Lined ditch profile top-left and top-right nodes resolve to the same lateral offset.",
                notes=f"{target_id};station={station:g};side={side}",
            )
        )
        return None, diagnostics
    bottom_points, offset_diagnostics = _lined_ditch_bottom_points(
        frame,
        top_points,
        thickness=thickness,
        join_policy=join_policy,
        miter_limit=miter_limit,
        side=side,
        target_id=target_id,
        station=station,
    )
    diagnostics.extend(offset_diagnostics)
    if len(bottom_points) != len(top_points):
        return None, diagnostics
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    subassembly_ref = str(getattr(target, "subassembly_ref", "") or getattr(source_row, "subassembly_id", "") or "")
    material = str(getattr(source_row, "material", "") or getattr(target, "material_ref", "") or "")
    top_nodes = [
        _basis_node(_lined_ditch_top_role(index, len(top_points)), point, frame_z)
        for index, point in enumerate(top_points)
    ]
    bottom_nodes = [
        _basis_node(_lined_ditch_bottom_role(index, len(bottom_points)), point, frame_z)
        for index, point in enumerate(reversed(bottom_points))
    ]
    return (
        _ProfileBasis(
            station=station,
            applied_section_ref=str(getattr(section, "applied_section_id", "") or f"station:{station:g}"),
            region_ref=str(getattr(source_row, "region_id", "") or getattr(section, "region_id", "") or ""),
            profile_role="lined_ditch_body",
            nodes=tuple(top_nodes + bottom_nodes),
            notes=(
                f"drainage_ref={str(getattr(target, 'drainage_ref', '') or '')};"
                f"flow_route_ref={str(getattr(target, 'flow_route_ref', '') or '')};"
                f"subassembly_ref={subassembly_ref};"
                f"side={side};material={material};"
                f"lining_thickness={thickness:g};join_policy={join_policy};miter_limit={miter_limit:g}"
            ),
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
    edge_rows = []
    for index, (start_node, end_node) in enumerate(zip(node_rows, node_rows[1:] + node_rows[:1]), start=1):
        edge_role = _profile_edge_role(start_node.semantic_role, end_node.semantic_role, index, len(node_rows))
        edge_rows.append(
            SolidProfileEdge(
                edge_id=f"{safe_profile}:edge:{edge_role}",
                start_node_id=start_node.node_id,
                end_node_id=end_node.node_id,
                semantic_role=edge_role,
                source_ref=basis.applied_section_ref,
            )
        )
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


def _profile_edge_role(start_role: str, end_role: str, index: int, node_count: int) -> str:
    if node_count == 4:
        edge_by_roles = {
            ("top_left", "top_right"): "top_edge",
            ("top_right", "bottom_right"): "right_side_edge",
            ("bottom_right", "bottom_left"): "bottom_edge",
            ("bottom_left", "top_left"): "left_side_edge",
        }
        role = edge_by_roles.get((start_role, end_role))
        if role:
            return role
    return f"profile_edge_{index:03d}"


def _profile_stations(
    sections: list[AppliedSection],
    *,
    station_start: float,
    station_end: float,
    target_region_ref: str = "",
    is_region_target: bool = False,
    target_subassembly_ref: str = "",
    is_subassembly_target: bool = False,
    target_drainage_ref: str = "",
    is_lined_ditch_target: bool = False,
    target_id: str = "",
) -> tuple[list[float], list[DiagnosticMessage]]:
    if station_end < station_start:
        station_start, station_end = station_end, station_start
    diagnostics: list[DiagnosticMessage] = []
    region_ref = str(target_region_ref or "").strip()
    subassembly_ref = str(target_subassembly_ref or "").strip()
    lined_ditch_side = _lined_ditch_side_from_refs(target_drainage_ref, target_id)
    values = [float(station_start), float(station_end)]
    matching_region_count = 0
    matching_subassembly_count = 0
    matching_lined_ditch_count = 0
    for section in list(sections or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        if station < station_start or station > station_end:
            continue
        if is_lined_ditch_target and not _ditch_surface_points(section, lined_ditch_side):
            diagnostics.append(
                DiagnosticMessage(
                    severity="info",
                    kind="skipped_missing_lined_ditch_profile",
                    message="A station profile inside the target range was skipped because the target lined ditch is not active.",
                    notes=f"{target_id};station={station:g};side={lined_ditch_side}",
                )
            )
            continue
        if (
            is_subassembly_target
            and subassembly_ref
            and _section_subassembly_row(section, subassembly_ref) is None
        ):
            diagnostics.append(
                DiagnosticMessage(
                    severity="info",
                    kind="skipped_missing_subassembly_profile",
                    message="A station profile inside the target range was skipped because the target Subassembly is not active.",
                    notes=f"{target_id};station={station:g};{_subassembly_note(subassembly_ref)}",
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
        if is_subassembly_target and subassembly_ref:
            matching_subassembly_count += 1
        if is_lined_ditch_target:
            matching_lined_ditch_count += 1
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
    if is_subassembly_target and subassembly_ref and matching_subassembly_count == 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="subassembly_target_no_matching_source_profiles",
                message="Subassembly solid target has no Applied Section profiles explicitly carrying the target Subassembly inside its range.",
                notes=f"{target_id};{_subassembly_note(subassembly_ref)};range={station_start:g}->{station_end:g}",
            )
        )
    if is_lined_ditch_target and matching_lined_ditch_count == 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="lined_ditch_target_no_matching_source_profiles",
                message="Lined ditch solid target has no Applied Section ditch profiles inside its range.",
                notes=f"{target_id};side={lined_ditch_side};range={station_start:g}->{station_end:g}",
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
    if is_subassembly_target and len(ordered) >= 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="subassembly_boundary_cap_profiles",
                message="Subassembly solid target uses target start/end stations as capped boundary profiles.",
                notes=f"{target_id};start={ordered[0]:g};end={ordered[-1]:g};profile_count={len(ordered)}",
            )
        )
    if is_lined_ditch_target and len(ordered) >= 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="lined_ditch_boundary_cap_profiles",
                message="Lined ditch solid target uses target start/end stations as capped boundary profiles.",
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


def _is_subassembly_scoped_target(target: SolidTargetRow) -> bool:
    family = str(getattr(target, "target_family", "") or "").strip().lower()
    scope = str(getattr(target, "scope_kind", "") or "").strip().lower()
    return (
        scope == "assembly_subassembly"
        or family in {"pavement_layer_body", "subbase_body", "shoulder_body"}
    )


def _is_lined_ditch_target(target: SolidTargetRow) -> bool:
    return str(getattr(target, "target_family", "") or "").strip().lower() == "lined_ditch_body"


def _lined_ditch_side(target: SolidTargetRow) -> str:
    return _lined_ditch_side_from_refs(
        str(getattr(target, "drainage_ref", "") or ""),
        str(getattr(target, "target_id", "") or ""),
        str(getattr(target, "subassembly_ref", "") or ""),
    )


def _lined_ditch_side_from_refs(*values: str) -> str:
    for value in values:
        text = str(value or "").strip().lower()
        if "right" in text:
            return "right"
        if "left" in text:
            return "left"
    return "left"


def _section_subassembly_row(section: AppliedSection, subassembly_ref: str):
    expected_subassembly = str(subassembly_ref or "").strip()
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or [])
    if expected_subassembly:
        for subassembly in subassembly_rows:
            if str(getattr(subassembly, "subassembly_id", "") or "").strip() == expected_subassembly:
                return subassembly
    return None


def _subassembly_dimension_offsets(subassembly) -> tuple[float, float]:
    width = max(float(getattr(subassembly, "width", 0.0) or 0.0), 0.0)
    side = str(getattr(subassembly, "side", "") or "center").strip().lower()
    if side == "left":
        return width, 0.0
    if side == "right":
        return 0.0, -width
    return width * 0.5, -width * 0.5


def _ditch_surface_points(section: AppliedSection, side: str) -> list[AppliedSectionPoint]:
    expected_side = str(side or "").strip().lower()
    rows = []
    for point in list(getattr(section, "point_rows", []) or []):
        if str(getattr(point, "point_role", "") or "").strip().lower() != "ditch_surface":
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if expected_side == "left" and offset > 0.0:
            rows.append(point)
        elif expected_side == "right" and offset < 0.0:
            rows.append(point)
    return sorted(rows, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))


def _ditch_subassembly_row(section: AppliedSection, side: str, *, target_ref: str = ""):
    expected_ref = str(target_ref or "").strip()
    expected_side = str(side or "").strip().lower()
    fallback = None
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or [])
    for subassembly in subassembly_rows:
        if str(getattr(subassembly, "kind", "") or "").strip().lower() != "ditch":
            continue
        subassembly_id = str(getattr(subassembly, "subassembly_id", "") or "").strip()
        if expected_ref and subassembly_id == expected_ref:
            return subassembly
        subassembly_side = str(getattr(subassembly, "side", "") or "center").strip().lower()
        if subassembly_side == expected_side or subassembly_side in {"both", "center"}:
            fallback = subassembly
    if fallback is not None:
        return fallback
    return None


def _ditch_lining_thickness(subassembly) -> float:
    if subassembly is None:
        return 0.0
    thickness = max(float(getattr(subassembly, "thickness", 0.0) or 0.0), 0.0)
    if thickness > 0.0:
        return thickness
    params = dict(getattr(subassembly, "parameters", {}) or {})
    for key in ("lining_thickness", "wall_thickness"):
        try:
            value = max(float(params.get(key, 0.0) or 0.0), 0.0)
        except Exception:
            value = 0.0
        if value > 0.0:
            return value
    return 0.0


def _ditch_lining_join_policy(subassembly) -> str:
    params = dict(getattr(subassembly, "parameters", {}) or {}) if subassembly is not None else {}
    raw = str(
        params.get("lining_join_policy", "")
        or params.get("lining_join", "")
        or params.get("join_policy", "")
        or "normal_average"
    ).strip().lower()
    if raw in {"miter", "mitre"}:
        return "miter"
    return "normal_average"


def _ditch_lining_miter_limit(subassembly) -> float:
    params = dict(getattr(subassembly, "parameters", {}) or {}) if subassembly is not None else {}
    for key in ("lining_miter_limit", "miter_limit"):
        try:
            value = float(params.get(key, 0.0) or 0.0)
        except Exception:
            value = 0.0
        if value > 0.0:
            return value
    return 2.0


def _lined_ditch_bottom_points(
    frame: AppliedSectionFrame,
    top_points: list[AppliedSectionPoint],
    *,
    thickness: float,
    join_policy: str,
    miter_limit: float,
    side: str,
    target_id: str,
    station: float,
) -> tuple[list[AppliedSectionPoint], list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    points = list(top_points or [])
    if len(points) < 2:
        return [], [
            DiagnosticMessage(
                severity="error",
                kind="degenerate_lined_ditch_offset_normal",
                message="Lined ditch profile cannot compute lining offset normals from fewer than two surface points.",
                notes=f"{target_id};station={station:g};side={side}",
            )
        ]
    offset_points: list[tuple[float, float]] = []
    for index, point in enumerate(points):
        adjacent_normals = []
        if index > 0:
            adjacent_normals.append(_downward_segment_normal(points[index - 1], point))
        if index < len(points) - 1:
            adjacent_normals.append(_downward_segment_normal(point, points[index + 1]))
        adjacent_normals = [normal for normal in adjacent_normals if normal is not None]
        if not adjacent_normals:
            return [], [
                DiagnosticMessage(
                    severity="error",
                    kind="degenerate_lined_ditch_offset_normal",
                    message="Lined ditch profile cannot compute a lining offset normal from coincident surface points.",
                    notes=f"{target_id};station={station:g};side={side};index={index + 1}",
                )
            ]
        if str(join_policy or "").strip().lower() == "miter" and 0 < index < len(points) - 1:
            miter_point = _miter_join_point(
                points[index - 1],
                point,
                points[index + 1],
                thickness=thickness,
                miter_limit=miter_limit,
            )
            if miter_point is not None:
                offset_points.append(miter_point)
                continue
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="lined_ditch_miter_limit_fallback",
                    message="Lined ditch miter join exceeded its limit or could not be solved, so normal-average offset was used.",
                    notes=f"{target_id};station={station:g};side={side};index={index + 1};miter_limit={miter_limit:g}",
                )
            )
        normal_offset, normal_z = _average_downward_normal(adjacent_normals)
        offset_points.append(
            (
                float(getattr(point, "lateral_offset", 0.0) or 0.0) + normal_offset * float(thickness),
                float(getattr(point, "z", 0.0) or 0.0) + normal_z * float(thickness),
            )
        )
    if str(join_policy or "").strip().lower() == "miter" and len(points) > 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="lined_ditch_miter_join_offset",
                message="Lined ditch solid profile used miter join offset where permitted by the miter limit.",
                notes=f"{target_id};station={station:g};side={side};points={len(points)};thickness={thickness:g};miter_limit={miter_limit:g}",
            )
        )
    elif len(points) > 2:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="lined_ditch_polyline_normal_offset",
                message="Lined ditch solid profile used multi-point polyline normal offset.",
                notes=f"{target_id};station={station:g};side={side};points={len(points)};thickness={thickness:g}",
            )
        )
    output: list[AppliedSectionPoint] = []
    for index, (offset, z) in enumerate(offset_points, start=1):
        output.append(
            _point_at_offset_and_z(
                frame,
                offset,
                z,
                point_id=f"lined-ditch:{side}:bottom:{index}",
            )
        )
    return output, diagnostics


def _average_downward_normal(normals: list[tuple[float, float]]) -> tuple[float, float]:
    normal_offset = sum(normal[0] for normal in normals)
    normal_z = sum(normal[1] for normal in normals)
    length = math.hypot(normal_offset, normal_z)
    if length <= 1.0e-12:
        normal_offset, normal_z = normals[0]
    else:
        normal_offset /= length
        normal_z /= length
    if normal_z > 0.0:
        normal_offset *= -1.0
        normal_z *= -1.0
    return normal_offset, normal_z


def _miter_join_point(
    previous_point: AppliedSectionPoint,
    point: AppliedSectionPoint,
    next_point: AppliedSectionPoint,
    *,
    thickness: float,
    miter_limit: float,
) -> tuple[float, float] | None:
    previous_normal = _downward_segment_normal(previous_point, point)
    next_normal = _downward_segment_normal(point, next_point)
    if previous_normal is None or next_normal is None:
        return None
    vertex = _section_point_2d(point)
    previous_a = _offset_2d(previous_point, previous_normal, thickness)
    previous_b = _offset_2d(point, previous_normal, thickness)
    next_a = _offset_2d(point, next_normal, thickness)
    next_b = _offset_2d(next_point, next_normal, thickness)
    intersection = _line_intersection(previous_a, previous_b, next_a, next_b)
    if intersection is None:
        return None
    miter_length = math.hypot(intersection[0] - vertex[0], intersection[1] - vertex[1])
    limit = max(float(thickness or 0.0), 0.0) * max(float(miter_limit or 0.0), 0.0)
    if limit <= 0.0 or miter_length > limit + 1.0e-9:
        return None
    return intersection


def _section_point_2d(point: AppliedSectionPoint) -> tuple[float, float]:
    return (
        float(getattr(point, "lateral_offset", 0.0) or 0.0),
        float(getattr(point, "z", 0.0) or 0.0),
    )


def _offset_2d(point: AppliedSectionPoint, normal: tuple[float, float], thickness: float) -> tuple[float, float]:
    offset, z = _section_point_2d(point)
    return offset + normal[0] * float(thickness), z + normal[1] * float(thickness)


def _line_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, float] | None:
    ax = a2[0] - a1[0]
    ay = a2[1] - a1[1]
    bx = b2[0] - b1[0]
    by = b2[1] - b1[1]
    denominator = ax * by - ay * bx
    if abs(denominator) <= 1.0e-12:
        return None
    cx = b1[0] - a1[0]
    cy = b1[1] - a1[1]
    ratio = (cx * by - cy * bx) / denominator
    return a1[0] + ax * ratio, a1[1] + ay * ratio


def _downward_segment_normal(start: AppliedSectionPoint, end: AppliedSectionPoint) -> tuple[float, float] | None:
    start_offset = float(getattr(start, "lateral_offset", 0.0) or 0.0)
    end_offset = float(getattr(end, "lateral_offset", 0.0) or 0.0)
    start_z = float(getattr(start, "z", 0.0) or 0.0)
    end_z = float(getattr(end, "z", 0.0) or 0.0)
    delta_offset = end_offset - start_offset
    delta_z = end_z - start_z
    length = math.hypot(delta_offset, delta_z)
    if length <= 1.0e-12:
        return None
    normal_offset = delta_z / length
    normal_z = -delta_offset / length
    if normal_z > 0.0:
        normal_offset *= -1.0
        normal_z *= -1.0
    return normal_offset, normal_z


def _point_at_offset_and_z(frame: AppliedSectionFrame, offset: float, z: float, *, point_id: str) -> AppliedSectionPoint:
    theta = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(theta)
    normal_y = math.cos(theta)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    return AppliedSectionPoint(
        point_id=point_id,
        x=base_x + normal_x * float(offset),
        y=base_y + normal_y * float(offset),
        z=float(z),
        point_role="lined_ditch_bottom_surface",
        lateral_offset=float(offset),
    )


def _lined_ditch_top_role(index: int, count: int) -> str:
    if index == 0:
        return "top_left"
    if index == count - 1:
        return "top_right"
    return f"top_mid_{index:03d}"


def _lined_ditch_bottom_role(index: int, count: int) -> str:
    if index == 0:
        return "bottom_right"
    if index == count - 1:
        return "bottom_left"
    return f"bottom_mid_{index:03d}"


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
