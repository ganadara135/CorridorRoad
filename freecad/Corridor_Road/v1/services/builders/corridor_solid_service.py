"""Corridor solid builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models.output.structure_solid_output import (
    StructureExportDiagnosticRow,
    StructureSolidOutput,
    StructureSolidOutputRow,
    StructureSolidSegmentRow,
)
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.source.structure_model import StructureGeometrySpec, StructureModel, StructureRow


@dataclass(frozen=True)
class StructureSolidBuildRequest:
    """Input bundle for building normalized corridor structure solid outputs."""

    project_id: str
    corridor: CorridorModel
    structure_model: StructureModel
    applied_section_set: AppliedSectionSet | None = None
    active_structure_refs: list[str] = field(default_factory=list)
    structure_solid_output_id: str = "structure-solids:main"


class StructureSolidOutputService:
    """Build first-slice structure solid output rows from v1 source specs."""

    def build(self, request: StructureSolidBuildRequest) -> StructureSolidOutput:
        """Create normalized bridge, culvert, wall, and envelope output rows."""

        geometry_by_id = {
            str(row.geometry_spec_id): row
            for row in list(getattr(request.structure_model, "geometry_spec_rows", []) or [])
        }
        bridge_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(request.structure_model, "bridge_geometry_spec_rows", []) or [])
        }
        culvert_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(request.structure_model, "culvert_geometry_spec_rows", []) or [])
        }
        wall_by_ref = {
            str(row.geometry_spec_ref): row
            for row in list(getattr(request.structure_model, "retaining_wall_geometry_spec_rows", []) or [])
        }

        solid_rows: list[StructureSolidOutputRow] = []
        solid_segment_rows: list[StructureSolidSegmentRow] = []
        diagnostics: list[StructureExportDiagnosticRow] = []
        path_source = _path_source(request.applied_section_set)
        active_structure_refs = _active_structure_refs(
            request.applied_section_set,
            explicit_refs=request.active_structure_refs,
        )
        active_structure_ref_set = set(active_structure_refs)
        for row in list(getattr(request.structure_model, "structure_rows", []) or []):
            structure_id = str(getattr(row, "structure_id", "") or "")
            if active_structure_ref_set and structure_id not in active_structure_ref_set:
                continue
            spec_ref = str(getattr(row, "geometry_spec_ref", "") or "")
            spec = geometry_by_id.get(spec_ref)
            if spec is None:
                diagnostics.append(_export_diagnostic(
                    "error",
                    "missing_structure_geometry_spec",
                    structure_id=str(getattr(row, "structure_id", "") or ""),
                    geometry_spec_id=spec_ref,
                    output_object_id="",
                    message=f"Structure {row.structure_id} cannot export because it has no native geometry spec.",
                ))
                continue
            solid_row = _solid_row_for_structure(
                row,
                spec,
                path_source=path_source,
                applied_section_set=request.applied_section_set,
                bridge=bridge_by_ref.get(spec_ref),
                culvert=culvert_by_ref.get(spec_ref),
                wall=wall_by_ref.get(spec_ref),
            )
            solid_rows.append(solid_row)
            solid_segment_rows.extend(
                _segment_rows_for_structure(
                    solid_row,
                    applied_section_set=request.applied_section_set,
                    offset=float(getattr(row.placement, "offset", 0.0) or 0.0),
                )
            )
        diagnostics.extend(
            _structure_export_readiness_diagnostics(
                solid_rows,
                solid_segment_rows,
                geometry_by_id=geometry_by_id,
                culvert_by_ref=culvert_by_ref,
            )
        )

        return StructureSolidOutput(
            schema_version=1,
            project_id=request.project_id,
            structure_solid_output_id=request.structure_solid_output_id,
            corridor_id=str(getattr(request.corridor, "corridor_id", "") or ""),
            structure_model_id=str(getattr(request.structure_model, "structure_model_id", "") or ""),
            applied_section_set_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
            label="Structure Solids",
            source_refs=_unique_refs(
                [
                    str(getattr(request.structure_model, "structure_model_id", "") or ""),
                    *active_structure_refs,
                    *_applied_section_source_refs(request.applied_section_set, active_structure_refs=active_structure_refs),
                ]
            ),
            result_refs=[
                ref
                for ref in [
                    str(getattr(request.corridor, "corridor_id", "") or ""),
                    str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                ]
                if ref
            ],
            solid_rows=solid_rows,
            solid_segment_rows=solid_segment_rows,
            diagnostic_rows=diagnostics,
        )


def _solid_row_for_structure(
    row: StructureRow,
    spec: StructureGeometrySpec,
    *,
    path_source: str,
    applied_section_set: AppliedSectionSet | None = None,
    bridge=None,
    culvert=None,
    wall=None,
) -> StructureSolidOutputRow:
    kind = str(getattr(row, "structure_kind", "") or "").strip().lower()
    station_start = float(getattr(row.placement, "station_start", 0.0) or 0.0)
    station_end = float(getattr(row.placement, "station_end", station_start) or station_start)
    if station_end < station_start:
        station_start, station_end = station_end, station_start
    length = max(station_end - station_start, 0.0)
    width = float(getattr(spec, "width", 0.0) or 0.0)
    height = float(getattr(spec, "height", 0.0) or 0.0)
    material = str(getattr(spec, "material", "") or "")
    notes = ""
    context = _source_context_for_structure(applied_section_set, str(row.structure_id))

    if kind == "bridge":
        solid_kind = "bridge_deck_solid"
        width = float(getattr(bridge, "deck_width", 0.0) or width)
        height = float(getattr(bridge, "deck_thickness", 0.0) or height)
    elif kind == "culvert":
        solid_kind = "culvert_body_solid"
        width = float(getattr(culvert, "span", 0.0) or getattr(culvert, "diameter", 0.0) or width)
        height = float(getattr(culvert, "rise", 0.0) or getattr(culvert, "diameter", 0.0) or height)
        if culvert is not None and not float(getattr(culvert, "length", 0.0) or 0.0):
            notes = "Length derived from placement station range."
    elif kind in {"retaining_wall", "wall"}:
        solid_kind = "retaining_wall_solid"
        width = float(getattr(wall, "wall_thickness", 0.0) or width)
        height = float(getattr(wall, "wall_height", 0.0) or height)
    else:
        solid_kind = "structure_envelope_solid"

    volume = max(width, 0.0) * max(height, 0.0) * max(length, 0.0)
    offset = float(getattr(row.placement, "offset", 0.0) or 0.0)
    start_x, start_y, start_z, start_tangent_direction_deg = _placement_from_applied_sections(
        applied_section_set,
        station=station_start,
        offset=offset,
    )
    end_x, end_y, end_z, end_tangent_direction_deg = _placement_from_applied_sections(
        applied_section_set,
        station=station_end,
        offset=offset,
    )
    return StructureSolidOutputRow(
        output_object_id=f"structure-solid:{row.structure_id}",
        structure_id=str(row.structure_id),
        geometry_spec_id=str(spec.geometry_spec_id),
        solid_kind=solid_kind,
        station_start=station_start,
        station_end=station_end,
        path_source=path_source,
        material=material,
        width=max(width, 0.0),
        height=max(height, 0.0),
        length=length,
        volume=volume,
        placement_x=start_x,
        placement_y=start_y,
        placement_z=start_z,
        tangent_direction_deg=start_tangent_direction_deg,
        start_x=start_x,
        start_y=start_y,
        start_z=start_z,
        end_x=end_x,
        end_y=end_y,
        end_z=end_z,
        start_tangent_direction_deg=start_tangent_direction_deg,
        end_tangent_direction_deg=end_tangent_direction_deg,
        region_ref=context["region_ref"],
        assembly_ref=context["assembly_ref"],
        structure_ref=context["structure_ref"],
        source_ref=str(row.structure_id),
        notes=notes,
    )


def _path_source(applied_section_set: AppliedSectionSet | None) -> str:
    if applied_section_set is None:
        return "station_range"
    sections = list(getattr(applied_section_set, "sections", []) or [])
    if any(getattr(section, "frame", None) is not None for section in sections):
        return "3d_centerline"
    return "station_range"


def _active_structure_refs(
    applied_section_set: AppliedSectionSet | None,
    *,
    explicit_refs: list[str] | None = None,
) -> list[str]:
    """Return singular active Structure refs carried by Applied Sections."""

    refs: list[str] = []
    refs.extend(list(explicit_refs or []))
    if applied_section_set is not None:
        for section in list(getattr(applied_section_set, "sections", []) or []):
            ref = _first_section_structure_ref(section)
            if ref:
                refs.append(ref)
    output: list[str] = []
    seen: set[str] = set()
    for value in refs:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _applied_section_source_refs(
    applied_section_set: AppliedSectionSet | None,
    *,
    active_structure_refs: list[str],
) -> list[str]:
    refs: list[str] = []
    active_set = {str(value or "").strip() for value in list(active_structure_refs or []) if str(value or "").strip()}
    for section in list(getattr(applied_section_set, "sections", []) or []) if applied_section_set is not None else []:
        if active_set and not any(_section_has_structure(section, ref) for ref in active_set):
            continue
        refs.extend(
            [
                str(getattr(section, "region_id", "") or ""),
                str(getattr(section, "assembly_id", "") or ""),
            ]
        )
    return _unique_refs(refs)


def _source_context_for_structure(applied_section_set: AppliedSectionSet | None, structure_id: str) -> dict[str, str]:
    structure_ref = str(structure_id or "").strip()
    for section in list(getattr(applied_section_set, "sections", []) or []) if applied_section_set is not None else []:
        if not _section_has_structure(section, structure_ref):
            continue
        return {
            "region_ref": str(getattr(section, "region_id", "") or ""),
            "assembly_ref": str(getattr(section, "assembly_id", "") or ""),
            "structure_ref": structure_ref,
        }
    return {"region_ref": "", "assembly_ref": "", "structure_ref": structure_ref}


def _section_has_structure(section, structure_ref: str) -> bool:
    expected = str(structure_ref or "").strip()
    if not expected:
        return False
    for value in list(getattr(section, "active_structure_ids", []) or []):
        if str(value or "").strip() == expected:
            return True
    for component in list(getattr(section, "component_rows", []) or []):
        for value in list(getattr(component, "structure_ids", []) or []):
            if str(value or "").strip() == expected:
                return True
    return False


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


def _first_section_structure_ref(section) -> str:
    for value in list(getattr(section, "active_structure_ids", []) or []):
        text = str(value or "").strip()
        if text:
            return text
    for component in list(getattr(section, "component_rows", []) or []):
        for value in list(getattr(component, "structure_ids", []) or []):
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _structure_export_readiness_diagnostics(
    solid_rows: list[StructureSolidOutputRow],
    solid_segment_rows: list[StructureSolidSegmentRow],
    *,
    geometry_by_id: dict[str, StructureGeometrySpec],
    culvert_by_ref: dict[str, object],
) -> list[StructureExportDiagnosticRow]:
    diagnostics: list[StructureExportDiagnosticRow] = []
    segments_by_parent: dict[str, list[StructureSolidSegmentRow]] = {}
    for segment in list(solid_segment_rows or []):
        parent = str(getattr(segment, "parent_output_object_id", "") or "")
        if parent:
            segments_by_parent.setdefault(parent, []).append(segment)
    for row in list(solid_rows or []):
        output_object_id = str(getattr(row, "output_object_id", "") or "")
        structure_id = str(getattr(row, "structure_id", "") or "")
        geometry_spec_id = str(getattr(row, "geometry_spec_id", "") or "")
        spec = geometry_by_id.get(geometry_spec_id)
        if float(getattr(row, "width", 0.0) or 0.0) <= 0.0 or float(getattr(row, "height", 0.0) or 0.0) <= 0.0:
            diagnostics.append(
                _export_diagnostic(
                    "error",
                    "missing_or_invalid_dimensions",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="Structure output width and height must be greater than zero before IFC export.",
                )
            )
        if float(getattr(row, "length", 0.0) or 0.0) <= 0.0:
            diagnostics.append(
                _export_diagnostic(
                    "error",
                    "zero_length",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="Structure output length must be greater than zero before IFC export.",
                )
            )
        if str(getattr(row, "path_source", "") or "") != "3d_centerline":
            diagnostics.append(
                _export_diagnostic(
                    "warning",
                    "missing_frame_context",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="Structure output is not tied to AppliedSection frame context and will export from station-range fallback coordinates.",
                )
            )
        if spec is not None and abs(float(getattr(spec, "skew_angle_deg", 0.0) or 0.0)) > 1.0e-9:
            diagnostics.append(
                _export_diagnostic(
                    "warning",
                    "unsupported_skew",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="Structure skew is recorded in source geometry but is not applied to the current IFC swept solid.",
                    notes=f"skew_angle_deg={float(getattr(spec, 'skew_angle_deg', 0.0) or 0.0):.6f}",
                )
            )
        culvert = culvert_by_ref.get(geometry_spec_id)
        if culvert is not None:
            inlet_skew = float(getattr(culvert, "inlet_skew_angle_deg", 0.0) or 0.0)
            outlet_skew = float(getattr(culvert, "outlet_skew_angle_deg", 0.0) or 0.0)
            if abs(inlet_skew) > 1.0e-9 or abs(outlet_skew) > 1.0e-9:
                diagnostics.append(
                    _export_diagnostic(
                        "warning",
                        "unsupported_skew",
                        structure_id=structure_id,
                        geometry_spec_id=geometry_spec_id,
                        output_object_id=output_object_id,
                        message="Culvert inlet/outlet skew is recorded in source geometry but is not applied to the current IFC swept solid.",
                        notes=f"inlet_skew_angle_deg={inlet_skew:.6f};outlet_skew_angle_deg={outlet_skew:.6f}",
                    )
                )
        segment_count = len(segments_by_parent.get(output_object_id, []))
        if segment_count > 1:
            diagnostics.append(
                _export_diagnostic(
                    "info",
                    "ifc_segmented_proxy_geometry",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="IFC export will use multiple swept solid segments under an IfcBuildingElementProxy handoff.",
                    notes=f"segment_count={segment_count}",
                )
            )
        else:
            diagnostics.append(
                _export_diagnostic(
                    "warning",
                    "simplified_ifc_geometry",
                    structure_id=structure_id,
                    geometry_spec_id=geometry_spec_id,
                    output_object_id=output_object_id,
                    message="IFC export will use a simplified rectangular swept solid proxy for this structure.",
                    notes=f"segment_count={segment_count}",
                )
            )
    return diagnostics


def _export_diagnostic(
    severity: str,
    kind: str,
    *,
    structure_id: str,
    geometry_spec_id: str,
    output_object_id: str,
    message: str,
    notes: str = "",
) -> StructureExportDiagnosticRow:
    safe_structure = structure_id or "structure"
    safe_output = output_object_id or "output"
    return StructureExportDiagnosticRow(
        diagnostic_id=f"structure-export:{kind}:{safe_structure}:{safe_output}",
        severity=severity,
        kind=kind,
        structure_id=structure_id,
        geometry_spec_id=geometry_spec_id,
        output_object_id=output_object_id,
        message=message,
        notes=notes,
    )


def _segment_rows_for_structure(
    solid_row: StructureSolidOutputRow,
    *,
    applied_section_set: AppliedSectionSet | None,
    offset: float = 0.0,
) -> list[StructureSolidSegmentRow]:
    stations = _segment_stations(
        applied_section_set,
        station_start=float(getattr(solid_row, "station_start", 0.0) or 0.0),
        station_end=float(getattr(solid_row, "station_end", 0.0) or 0.0),
    )
    rows: list[StructureSolidSegmentRow] = []
    total_length = max(float(getattr(solid_row, "length", 0.0) or 0.0), 0.0)
    total_volume = max(float(getattr(solid_row, "volume", 0.0) or 0.0), 0.0)
    for index, (start_station, end_station) in enumerate(zip(stations, stations[1:]), start=1):
        segment_length = max(float(end_station - start_station), 0.0)
        if segment_length <= 0.0:
            continue
        start_x, start_y, start_z, start_tangent = _placement_from_applied_sections(
            applied_section_set,
            station=start_station,
            offset=offset,
        )
        end_x, end_y, end_z, end_tangent = _placement_from_applied_sections(
            applied_section_set,
            station=end_station,
            offset=offset,
        )
        volume = total_volume * (segment_length / total_length) if total_length > 0.0 else 0.0
        rows.append(
            StructureSolidSegmentRow(
                segment_id=f"{solid_row.output_object_id}:segment:{index}",
                parent_output_object_id=str(solid_row.output_object_id),
                structure_id=str(solid_row.structure_id),
                geometry_spec_id=str(solid_row.geometry_spec_id),
                segment_index=index,
                station_start=float(start_station),
                station_end=float(end_station),
                start_x=start_x,
                start_y=start_y,
                start_z=start_z,
                end_x=end_x,
                end_y=end_y,
                end_z=end_z,
                start_tangent_direction_deg=start_tangent,
                end_tangent_direction_deg=end_tangent,
                path_source=str(solid_row.path_source),
                width=float(solid_row.width),
                height=float(solid_row.height),
                length=segment_length,
                volume=volume,
                region_ref=str(solid_row.region_ref),
                assembly_ref=str(solid_row.assembly_ref),
                structure_ref=str(solid_row.structure_ref),
                notes="single_segment" if len(stations) <= 2 else "frame_segment",
            )
        )
    return rows


def _segment_stations(
    applied_section_set: AppliedSectionSet | None,
    *,
    station_start: float,
    station_end: float,
) -> list[float]:
    if station_end < station_start:
        station_start, station_end = station_end, station_start
    stations = [float(station_start), float(station_end)]
    if applied_section_set is not None:
        for section in list(getattr(applied_section_set, "sections", []) or []):
            frame = getattr(section, "frame", None)
            if frame is None:
                continue
            station = float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
            if station_start < station < station_end:
                stations.append(station)
    ordered: list[float] = []
    seen: set[float] = set()
    for station in sorted(stations):
        key = round(float(station), 9)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(float(station))
    return ordered


def _placement_from_applied_sections(
    applied_section_set: AppliedSectionSet | None,
    *,
    station: float,
    offset: float = 0.0,
) -> tuple[float, float, float, float]:
    frame = _interpolated_frame(applied_section_set, station=station)
    if frame is None:
        return float(station or 0.0), float(offset or 0.0), 0.0, 0.0
    tangent = float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0)
    theta = math.radians(tangent)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    return (
        base_x - math.sin(theta) * float(offset or 0.0),
        base_y + math.cos(theta) * float(offset or 0.0),
        float(getattr(frame, "z", 0.0) or 0.0),
        tangent,
    )


def _interpolated_frame(applied_section_set: AppliedSectionSet | None, *, station: float):
    if applied_section_set is None:
        return None
    frames = [
        section.frame
        for section in list(getattr(applied_section_set, "sections", []) or [])
        if getattr(section, "frame", None) is not None
    ]
    if not frames:
        return None
    frames = sorted(frames, key=lambda frame: float(getattr(frame, "station", 0.0) or 0.0))
    target = float(station or 0.0)
    if target <= float(getattr(frames[0], "station", 0.0) or 0.0):
        return frames[0]
    if target >= float(getattr(frames[-1], "station", 0.0) or 0.0):
        return frames[-1]
    for left, right in zip(frames, frames[1:]):
        left_station = float(getattr(left, "station", 0.0) or 0.0)
        right_station = float(getattr(right, "station", left_station) or left_station)
        if target < left_station or target > right_station:
            continue
        span = right_station - left_station
        ratio = 0.0 if abs(span) < 1.0e-12 else (target - left_station) / span
        return _InterpolatedFrame(
            station=target,
            x=_lerp(float(getattr(left, "x", 0.0) or 0.0), float(getattr(right, "x", 0.0) or 0.0), ratio),
            y=_lerp(float(getattr(left, "y", 0.0) or 0.0), float(getattr(right, "y", 0.0) or 0.0), ratio),
            z=_lerp(float(getattr(left, "z", 0.0) or 0.0), float(getattr(right, "z", 0.0) or 0.0), ratio),
            tangent_direction_deg=_lerp(
                float(getattr(left, "tangent_direction_deg", 0.0) or 0.0),
                float(getattr(right, "tangent_direction_deg", 0.0) or 0.0),
                ratio,
            ),
        )
    return frames[0]


@dataclass(frozen=True)
class _InterpolatedFrame:
    station: float
    x: float
    y: float
    z: float
    tangent_direction_deg: float


def _lerp(start: float, end: float, ratio: float) -> float:
    return start + (end - start) * ratio
