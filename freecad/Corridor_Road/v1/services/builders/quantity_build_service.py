"""Quantity builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from ...common.identity import new_entity_id
from ...models.output.structure_solid_output import StructureSolidOutput
from ...models.source.structure_model import StructureModel
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


class QuantityBuildService:
    """Build quantity fragments and aggregates from applied sections."""

    def build(self, request: QuantityBuildRequest) -> QuantityModel:
        """Create a minimal quantity model from one applied section set."""

        fragment_rows: list[QuantityFragment] = []

        for section in request.applied_section_set.sections:
            fragment_rows.extend(self._fragment_rows_for_section(section))
            fragment_rows.extend(_side_slope_surface_fragment_rows(section))
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
            source_refs=[
                ref
                for ref in [
                    request.corridor.corridor_id,
                    request.applied_section_set.applied_section_set_id,
                    str(getattr(request.structure_solid_output, "structure_solid_output_id", "") or ""),
                ]
                if ref
            ],
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
                    component_ref=row.component_id,
                    assembly_ref=section.assembly_id,
                    region_ref=section.region_id,
                    structure_ref=self._structure_ref_for_component(section, row.component_id),
                )
                for row in section.quantity_rows
            ]

        return [
            QuantityFragment(
                fragment_id=new_entity_id("quantity_fragment"),
                quantity_kind=f"{component.kind}_count",
                measurement_kind="count",
                value=1.0,
                unit="ea",
                station_start=section.station,
                station_end=section.station,
                component_ref=component.component_id,
                assembly_ref=section.assembly_id,
                region_ref=section.region_id,
                structure_ref=_first_ref(component.structure_ids),
            )
            for component in section.component_rows
        ]

    def _structure_ref_for_component(
        self,
        section: AppliedSection,
        component_id: str,
    ) -> str:
        """Resolve the singular structure ref for one quantity fragment."""

        for component in section.component_rows:
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
            rows.append(
                QuantityFragment(
                    fragment_id=f"{section.applied_section_id}:quantity:{quantity_kind}:{side_label}:{index}",
                    quantity_kind=quantity_kind,
                    measurement_kind="section_side_slope_breakline",
                    value=length,
                    unit="m",
                    station_start=section.station,
                    station_end=section.station,
                    component_ref=str(getattr(end, "point_id", "") or ""),
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
        component_ref=str(getattr(solid, "output_object_id", "") or ""),
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


def _positive(value, *, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = float(fallback)
    if numeric <= 0.0:
        return float(fallback)
    return numeric
