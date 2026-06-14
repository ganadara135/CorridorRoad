"""Quantity builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...common.identity import new_entity_id
from ...models.output.structure_solid_output import StructureSolidOutput
from ...models.source.structure_model import StructureModel
from ...models.source.drainage_model import DrainageModel
from ...models.result.applied_section import AppliedSection
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.quantity_model import (
    QuantityAggregate,
    QuantityFragment,
    QuantityGroupingRow,
    QuantityModel,
)
from ..evaluation import SectionEarthworkVolumeService


@dataclass(frozen=True)
class QuantityBuildRequest:
    """Input contract for building grouped quantity results."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    quantity_model_id: str
    structure_solid_output: StructureSolidOutput | None = None
    structure_model: StructureModel | None = None
    drainage_model: DrainageModel | None = None


class QuantityBuildService:
    """Build quantity fragments and aggregates from applied sections."""

    def build(self, request: QuantityBuildRequest) -> QuantityModel:
        """Create a minimal quantity model from one applied section set."""

        fragment_rows: list[QuantityFragment] = []
        diagnostic_rows: list[DiagnosticMessage] = []

        for section in request.applied_section_set.sections:
            fragment_rows.extend(self._fragment_rows_for_section(section))
            fragment_rows.extend(_side_slope_surface_fragment_rows(section))
        drainage_fragments, drainage_diagnostics, drainage_source_refs = _drainage_quantity_fragment_rows(
            request.applied_section_set,
            fragment_id_prefix=f"{request.quantity_model_id}:drainage",
            drainage_model=request.drainage_model,
        )
        fragment_rows.extend(drainage_fragments)
        diagnostic_rows.extend(drainage_diagnostics)
        fragment_rows.extend(self._structure_solid_fragment_rows(request.structure_solid_output, request.structure_model))
        fragment_rows.extend(
            SectionEarthworkVolumeService().build(
                fragment_rows,
                station_values=self._station_values(request.applied_section_set),
                fragment_id_prefix=f"{request.quantity_model_id}:section-earthwork-volume",
            ).rows
        )

        grouping_row = QuantityGroupingRow(
            grouping_id=f"{request.quantity_model_id}:corridor-total",
            grouping_kind="corridor_total",
            grouping_key=request.corridor.corridor_id,
            station_start=self._min_station(request.applied_section_set),
            station_end=self._max_station(request.applied_section_set),
        )

        aggregate_rows = self._build_aggregate_rows(
            grouping_id=grouping_row.grouping_id,
            fragment_rows=fragment_rows,
        )

        return QuantityModel(
            schema_version=1,
            project_id=request.project_id,
            quantity_model_id=request.quantity_model_id,
            corridor_id=request.corridor.corridor_id,
            label=request.corridor.label or "Corridor Quantity",
            unit_context=request.corridor.unit_context,
            coordinate_context=request.corridor.coordinate_context,
            source_refs=_unique_refs(
                [
                    request.corridor.corridor_id,
                    request.applied_section_set.applied_section_set_id,
                    str(getattr(request.structure_solid_output, "structure_solid_output_id", "") or ""),
                ]
                + drainage_source_refs
                + _subassembly_refs_for_sections(request.applied_section_set.sections)
            ),
            diagnostic_rows=diagnostic_rows,
            fragment_rows=fragment_rows,
            aggregate_rows=aggregate_rows,
            grouping_rows=[grouping_row],
            comparison_rows=[],
        )

    def _fragment_rows_for_section(self, section: AppliedSection) -> list[QuantityFragment]:
        """Create minimal quantity fragments for one applied section."""

        if section.quantity_rows:
            return [
                QuantityFragment(
                    fragment_id=row.fragment_id,
                    quantity_kind=row.quantity_kind,
                    measurement_kind="station_fragment",
                    value=row.value,
                    unit=row.unit,
                    station_start=section.station,
                    station_end=section.station,
                    subassembly_ref=str(getattr(row, "subassembly_id", "") or ""),
                    component_ref=_compatibility_ref(row.component_id, str(getattr(row, "subassembly_id", "") or "")),
                    assembly_ref=section.assembly_id,
                    region_ref=section.region_id,
                    structure_ref=self._structure_ref_for_quantity_row(section, row),
                )
                for row in section.quantity_rows
            ]

        subassembly_rows = list(getattr(section, "subassembly_rows", []) or [])
        if subassembly_rows:
            return [
                QuantityFragment(
                    fragment_id=new_entity_id("quantity_fragment"),
                    quantity_kind=f"{subassembly.kind}_count",
                    measurement_kind="count",
                    value=1.0,
                    unit="ea",
                    station_start=section.station,
                    station_end=section.station,
                    subassembly_ref=str(getattr(subassembly, "subassembly_id", "") or ""),
                    component_ref="",
                    assembly_ref=section.assembly_id,
                    region_ref=section.region_id,
                    structure_ref=_first_ref(getattr(subassembly, "structure_ids", []) or []),
                )
                for subassembly in subassembly_rows
            ]

        rows: list[QuantityFragment] = []
        for component in _compatibility_component_rows(section):
            subassembly_ref = _subassembly_ref_for_compatibility_component(section, component.component_id)
            rows.append(
                QuantityFragment(
                    fragment_id=new_entity_id("quantity_fragment"),
                    quantity_kind=f"{component.kind}_count",
                    measurement_kind="count",
                    value=1.0,
                    unit="ea",
                    station_start=section.station,
                    station_end=section.station,
                    subassembly_ref=subassembly_ref,
                    component_ref=_compatibility_ref(component.component_id, subassembly_ref),
                    assembly_ref=section.assembly_id,
                    region_ref=section.region_id,
                    structure_ref=_first_ref(component.structure_ids),
                )
            )
        return rows

    def _structure_ref_for_quantity_row(
        self,
        section: AppliedSection,
        quantity_row,
    ) -> str:
        """Resolve the singular structure ref for one quantity fragment."""

        subassembly_id = str(getattr(quantity_row, "subassembly_id", "") or "").strip()
        if subassembly_id:
            for subassembly in list(getattr(section, "subassembly_rows", []) or []):
                if str(getattr(subassembly, "subassembly_id", "") or "").strip() == subassembly_id:
                    return _first_ref(getattr(subassembly, "structure_ids", []) or [])
            return ""
        if list(getattr(section, "subassembly_rows", []) or []):
            return ""
        component_id = str(getattr(quantity_row, "component_id", "") or "").strip()
        for component in _compatibility_component_rows(section):
            if component.component_id == component_id:
                return _first_ref(component.structure_ids)
        return ""

    def _structure_solid_fragment_rows(
        self,
        structure_solid_output: StructureSolidOutput | None,
        structure_model: StructureModel | None = None,
    ) -> list[QuantityFragment]:
        """Create structure quantity fragments from normalized structure solid outputs."""

        if structure_solid_output is None:
            return []
        rows: list[QuantityFragment] = []
        output_id = str(getattr(structure_solid_output, "structure_solid_output_id", "") or "structure-solids")
        bridge_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "bridge_geometry_spec_rows", []) or [])
        }
        culvert_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "culvert_geometry_spec_rows", []) or [])
        }
        wall_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(structure_model, "retaining_wall_geometry_spec_rows", []) or [])
        }
        for solid in list(getattr(structure_solid_output, "solid_rows", []) or []):
            rows.extend(
                _structure_solid_quantity_fragments(
                    output_id=output_id,
                    solid=solid,
                    bridge=bridge_by_ref.get(str(getattr(solid, "geometry_spec_id", "") or "")),
                    culvert=culvert_by_ref.get(str(getattr(solid, "geometry_spec_id", "") or "")),
                    wall=wall_by_ref.get(str(getattr(solid, "geometry_spec_id", "") or "")),
                )
            )
        return rows

    def _build_aggregate_rows(
        self,
        grouping_id: str,
        fragment_rows: list[QuantityFragment],
    ) -> list[QuantityAggregate]:
        """Create simple aggregates grouped by quantity kind and unit."""

        totals: dict[tuple[str, str], dict[str, object]] = defaultdict(
            lambda: {"value": 0.0, "fragment_refs": []}
        )

        for row in fragment_rows:
            key = (row.quantity_kind, row.unit)
            totals[key]["value"] += row.value
            totals[key]["fragment_refs"].append(row.fragment_id)

        aggregate_rows: list[QuantityAggregate] = []
        for (quantity_kind, unit), payload in sorted(totals.items()):
            aggregate_rows.append(
                QuantityAggregate(
                    aggregate_id=new_entity_id("quantity_aggregate"),
                    aggregate_kind=quantity_kind,
                    grouping_ref=grouping_id,
                    value=float(payload["value"]),
                    unit=unit,
                    fragment_refs=list(payload["fragment_refs"]),
                )
            )

        return aggregate_rows

    def _min_station(self, applied_section_set: AppliedSectionSet) -> float | None:
        """Find the lowest sampled station in one section set."""

        if not applied_section_set.station_rows:
            return None
        return min(row.station for row in applied_section_set.station_rows)

    def _max_station(self, applied_section_set: AppliedSectionSet) -> float | None:
        """Find the highest sampled station in one section set."""

        if not applied_section_set.station_rows:
            return None
        return max(row.station for row in applied_section_set.station_rows)

    def _station_values(self, applied_section_set: AppliedSectionSet) -> list[float]:
        """Return sorted station values for average-end-area volume windows."""

        return sorted(float(row.station) for row in applied_section_set.station_rows)


def _structure_solid_quantity_fragments(
    *,
    output_id: str,
    solid,
    bridge=None,
    culvert=None,
    wall=None,
) -> list[QuantityFragment]:
    solid_kind = str(getattr(solid, "solid_kind", "") or "")
    if solid_kind == "bridge_deck_solid":
        return _bridge_quantity_fragments(output_id=output_id, solid=solid, bridge=bridge)
    if solid_kind == "culvert_body_solid":
        return _culvert_quantity_fragments(output_id=output_id, solid=solid, culvert=culvert)
    if solid_kind == "retaining_wall_solid":
        return _retaining_wall_quantity_fragments(output_id=output_id, solid=solid, wall=wall)
    if solid_kind == "structure_envelope_solid":
        return [
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="envelope",
                quantity_kind="structure_envelope_volume",
                value=float(getattr(solid, "volume", 0.0) or 0.0),
                unit="m3",
            )
        ]
    return []


def _side_slope_surface_fragment_rows(section: AppliedSection) -> list[QuantityFragment]:
    rows: list[QuantityFragment] = []
    for side_label in ("left", "right"):
        points = _side_slope_quantity_points(section, side_label=side_label)
        if len(points) < 2:
            continue
        for index, (start, end) in enumerate(zip(points[:-1], points[1:]), start=1):
            role = str(getattr(end, "point_role", "") or "")
            if role == "daylight_marker":
                continue
            quantity_kind = "bench_surface_length" if role == "bench_surface" else "slope_face_length"
            length = _section_segment_length(start, end)
            if length <= 1.0e-9:
                continue
            subassembly_ref = _joined_refs(_subassembly_refs_for_points([start, end]))
            rows.append(
                QuantityFragment(
                    fragment_id=f"{section.applied_section_id}:quantity:{quantity_kind}:{side_label}:{index}",
                    quantity_kind=quantity_kind,
                    measurement_kind="section_side_slope_breakline",
                    value=length,
                    unit="m",
                    station_start=section.station,
                    station_end=section.station,
                    subassembly_ref=subassembly_ref,
                    component_ref=_compatibility_ref(_joined_refs(_compatibility_refs_for_points([start, end])), subassembly_ref),
                    assembly_ref=section.assembly_id,
                    region_ref=section.region_id,
                )
            )
    return rows


def _side_slope_quantity_points(section: AppliedSection, *, side_label: str) -> list[object]:
    edge = _quantity_terminal_edge(section, side_label=side_label)
    points = [edge]
    edge_offset = float(getattr(edge, "lateral_offset", 0.0) or 0.0)
    direction = 1.0 if side_label == "left" else -1.0
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if (offset - edge_offset) * direction < -1.0e-9:
            continue
        points.append(point)
    points.sort(key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0) - edge_offset) * direction)
    return points


@dataclass(frozen=True)
class _QuantityPoint:
    point_id: str
    z: float
    lateral_offset: float
    point_role: str = ""


def _quantity_terminal_edge(section: AppliedSection, *, side_label: str) -> _QuantityPoint:
    frame = getattr(section, "frame", None)
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    if side_label == "left":
        edge_offset = max(0.0, float(getattr(section, "surface_left_width", 0.0) or 0.0))
    else:
        edge_offset = -max(0.0, float(getattr(section, "surface_right_width", 0.0) or 0.0))
    edge_z = frame_z
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"fg_surface", "ditch_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        z = float(getattr(point, "z", frame_z) or frame_z)
        if side_label == "left":
            if offset > edge_offset or (abs(offset - edge_offset) <= 1.0e-9 and z > edge_z):
                edge_offset = offset
                edge_z = z
        elif offset < edge_offset or (abs(offset - edge_offset) <= 1.0e-9 and z > edge_z):
            edge_offset = offset
            edge_z = z
    return _QuantityPoint(f"{side_label}:terminal-edge", edge_z, edge_offset, "terminal_edge")


def _section_segment_length(start, end) -> float:
    offset_delta = float(getattr(end, "lateral_offset", 0.0) or 0.0) - float(getattr(start, "lateral_offset", 0.0) or 0.0)
    z_delta = float(getattr(end, "z", 0.0) or 0.0) - float(getattr(start, "z", 0.0) or 0.0)
    return math.sqrt(offset_delta * offset_delta + z_delta * z_delta)


def _drainage_quantity_fragment_rows(
    applied_section_set: AppliedSectionSet,
    *,
    fragment_id_prefix: str,
    drainage_model: DrainageModel | None = None,
) -> tuple[list[QuantityFragment], list[DiagnosticMessage], list[str]]:
    sections = _station_ordered_sections(applied_section_set)
    rows: list[QuantityFragment] = []
    diagnostics: list[DiagnosticMessage] = []
    drainage_refs = _drainage_refs_for_sections(sections)
    flow_route_by_drainage_ref = _flow_route_by_drainage_ref(drainage_model)
    missing_ref_count = _ditch_points_missing_drainage_ref_count(sections)
    if missing_ref_count:
        diagnostics.append(
            DiagnosticMessage(
                "warning",
                "missing_drainage_quantity_source_ref",
                f"{missing_ref_count} ditch_surface point row(s) cannot produce drainage-id quantities.",
                "Rebuild Applied Sections after assigning Drainage Elements to Regions so ditch_surface rows carry drainage_ref.",
            )
        )
    for drainage_ref in drainage_refs:
        source_sections = [
            section
            for section in sections
            if _ditch_points_for_drainage(section, drainage_ref=drainage_ref)
        ]
        if len(source_sections) < 2:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "missing_drainage_quantity_span",
                    f"Drainage ref {drainage_ref} has fewer than two section rows.",
                    "At least two station rows are required to calculate longitudinal drainage length.",
                )
            )
            continue
        rows.extend(
            _drainage_length_rows_for_ref(
                source_sections,
                drainage_ref=drainage_ref,
                flow_route_ref=flow_route_by_drainage_ref.get(drainage_ref, ""),
                fragment_id_prefix=f"{fragment_id_prefix}:{_safe_id(drainage_ref)}",
            )
        )
        if not any(row.quantity_kind == "drainage_flowline_length" and row.drainage_ref == drainage_ref for row in rows):
            diagnostics.append(
                DiagnosticMessage(
                    "info",
                    "missing_drainage_flowline_source_rows",
                    f"Drainage ref {drainage_ref} has no paired flowline/invert point rows.",
                    "First slice detects flowline rows from ditch_surface point ids containing flowline, flow, or invert.",
                )
            )
    return rows, diagnostics, _unique_refs(drainage_refs + [row.flow_route_ref for row in rows])


def _drainage_length_rows_for_ref(
    sections: list[AppliedSection],
    *,
    drainage_ref: str,
    flow_route_ref: str = "",
    fragment_id_prefix: str,
) -> list[QuantityFragment]:
    rows: list[QuantityFragment] = []
    for index, (start_section, end_section) in enumerate(zip(sections[:-1], sections[1:]), start=1):
        start_points = _ditch_points_for_drainage(start_section, drainage_ref=drainage_ref)
        end_points = _ditch_points_for_drainage(end_section, drainage_ref=drainage_ref)
        start_centroid = _representative_point_xyz(start_points)
        end_centroid = _representative_point_xyz(end_points)
        ditch_length = _xyz_distance(start_centroid, end_centroid)
        if ditch_length > 1.0e-9:
            rows.append(
                QuantityFragment(
                    fragment_id=f"{fragment_id_prefix}:ditch-length:{index}",
                    quantity_kind="drainage_ditch_length",
                    measurement_kind="drainage_applied_section_longitudinal",
                    value=ditch_length,
                    unit="m",
                    station_start=_section_station(start_section),
                    station_end=_section_station(end_section),
                    subassembly_ref=_joined_refs(_subassembly_refs_for_points(start_points + end_points)),
                    component_ref=_compatibility_ref(
                        _joined_refs(_compatibility_refs_for_points(start_points + end_points)),
                        _joined_refs(_subassembly_refs_for_points(start_points + end_points)),
                    ),
                    assembly_ref=str(getattr(start_section, "assembly_id", "") or ""),
                    region_ref=str(getattr(start_section, "region_id", "") or ""),
                    drainage_ref=drainage_ref,
                    flow_route_ref=flow_route_ref,
                )
            )
        start_flow = _flowline_points(start_points)
        end_flow = _flowline_points(end_points)
        if not start_flow or not end_flow:
            continue
        flowline_length = _xyz_distance(_representative_point_xyz(start_flow), _representative_point_xyz(end_flow))
        if flowline_length <= 1.0e-9:
            continue
        rows.append(
            QuantityFragment(
                fragment_id=f"{fragment_id_prefix}:flowline-length:{index}",
                quantity_kind="drainage_flowline_length",
                measurement_kind="drainage_applied_section_flowline",
                value=flowline_length,
                unit="m",
                station_start=_section_station(start_section),
                station_end=_section_station(end_section),
                subassembly_ref=_joined_refs(_subassembly_refs_for_points(start_flow + end_flow)),
                component_ref=_compatibility_ref(
                    _joined_refs(_compatibility_refs_for_points(start_flow + end_flow)),
                    _joined_refs(_subassembly_refs_for_points(start_flow + end_flow)),
                ),
                assembly_ref=str(getattr(start_section, "assembly_id", "") or ""),
                region_ref=str(getattr(start_section, "region_id", "") or ""),
                drainage_ref=drainage_ref,
                flow_route_ref=flow_route_ref,
            )
        )
    return rows


def _flow_route_by_drainage_ref(drainage_model: DrainageModel | None) -> dict[str, str]:
    if drainage_model is None:
        return {}
    output: dict[str, str] = {}
    for row in list(getattr(drainage_model, "flow_route_rows", []) or []):
        route_id = str(getattr(row, "flow_route_id", "") or "").strip()
        if not route_id:
            continue
        for ref in [
            str(getattr(row, "from_element_ref", "") or "").strip(),
            str(getattr(row, "to_element_ref", "") or "").strip(),
        ]:
            if ref and ref not in output:
                output[ref] = route_id
    return output


def _station_ordered_sections(applied_section_set: AppliedSectionSet) -> list[AppliedSection]:
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    rows: list[AppliedSection] = []
    for station_row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
    ):
        section = section_by_id.get(str(getattr(station_row, "applied_section_id", "") or ""))
        if section is not None:
            rows.append(section)
    if rows:
        return rows
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=_section_station)


def _drainage_refs_for_sections(sections: list[AppliedSection]) -> list[str]:
    refs: list[str] = []
    for section in sections:
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") != "ditch_surface":
                continue
            refs.append(str(getattr(point, "drainage_ref", "") or ""))
    return _unique_refs(refs)


def _ditch_points_missing_drainage_ref_count(sections: list[AppliedSection]) -> int:
    return sum(
        1
        for section in sections
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
        and not str(getattr(point, "drainage_ref", "") or "").strip()
    )


def _ditch_points_for_drainage(section: AppliedSection, *, drainage_ref: str) -> list[object]:
    points = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
        and str(getattr(point, "drainage_ref", "") or "").strip() == drainage_ref
    ]
    return sorted(points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))


def _flowline_points(points: list[object]) -> list[object]:
    output = []
    for point in list(points or []):
        point_id = str(getattr(point, "point_id", "") or "").lower()
        if "flowline" in point_id or "flow" in point_id or "invert" in point_id:
            output.append(point)
    return output


def _representative_point_xyz(points: list[object]) -> tuple[float, float, float]:
    if not points:
        return (0.0, 0.0, 0.0)
    count = float(len(points))
    return (
        sum(float(getattr(point, "x", 0.0) or 0.0) for point in points) / count,
        sum(float(getattr(point, "y", 0.0) or 0.0) for point in points) / count,
        sum(float(getattr(point, "z", 0.0) or 0.0) for point in points) / count,
    )


def _xyz_distance(start: tuple[float, float, float], end: tuple[float, float, float]) -> float:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    dz = float(end[2]) - float(start[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _section_station(section: AppliedSection) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        return float(getattr(section, "station", 0.0) or 0.0)


def _compatibility_refs_for_points(points: list[object]) -> list[str]:
    refs: list[str] = []
    for point in list(points or []):
        if str(getattr(point, "subassembly_ref", "") or "").strip():
            continue
        refs.append(str(getattr(point, "component_ref", "") or ""))
    return _unique_refs(refs)


def _compatibility_ref(component_ref: object, subassembly_ref: object = "") -> str:
    return "" if str(subassembly_ref or "").strip() else str(component_ref or "").strip()


def _compatibility_component_rows(section: AppliedSection) -> list[object]:
    """Return legacy component rows only when no active Subassembly rows exist."""

    if list(getattr(section, "subassembly_rows", []) or []):
        return []
    return list(getattr(section, "component_rows", []) or [])


def _subassembly_refs_for_sections(sections: list[AppliedSection]) -> list[str]:
    refs: list[str] = []
    for section in list(sections or []):
        refs.extend(str(getattr(row, "subassembly_id", "") or "") for row in list(getattr(section, "subassembly_rows", []) or []))
        refs.extend(str(getattr(point, "subassembly_ref", "") or "") for point in list(getattr(section, "point_rows", []) or []))
        refs.extend(str(getattr(point, "subassembly_ref", "") or "") for point in list(getattr(section, "subassembly_point_rows", []) or []))
        refs.extend(str(getattr(link, "subassembly_ref", "") or "") for link in list(getattr(section, "subassembly_link_rows", []) or []))
        refs.extend(str(getattr(shape, "subassembly_ref", "") or "") for shape in list(getattr(section, "subassembly_shape_rows", []) or []))
    return _unique_refs(refs)


def _subassembly_refs_for_points(points: list[object]) -> list[str]:
    return _unique_refs(str(getattr(point, "subassembly_ref", "") or "") for point in list(points or []))


def _subassembly_ref_for_compatibility_component(section: AppliedSection, component_ref: str) -> str:
    expected = str(component_ref or "").strip()
    if not expected:
        return ""
    for row in list(getattr(section, "subassembly_rows", []) or []):
        subassembly_id = str(getattr(row, "subassembly_id", "") or "").strip()
        if subassembly_id == expected:
            return subassembly_id
    for point in list(getattr(section, "point_rows", []) or []):
        if str(getattr(point, "component_ref", "") or "").strip() == expected:
            subassembly_ref = str(getattr(point, "subassembly_ref", "") or "").strip()
            if subassembly_ref:
                return subassembly_ref
    for point in list(getattr(section, "subassembly_point_rows", []) or []):
        subassembly_ref = str(getattr(point, "subassembly_ref", "") or "").strip()
        if subassembly_ref == expected:
            return subassembly_ref
    return ""


def _joined_refs(values) -> str:
    return ",".join(_unique_refs(values))


def _bridge_quantity_fragments(*, output_id: str, solid, bridge=None) -> list[QuantityFragment]:
    rows = [
        _structure_fragment(
            output_id=output_id,
            solid=solid,
            suffix="deck",
            quantity_kind="bridge_deck_volume",
            value=float(getattr(solid, "volume", 0.0) or 0.0),
            unit="m3",
        )
    ]
    length = _length(solid)
    deck_width = _positive(getattr(bridge, "deck_width", 0.0), fallback=_positive(getattr(solid, "width", 0.0)))
    girder_depth = _positive(getattr(bridge, "girder_depth", 0.0))
    if girder_depth > 0.0 and length > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="girder-depth",
                quantity_kind="bridge_girder_depth_length",
                value=girder_depth * length,
                unit="m2",
            )
        )
    barrier_height = _positive(getattr(bridge, "barrier_height", 0.0))
    if barrier_height > 0.0 and length > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="barrier",
                quantity_kind="bridge_barrier_face_area",
                value=barrier_height * length * 2.0,
                unit="m2",
            )
        )
    approach_slab_length = _positive(getattr(bridge, "approach_slab_length", 0.0))
    if approach_slab_length > 0.0 and deck_width > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="approach-slab",
                quantity_kind="bridge_approach_slab_area",
                value=approach_slab_length * deck_width * 2.0,
                unit="m2",
            )
        )
    pier_refs = list(getattr(bridge, "pier_station_refs", []) or [])
    support_count = len([ref for ref in pier_refs if str(ref or "").strip()])
    if _positive(getattr(bridge, "abutment_start_offset", 0.0)) > 0.0 or _positive(getattr(bridge, "abutment_end_offset", 0.0)) > 0.0:
        support_count += 2
    if support_count > 0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="supports",
                quantity_kind="bridge_support_count",
                value=float(support_count),
                unit="ea",
            )
        )
    return rows


def _culvert_quantity_fragments(*, output_id: str, solid, culvert=None) -> list[QuantityFragment]:
    rows = [
        _structure_fragment(
            output_id=output_id,
            solid=solid,
            suffix="barrel",
            quantity_kind="culvert_barrel_volume",
            value=float(getattr(solid, "volume", 0.0) or 0.0),
            unit="m3",
        ),
        _structure_fragment(
            output_id=output_id,
            solid=solid,
            suffix="opening",
            quantity_kind="culvert_opening_area",
            value=_positive(getattr(solid, "width", 0.0)) * _positive(getattr(solid, "height", 0.0)),
            unit="m2",
        ),
    ]
    barrel_count = int(_positive(getattr(culvert, "barrel_count", 0.0)))
    if barrel_count > 0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="barrel-count",
                quantity_kind="culvert_barrel_count",
                value=float(barrel_count),
                unit="ea",
            )
        )
    wall_volume = _culvert_wall_volume(solid, culvert=culvert, barrel_count=barrel_count)
    if wall_volume > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="wall",
                quantity_kind="culvert_wall_volume",
                value=wall_volume,
                unit="m3",
            )
        )
    if str(getattr(culvert, "headwall_type", "") or "").strip():
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="headwall",
                quantity_kind="culvert_headwall_count",
                value=2.0,
                unit="ea",
            )
        )
    if str(getattr(culvert, "wingwall_type", "") or "").strip():
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="wingwall",
                quantity_kind="culvert_wingwall_count",
                value=4.0,
                unit="ea",
            )
        )
    return rows


def _retaining_wall_quantity_fragments(*, output_id: str, solid, wall=None) -> list[QuantityFragment]:
    rows = [
        _structure_fragment(
            output_id=output_id,
            solid=solid,
            suffix="body",
            quantity_kind="wall_body_volume",
            value=float(getattr(solid, "volume", 0.0) or 0.0),
            unit="m3",
        )
    ]
    length = _length(solid)
    footing_width = _positive(getattr(wall, "footing_width", 0.0))
    footing_thickness = _positive(getattr(wall, "footing_thickness", 0.0))
    if footing_width > 0.0 and footing_thickness > 0.0 and length > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="footing",
                quantity_kind="wall_footing_volume",
                value=footing_width * footing_thickness * length,
                unit="m3",
            )
        )
    wall_thickness = _positive(getattr(wall, "wall_thickness", 0.0), fallback=_positive(getattr(solid, "width", 0.0)))
    coping_height = _positive(getattr(wall, "coping_height", 0.0))
    if wall_thickness > 0.0 and coping_height > 0.0 and length > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="coping",
                quantity_kind="wall_coping_volume",
                value=wall_thickness * coping_height * length,
                unit="m3",
            )
        )
    if str(getattr(wall, "drainage_layer_ref", "") or "").strip() and length > 0.0:
        rows.append(
            _structure_fragment(
                output_id=output_id,
                solid=solid,
                suffix="drainage-layer",
                quantity_kind="wall_drainage_layer_length",
                value=length,
                unit="m",
            )
        )
    return rows


def _structure_fragment(
    *,
    output_id: str,
    solid,
    suffix: str,
    quantity_kind: str,
    value: float,
    unit: str,
) -> QuantityFragment:
    return QuantityFragment(
        fragment_id=f"{output_id}:quantity:{getattr(solid, 'output_object_id', '')}:{suffix}",
        quantity_kind=quantity_kind,
        measurement_kind="structure_solid_output",
        value=float(value or 0.0),
        unit=unit,
        station_start=getattr(solid, "station_start", None),
        station_end=getattr(solid, "station_end", None),
        component_ref="",
        structure_ref=str(getattr(solid, "structure_id", "") or ""),
    )


def _culvert_wall_volume(solid, *, culvert=None, barrel_count: int = 0) -> float:
    thickness = _positive(getattr(culvert, "wall_thickness", 0.0))
    length = _length(solid)
    count = max(int(barrel_count or 0), 1)
    if thickness <= 0.0 or length <= 0.0:
        return 0.0
    shape = str(getattr(culvert, "barrel_shape", "") or "").strip().lower()
    if shape == "circular":
        diameter = _positive(getattr(culvert, "diameter", 0.0), fallback=_positive(getattr(solid, "width", 0.0)))
        if diameter <= 0.0:
            return 0.0
        inner_radius = diameter / 2.0
        outer_radius = inner_radius + thickness
        return math.pi * (outer_radius * outer_radius - inner_radius * inner_radius) * length * count
    span = _positive(getattr(culvert, "span", 0.0), fallback=_positive(getattr(solid, "width", 0.0)))
    rise = _positive(getattr(culvert, "rise", 0.0), fallback=_positive(getattr(solid, "height", 0.0)))
    if span <= 0.0 or rise <= 0.0:
        return 0.0
    outer_area = (span + 2.0 * thickness) * (rise + 2.0 * thickness)
    inner_area = span * rise
    return max(outer_area - inner_area, 0.0) * length * count


def _length(solid) -> float:
    return _positive(getattr(solid, "length", 0.0))


def _first_ref(values) -> str:
    for value in list(values or []):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _unique_refs(values) -> list[str]:
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
    return str(value or "").strip().replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "-") or "unknown"


def _positive(value, *, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = float(fallback)
    if numeric <= 0.0:
        return float(fallback)
    return numeric
