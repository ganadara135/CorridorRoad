"""Watertight solid target discovery service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.source.drainage_model import DrainageModel
from ...models.source.intersection_model import IntersectionModel
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from ...models.source.solid_target_model import (
    SolidTargetDiagnosticRow,
    SolidTargetModel,
    SolidTargetRow,
)
from ..evaluation.drainage_resolution_service import build_drainage_pipeline_result
from ..evaluation.intersection_evaluation_service import IntersectionEvaluationService
from ..evaluation.station_context_resolver import StationContextResolver


@dataclass(frozen=True)
class SolidTargetDiscoveryRequest:
    """Input context for discovering watertight solid target candidates."""

    project_id: str = "corridorroad-v1"
    corridor_ref: str = "corridor:main"
    applied_section_set: AppliedSectionSet | None = None
    corridor_model: CorridorModel | None = None
    region_model: RegionModel | None = None
    intersection_model: IntersectionModel | None = None
    structure_model: StructureModel | None = None
    drainage_model: DrainageModel | None = None


class SolidTargetDiscoveryService:
    """Discover topology-first watertight solid target candidates from v1 results."""

    def discover(self, request: SolidTargetDiscoveryRequest) -> SolidTargetModel:
        applied = request.applied_section_set
        corridor = request.corridor_model
        region_model = request.region_model
        intersection_model = request.intersection_model
        structure_model = request.structure_model
        drainage_model = request.drainage_model
        diagnostics: list[SolidTargetDiagnosticRow] = []
        target_rows: list[SolidTargetRow] = []
        station_start, station_end, station_count = _station_range(applied)
        corridor_ref = str(request.corridor_ref or getattr(corridor, "corridor_id", "") or "corridor:main")
        source_refs = _source_refs(applied, corridor)

        if applied is None:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_applied_sections",
                    "solid-target:road-body-envelope",
                    "Applied Sections are required before watertight solid target discovery.",
                )
            )
        if corridor is None:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_corridor_model",
                    "solid-target:road-body-envelope",
                    "Build Corridor must create a CorridorModel before watertight solid target discovery.",
                )
            )
        if applied is not None and station_count < 2:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "insufficient_station_profiles",
                    "solid-target:road-body-envelope",
                    "At least two Applied Section stations are required to discover a road body envelope target.",
                )
            )

        road_ready = applied is not None and corridor is not None and station_count >= 2
        road_diag_refs = [
            row.diagnostic_id
            for row in diagnostics
            if row.source_ref == "solid-target:road-body-envelope" and row.severity == "error"
        ]
        target_rows.append(
            SolidTargetRow(
                target_id="solid-target:road-body-envelope",
                target_family="road_body_envelope",
                scope_kind="whole_corridor",
                station_start=station_start,
                station_end=station_end,
                enabled=False,
                readiness_status="available" if road_ready else "blocked",
                source_refs=source_refs,
                diagnostic_refs=road_diag_refs,
                notes="Whole-corridor envelope target discovered from Applied Sections and CorridorModel.",
            )
        )

        if region_model is not None:
            region_rows, region_diagnostics = _region_target_rows(
                region_model,
                applied=applied,
                structure_model=structure_model,
                drainage_model=drainage_model,
                source_refs=source_refs,
            )
            target_rows.extend(region_rows)
            diagnostics.extend(region_diagnostics)

        intersection_rows, intersection_diagnostics = _intersection_patch_target_rows(
            intersection_model,
            applied=applied,
            source_refs=source_refs,
        )
        target_rows.extend(intersection_rows)
        diagnostics.extend(intersection_diagnostics)

        intersection_zone_rows, intersection_zone_diagnostics = _intersection_surface_zone_target_rows(
            intersection_model,
            source_refs=source_refs,
        )
        target_rows.extend(intersection_zone_rows)
        diagnostics.extend(intersection_zone_diagnostics)

        subassembly_rows, subassembly_diagnostics = _subassembly_target_rows(
            applied,
            source_refs=source_refs,
        )
        target_rows.extend(subassembly_rows)
        diagnostics.extend(subassembly_diagnostics)

        lined_ditch_rows, lined_ditch_diagnostics = _lined_ditch_target_rows(
            applied,
            region_model=region_model,
            drainage_model=drainage_model,
            source_refs=source_refs,
        )
        target_rows.extend(lined_ditch_rows)
        diagnostics.extend(lined_ditch_diagnostics)

        pipeline_rows, pipeline_diagnostics = _drainage_pipeline_target_rows(
            drainage_model,
            structure_model=structure_model,
            source_refs=source_refs,
        )
        target_rows.extend(pipeline_rows)
        diagnostics.extend(pipeline_diagnostics)

        structure_rows, structure_diagnostics = _structure_target_rows(
            structure_model,
            source_refs=source_refs,
        )
        target_rows.extend(structure_rows)
        diagnostics.extend(structure_diagnostics)

        return SolidTargetModel(
            schema_version=1,
            project_id=str(request.project_id or "corridorroad-v1"),
            solid_target_model_id="solid-targets:main",
            corridor_ref=corridor_ref,
            label="Watertight Solid Targets",
            target_rows=target_rows,
            target_diagnostic_rows=diagnostics,
            source_refs=source_refs,
        )


def _region_target_rows(
    region_model: RegionModel,
    *,
    applied: AppliedSectionSet | None,
    structure_model: StructureModel | None = None,
    drainage_model: DrainageModel | None = None,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    station_min, station_max, station_count = _station_range(applied)
    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for region in list(getattr(region_model, "region_rows", []) or []):
        region_id = str(getattr(region, "region_id", "") or "").strip()
        if not region_id:
            continue
        start = float(getattr(region, "station_start", 0.0) or 0.0)
        end = float(getattr(region, "station_end", 0.0) or 0.0)
        overlaps = applied is not None and station_count >= 2 and end >= station_min and start <= station_max and start < end
        diagnostic_refs: list[str] = []
        if not overlaps:
            diagnostic = _diagnostic(
                "error",
                "region_target_range_not_ready",
                f"solid-target:region-body:{_safe_id(region_id)}",
                f"Region {region_id} does not overlap a usable Applied Section station range.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        station_context_summary = _station_context_summary_for_range(
            applied,
            region_model=region_model,
            structure_model=structure_model,
            drainage_model=drainage_model,
            station_start=start,
            station_end=end,
            region_ref=region_id,
        )
        notes = "Region-scoped body target discovered from RegionModel and base Assembly only."
        if station_context_summary:
            notes = f"{notes} StationContext: {station_context_summary}."
        rows.append(
            SolidTargetRow(
                target_id=f"solid-target:region-body:{_safe_id(region_id)}",
                target_family="region_body",
                scope_kind="region",
                station_start=start,
                station_end=end,
                region_ref=region_id,
                assembly_ref=str(getattr(region, "assembly_ref", "") or ""),
                enabled=False,
                readiness_status="available" if overlaps else "blocked",
                source_refs=source_refs + [region_id],
                diagnostic_refs=diagnostic_refs,
                notes=notes,
            )
        )
    return rows, diagnostics


def _intersection_surface_zone_target_rows(
    intersection_model: IntersectionModel | None,
    *,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if intersection_model is None:
        return [], []
    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    service = IntersectionEvaluationService()
    for intersection in list(getattr(intersection_model, "intersection_rows", []) or []):
        intersection_id = str(getattr(intersection, "intersection_id", "") or "").strip()
        if not intersection_id:
            continue
        surface_zones = service.evaluate_surface_zones(intersection_model, intersection_id=intersection_id)
        if str(getattr(surface_zones, "status", "") or "") == "error":
            target_id = f"solid-target:intersection-zone:{_safe_id(intersection_id)}"
            diagnostics.append(
                _diagnostic(
                    "error",
                    "intersection_surface_zone_target_contract_error",
                    target_id,
                    "Intersection surface-zone contracts must be ready before zone-scoped watertight targets can be discovered.",
                    notes="; ".join(str(row) for row in list(getattr(surface_zones, "diagnostic_rows", []) or []) if str(row)),
                )
            )
            continue
        station_start, station_end = _intersection_station_range(intersection_model, intersection_id)
        control_refs = _intersection_control_region_refs(intersection_model, intersection)
        for zone in list(getattr(surface_zones, "zone_rows", []) or []):
            target_families = _intersection_zone_target_families(zone)
            if not target_families:
                continue
            zone_id = str(getattr(zone, "zone_id", "") or "").strip()
            zone_token = _safe_id(zone_id or str(getattr(zone, "zone_role", "") or "zone"))
            zone_status = str(getattr(zone, "status", "") or "").strip().lower()
            readiness = "planned" if zone_status in {"candidate", "ready", "warning", "warn"} else "blocked"
            diagnostic_refs: list[str] = []
            if readiness == "blocked":
                diagnostic = _diagnostic(
                    "error",
                    "intersection_surface_zone_target_not_ready",
                    f"solid-target:intersection-zone:{_safe_id(intersection_id)}:{zone_token}",
                    "Intersection surface-zone target is blocked because the source zone is not ready.",
                    notes=f"zone={zone_id};status={zone_status or '-'}",
                )
                diagnostics.append(diagnostic)
                diagnostic_refs.append(diagnostic.diagnostic_id)
            for family in target_families:
                family_token = _intersection_zone_target_family_token(family)
                target_id = f"solid-target:{family_token}:{_safe_id(intersection_id)}:{zone_token}"
                rows.append(
                    SolidTargetRow(
                        target_id=target_id,
                        target_family=family,
                        scope_kind="intersection",
                        station_start=station_start,
                        station_end=station_end,
                        region_ref=",".join(control_refs),
                        enabled=False,
                        readiness_status=readiness,
                        source_refs=_unique_refs(
                            source_refs
                            + [
                                str(getattr(intersection_model, "intersection_model_id", "") or ""),
                                intersection_id,
                                zone_id,
                                *list(getattr(zone, "source_edge_refs", ()) or ()),
                                *list(getattr(zone, "boundary_edge_refs", ()) or ()),
                                *list(getattr(zone, "control_area_refs", ()) or ()),
                            ]
                        ),
                        diagnostic_refs=diagnostic_refs,
                        notes=(
                            "Intersection surface-zone watertight target handoff. "
                            f"intersection={intersection_id}; "
                            f"zone={zone_id}; "
                            f"zone_family={str(getattr(zone, 'zone_family', '') or '')}; "
                            f"design_zone_role={str(getattr(zone, 'design_zone_role', '') or '')}; "
                            f"surface_role={str(getattr(zone, 'surface_role', '') or '')}; "
                            "build_backend=planned_edge_network_zone_solid."
                        ),
                    )
                )
    return rows, diagnostics


def _intersection_zone_target_families(zone: object) -> tuple[str, ...]:
    zone_family = str(getattr(zone, "zone_family", "") or "").strip().lower()
    design_role = str(getattr(zone, "design_zone_role", "") or "").strip().lower()
    if zone_family == "curb_return" or design_role == "curb_return_pavement":
        return ("intersection_curb_return_body", "intersection_subgrade_body")
    if zone_family == "slope" or design_role == "exterior_slope_face":
        return ("intersection_slope_body",)
    if design_role in {"central_pavement", "main_pavement", "side_pavement"} or zone_family in {"central_junction", "leg_pavement"}:
        return ("intersection_pavement_body", "intersection_subgrade_body")
    return ()


def _intersection_zone_target_family_token(family: str) -> str:
    text = str(family or "").strip().lower().replace("_body", "").replace("_", "-")
    return text or "intersection-zone"


def _structure_target_rows(
    structure_model: StructureModel | None,
    *,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if structure_model is None:
        return [], []
    geometry_by_id = {
        str(getattr(row, "geometry_spec_id", "") or ""): row
        for row in list(getattr(structure_model, "geometry_spec_rows", []) or [])
        if str(getattr(row, "geometry_spec_id", "") or "")
    }
    connection_points_by_structure: dict[str, list[object]] = {}
    for point in list(getattr(structure_model, "connection_point_rows", []) or []):
        structure_ref = str(getattr(point, "structure_ref", "") or "").strip()
        if structure_ref:
            connection_points_by_structure.setdefault(structure_ref, []).append(point)
    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for structure in list(getattr(structure_model, "structure_rows", []) or []):
        structure_id = str(getattr(structure, "structure_id", "") or "").strip()
        if not structure_id:
            continue
        placement = getattr(structure, "placement", None)
        start = float(getattr(placement, "station_start", 0.0) or 0.0)
        end = float(getattr(placement, "station_end", start) or start)
        if end < start:
            start, end = end, start
        spec_ref = str(getattr(structure, "geometry_spec_ref", "") or "").strip()
        geometry_ref = str(getattr(structure, "geometry_ref", "") or "").strip()
        geometry_source_mode = _structure_geometry_source_mode(structure)
        spec = geometry_by_id.get(spec_ref)
        target_id = f"solid-target:structure-body:{_safe_id(structure_id)}"
        diagnostic_refs: list[str] = []
        connection_points = list(connection_points_by_structure.get(structure_id, []) or [])
        needs_external_connection_points = (
            geometry_source_mode == "external_ref"
            and _structure_requires_connection_points(structure)
        )
        ready = (
            (spec is not None or (geometry_source_mode == "external_ref" and bool(geometry_ref)))
            and end > start
            and (not needs_external_connection_points or bool(connection_points))
        )
        if spec is None and geometry_source_mode != "external_ref":
            diagnostic = _diagnostic(
                "error",
                "missing_structure_geometry_spec",
                target_id,
                f"Structure {structure_id} cannot produce a solid target without a native geometry spec.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        if geometry_source_mode == "external_ref" and not geometry_ref:
            diagnostic = _diagnostic(
                "error",
                "missing_structure_geometry_ref",
                target_id,
                f"Structure {structure_id} cannot produce an external solid target without a geometry_ref.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        if needs_external_connection_points and not connection_points:
            diagnostic = _diagnostic(
                "error",
                "missing_external_structure_connection_points",
                target_id,
                f"External Drainage-ready Structure {structure_id} needs at least one Structure connection point before it can be used as a solid target.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        if end <= start:
            diagnostic = _diagnostic(
                "error",
                "invalid_structure_station_range",
                target_id,
                f"Structure {structure_id} must have station_end greater than station_start.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family="structure_body",
                scope_kind="structure",
                station_start=start,
                station_end=end,
                structure_ref=structure_id,
                enabled=False,
                material_ref=str(getattr(spec, "material", "") or "") if spec is not None else "",
                readiness_status="available" if ready else "blocked",
                source_refs=source_refs + [str(getattr(structure_model, "structure_model_id", "") or ""), structure_id, spec_ref, geometry_ref],
                diagnostic_refs=diagnostic_refs,
                notes=(
                    "Structure body target discovered from StructureModel; "
                    f"structure_kind={str(getattr(structure, 'structure_kind', '') or '')}; "
                    f"geometry_source_mode={geometry_source_mode}; "
                    f"connection_point_count={len(connection_points)}."
                ),
            )
        )
    return rows, diagnostics


def _intersection_patch_target_rows(
    intersection_model: IntersectionModel | None,
    *,
    applied: AppliedSectionSet | None,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if intersection_model is None:
        return [], []
    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    sections = list(getattr(applied, "sections", []) or []) if applied is not None else []
    for intersection in list(getattr(intersection_model, "intersection_rows", []) or []):
        intersection_id = str(getattr(intersection, "intersection_id", "") or "").strip()
        if not intersection_id:
            continue
        target_id = f"solid-target:intersection-patch:{_safe_id(intersection_id)}"
        control_refs = _intersection_control_region_refs(intersection_model, intersection)
        station_start, station_end = _intersection_station_range(intersection_model, intersection_id)
        if station_end <= station_start:
            station_start, station_end, _station_count = _station_range(applied)
        section_count = _intersection_applied_section_count(sections, intersection_id, control_refs)
        diagnostic_refs: list[str] = []
        if section_count < 2:
            diagnostic = _diagnostic(
                "error",
                "intersection_patch_target_insufficient_sections",
                target_id,
                "Intersection patch solid target needs Applied Sections for at least two participating control Regions.",
                notes=f"intersection={intersection_id};control_regions={','.join(control_refs) or '-'};sections={section_count}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        ready = section_count >= 2
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family="intersection_patch_body",
                scope_kind="intersection",
                station_start=station_start,
                station_end=station_end,
                region_ref=",".join(control_refs),
                enabled=False,
                readiness_status="available" if ready else "blocked",
                source_refs=_unique_refs(
                    source_refs
                    + [
                        str(getattr(intersection_model, "intersection_model_id", "") or ""),
                        intersection_id,
                        *control_refs,
                        "intersection-patch-boundary:refined-preferred",
                    ]
                ),
                diagnostic_refs=diagnostic_refs,
                notes=(
                    "Intersection patch body target discovered from IntersectionModel control Regions. "
                    f"intersection={intersection_id}; kind={str(getattr(intersection, 'intersection_kind', '') or '')}; "
                    f"control_regions={len(control_refs)}; applied_sections={section_count}; "
                    "boundary_source=refined_patch_boundary_preferred; build_backend=thin_patch_prism."
                ),
            )
        )
    return rows, diagnostics


def _subassembly_target_rows(
    applied: AppliedSectionSet | None,
    *,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if applied is None:
        return [], []
    subassembly_targets: dict[tuple[str, str], dict[str, object]] = {}
    for section in list(getattr(applied, "sections", []) or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        source_rows = _section_subassembly_rows(section)
        for source_row in source_rows:
            kind = str(getattr(source_row, "kind", "") or "").strip().lower()
            family = _subassembly_target_family(kind)
            if not family:
                continue
            subassembly_ref = str(getattr(source_row, "subassembly_id", "") or "").strip()
            if not subassembly_ref:
                continue
            width = max(float(getattr(source_row, "width", 0.0) or 0.0), 0.0)
            thickness = max(float(getattr(source_row, "thickness", 0.0) or 0.0), 0.0)
            owner_ref = subassembly_ref
            key = (family, owner_ref)
            data = subassembly_targets.setdefault(
                key,
                {
                    "stations": [],
                    "kind": kind,
                    "family": family,
                    "material": str(getattr(source_row, "material", "") or ""),
                    "region_refs": [],
                    "assembly_refs": [],
                    "subassembly_refs": [],
                    "invalid_dimension_stations": [],
                },
            )
            data["stations"].append(station)
            data["region_refs"].append(str(getattr(source_row, "region_id", "") or getattr(section, "region_id", "") or ""))
            data["assembly_refs"].append(str(getattr(section, "assembly_id", "") or ""))
            data["subassembly_refs"].append(subassembly_ref)
            if width <= 0.0 or thickness <= 0.0:
                data["invalid_dimension_stations"].append(station)
            if not str(data.get("material", "") or ""):
                data["material"] = str(getattr(source_row, "material", "") or "")
        for shape in list(getattr(section, "subassembly_shape_rows", []) or []):
            family = _subassembly_target_family_for_solid_family(getattr(shape, "solid_family", ""))
            if not family:
                continue
            subassembly_ref = str(getattr(shape, "subassembly_ref", "") or "").strip()
            if not subassembly_ref:
                continue
            shape_id = str(getattr(shape, "shape_id", "") or "").strip()
            owner_ref = subassembly_ref
            key = (family, owner_ref)
            data = subassembly_targets.setdefault(
                key,
                {
                    "stations": [],
                    "kind": str(getattr(shape, "solid_family", "") or getattr(shape, "shape_code", "") or "shape"),
                    "family": family,
                    "material": str(getattr(shape, "material", "") or ""),
                    "region_refs": [],
                    "assembly_refs": [],
                    "subassembly_refs": [],
                    "shape_refs": [],
                    "invalid_dimension_stations": [],
                    "invalid_shape_stations": [],
                },
            )
            data["stations"].append(station)
            data["region_refs"].append(str(getattr(section, "region_id", "") or ""))
            data["assembly_refs"].append(str(getattr(section, "assembly_id", "") or ""))
            data["subassembly_refs"].append(subassembly_ref)
            data.setdefault("shape_refs", []).append(shape_id)
            if len(list(getattr(shape, "point_refs", []) or [])) < 3:
                data.setdefault("invalid_shape_stations", []).append(station)
            if not str(data.get("material", "") or ""):
                data["material"] = str(getattr(shape, "material", "") or "")

    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for (family, owner_ref), data in sorted(subassembly_targets.items()):
        stations = sorted(float(value) for value in list(data.get("stations", []) or []))
        station_count = len(set(round(value, 6) for value in stations))
        subassembly_refs = _unique_refs(list(data.get("subassembly_refs", []) or []))
        active_ref = _single_ref(subassembly_refs) or str(owner_ref or "")
        target_prefix = _subassembly_target_prefix(family)
        target_id = f"solid-target:{target_prefix}:{_safe_id(active_ref)}"
        diagnostic_refs: list[str] = []
        if station_count < 2:
            diagnostic = _diagnostic(
                "error",
                "subassembly_target_insufficient_profiles",
                target_id,
                f"Subassembly {active_ref} needs at least two Applied Section profiles before it can become a solid target.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        invalid_stations = _unique_sorted_floats(list(data.get("invalid_dimension_stations", []) or []))
        if invalid_stations:
            diagnostic = _diagnostic(
                "error",
                "subassembly_target_invalid_dimensions",
                target_id,
                f"Subassembly {active_ref} needs positive width and thickness at every target station.",
                notes=f"stations={','.join(f'{station:g}' for station in invalid_stations)}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        invalid_shape_stations = _unique_sorted_floats(list(data.get("invalid_shape_stations", []) or []))
        if invalid_shape_stations:
            diagnostic = _diagnostic(
                "error",
                "subassembly_shape_target_invalid_profile",
                target_id,
                f"Subassembly {active_ref} needs closed shape profiles with at least three points at every target station.",
                notes=f"stations={','.join(f'{station:g}' for station in invalid_shape_stations)}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        shape_refs = _unique_refs(list(data.get("shape_refs", []) or []))
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family=family,
                scope_kind="assembly_subassembly",
                station_start=min(stations) if stations else 0.0,
                station_end=max(stations) if stations else 0.0,
                region_ref=_single_ref(data.get("region_refs", [])),
                assembly_ref=_single_ref(data.get("assembly_refs", [])),
                subassembly_ref=_single_ref(subassembly_refs),
                enabled=False,
                material_ref=str(data.get("material", "") or ""),
                readiness_status="available" if station_count >= 2 and not invalid_stations and not invalid_shape_stations else "blocked",
                source_refs=_unique_refs(source_refs + subassembly_refs + shape_refs),
                diagnostic_refs=diagnostic_refs,
                notes=(
                    f"{_subassembly_target_label(family)} target discovered from Applied Section Subassembly rows; "
                    f"subassembly_refs={_join_refs(subassembly_refs) or '-'}; "
                    f"shape_refs={_join_refs(shape_refs) or '-'}; "
                    f"source_kind={data.get('kind', '')}."
                ),
            )
        )
    return rows, diagnostics


def _lined_ditch_target_rows(
    applied: AppliedSectionSet | None,
    *,
    region_model: RegionModel | None = None,
    drainage_model: DrainageModel | None = None,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if applied is None:
        return [], []
    surface_stations_by_side: dict[str, list[float]] = {"left": [], "right": []}
    ditch_data_by_side: dict[str, dict[str, object]] = {"left": {}, "right": {}}
    drainage_owner_by_side = _drainage_lined_ditch_owner_by_side(drainage_model)
    flow_route_by_drainage_ref = _flow_route_by_drainage_ref(drainage_model)
    for section in list(getattr(applied, "sections", []) or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        section_sides = _ditch_surface_sides(section)
        for side in section_sides:
            surface_stations_by_side.setdefault(side, []).append(station)
        source_rows = _section_subassembly_rows(section, kind_filter="ditch")
        for source_row in source_rows:
            if str(getattr(source_row, "kind", "") or "").strip().lower() != "ditch":
                continue
            for side in _subassembly_sides(source_row):
                data = ditch_data_by_side.setdefault(side, {})
                subassembly_ref = str(getattr(source_row, "subassembly_id", "") or "").strip()
                data.setdefault("stations", []).append(station)
                data.setdefault("subassembly_refs", []).append(subassembly_ref)
                data.setdefault("materials", []).append(str(getattr(source_row, "material", "") or ""))
                data.setdefault("thicknesses", []).append(_ditch_lining_thickness(source_row))
                data.setdefault("region_refs", []).append(str(getattr(source_row, "region_id", "") or getattr(section, "region_id", "") or ""))
                data.setdefault("assembly_refs", []).append(str(getattr(section, "assembly_id", "") or ""))

    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for side in ("left", "right"):
        surface_stations = _unique_sorted_floats(surface_stations_by_side.get(side, []))
        ditch_data = ditch_data_by_side.get(side, {})
        ditch_stations = _unique_sorted_floats(list(ditch_data.get("stations", []) or []))
        all_stations = _unique_sorted_floats(surface_stations + ditch_stations)
        if len(all_stations) < 2:
            continue
        target_id = f"solid-target:lined-ditch:{side}"
        station_context = _drainage_station_context_for_side(
            applied,
            side=side,
            stations=all_stations,
            region_model=region_model,
            drainage_model=drainage_model,
        )
        context_drainage_refs = _unique_refs(list(getattr(station_context, "active_drainage_refs", []) or []))
        context_flow_route_refs = _unique_refs(list(getattr(station_context, "active_flow_route_refs", []) or []))
        drainage_owner = _drainage_owner_by_ref(
            drainage_model,
            context_drainage_refs[0] if context_drainage_refs else "",
        ) or drainage_owner_by_side.get(side)
        drainage_ref = context_drainage_refs[0] if context_drainage_refs else str(getattr(drainage_owner, "drainage_element_id", "") or "")
        if not drainage_ref:
            drainage_ref = f"lined_ditch:{side}"
        flow_route_ref = context_flow_route_refs[0] if context_flow_route_refs else flow_route_by_drainage_ref.get(drainage_ref, "")
        subassembly_refs = _unique_refs(list(ditch_data.get("subassembly_refs", []) or []))
        materials = _unique_refs(list(ditch_data.get("materials", []) or []))
        thicknesses = [float(value) for value in list(ditch_data.get("thicknesses", []) or [])]
        has_surface = len(surface_stations) >= 2
        has_material = len(materials) == 1 and bool(materials[0])
        has_lining_thickness = bool(thicknesses) and all(value > 0.0 for value in thicknesses)
        diagnostic_refs: list[str] = []
        if not has_surface:
            diagnostic = _diagnostic(
                "error",
                "lined_ditch_missing_surface_profile",
                target_id,
                f"Lined ditch {side} target needs ditch_surface points at two or more stations.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        if not has_material or not has_lining_thickness:
            diagnostic = _diagnostic(
                "error",
                "lined_ditch_missing_lining_policy",
                target_id,
                f"Lined ditch {side} target needs a material and positive lining thickness before it can become a solid.",
                notes=f"material={'yes' if has_material else 'no'};thickness={'yes' if has_lining_thickness else 'no'}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family="lined_ditch_body",
                scope_kind="drainage",
                station_start=min(all_stations),
                station_end=max(all_stations),
                subassembly_ref=_single_ref(subassembly_refs),
                drainage_ref=drainage_ref,
                flow_route_ref=flow_route_ref,
                enabled=False,
                material_ref=materials[0] if len(materials) == 1 else "",
                readiness_status="available" if has_surface and has_material and has_lining_thickness else "blocked",
                source_refs=_unique_refs(
                    source_refs
                    + subassembly_refs
                    + [f"ditch_surface:{side}"]
                    + _drainage_owner_source_refs(drainage_model, drainage_owner)
                    + ([flow_route_ref] if flow_route_ref else [])
                ),
                diagnostic_refs=diagnostic_refs,
                notes=_lined_ditch_target_notes(
                    side=side,
                    drainage_owner=drainage_owner,
                    drainage_ref=drainage_ref,
                    flow_route_ref=flow_route_ref,
                    station_context=station_context,
                    subassembly_refs=subassembly_refs,
                ),
            )
        )
    return rows, diagnostics


def _drainage_pipeline_target_rows(
    drainage_model: DrainageModel | None,
    *,
    structure_model: StructureModel | None,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if drainage_model is None or structure_model is None:
        return [], []
    pipeline_result = build_drainage_pipeline_result(drainage_model, structure_model)
    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    network_segments = []
    for segment in list(getattr(pipeline_result, "segment_rows", []) or []):
        segment_id = str(getattr(segment, "pipeline_segment_id", "") or "").strip()
        flow_route_ref = str(getattr(segment, "flow_route_ref", "") or "").strip()
        if not segment_id:
            continue
        target_id = f"solid-target:drainage-pipeline:{_safe_id(segment_id)}"
        start = float(getattr(segment, "station_start", 0.0) or 0.0)
        end = float(getattr(segment, "station_end", start) or start)
        if end < start:
            start, end = end, start
        diameter = float(getattr(segment, "diameter", 0.0) or 0.0)
        diagnostic_refs: list[str] = []
        ready = end > start and diameter > 0.0
        if ready:
            network_segments.append(segment)
        if not ready:
            diagnostic = _diagnostic(
                "error",
                "drainage_pipeline_target_not_ready",
                target_id,
                "Drainage pipeline segment needs a positive station span and diameter before it can become a solid target.",
                notes=f"flow_route_ref={flow_route_ref};diameter={diameter:g};station_start={start:g};station_end={end:g}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family="drainage_pipeline_body",
                scope_kind="drainage",
                station_start=start,
                station_end=end,
                drainage_ref=segment_id,
                flow_route_ref=flow_route_ref,
                enabled=False,
                material_ref="drainage-pipe",
                readiness_status="available" if ready else "blocked",
                source_refs=_unique_refs(
                    source_refs
                    + list(getattr(pipeline_result, "source_refs", []) or [])
                    + [
                        segment_id,
                        flow_route_ref,
                        str(getattr(segment, "from_element_ref", "") or ""),
                        str(getattr(segment, "to_element_ref", "") or ""),
                        str(getattr(segment, "from_connection_point_ref", "") or ""),
                        str(getattr(segment, "to_connection_point_ref", "") or ""),
                    ]
                ),
                diagnostic_refs=diagnostic_refs,
                notes=(
                    "Drainage pipeline body target discovered from Flow Route endpoint Structure connection points. "
                    f"segment={segment_id}; flow_route={flow_route_ref}; diameter={diameter:g}."
                ),
            )
        )
    if network_segments:
        station_start = min(float(getattr(segment, "station_start", 0.0) or 0.0) for segment in network_segments)
        station_end = max(float(getattr(segment, "station_end", 0.0) or 0.0) for segment in network_segments)
        segment_refs = _unique_refs([str(getattr(segment, "pipeline_segment_id", "") or "") for segment in network_segments])
        flow_route_refs = _unique_refs([str(getattr(segment, "flow_route_ref", "") or "") for segment in network_segments])
        rows.append(
            SolidTargetRow(
                target_id="solid-target:drainage-pipeline-network:main",
                target_family="drainage_pipeline_network_body",
                scope_kind="drainage",
                station_start=station_start,
                station_end=station_end,
                drainage_ref="drainage-pipeline-network:main",
                flow_route_ref=",".join(flow_route_refs),
                enabled=False,
                material_ref="drainage-pipe",
                readiness_status="available",
                source_refs=_unique_refs(
                    source_refs
                    + list(getattr(pipeline_result, "source_refs", []) or [])
                    + segment_refs
                    + flow_route_refs
                ),
                notes=(
                    "Drainage pipeline network target groups ready Flow Route pipe segments. "
                    f"segments={len(segment_refs)}; flow_routes={len(flow_route_refs)}; fuse_mode=compound_first_slice."
                ),
            )
        )
    return rows, diagnostics


def _station_context_summary_for_range(
    applied: AppliedSectionSet | None,
    *,
    region_model: RegionModel | None,
    structure_model: StructureModel | None,
    drainage_model: DrainageModel | None,
    station_start: float,
    station_end: float,
    region_ref: str = "",
) -> str:
    contexts = _station_contexts_for_range(
        applied,
        region_model=region_model,
        structure_model=structure_model,
        drainage_model=drainage_model,
        station_start=station_start,
        station_end=station_end,
        region_ref=region_ref,
    )
    structure_refs: list[str] = []
    drainage_refs: list[str] = []
    flow_route_refs: list[str] = []
    for context in contexts:
        structure_refs.extend(list(getattr(getattr(context, "structure_result", None), "active_structure_ids", []) or []))
        drainage_refs.extend(list(getattr(context, "active_drainage_refs", []) or []))
        flow_route_refs.extend(list(getattr(context, "active_flow_route_refs", []) or []))
    pieces: list[str] = []
    if structure_refs:
        pieces.append(f"structures={_join_refs(structure_refs)}")
    if drainage_refs:
        pieces.append(f"drainage={_join_refs(drainage_refs)}")
    if flow_route_refs:
        pieces.append(f"flow_routes={_join_refs(flow_route_refs)}")
    return "; ".join(pieces)


def _station_contexts_for_range(
    applied: AppliedSectionSet | None,
    *,
    region_model: RegionModel | None,
    structure_model: StructureModel | None = None,
    drainage_model: DrainageModel | None = None,
    station_start: float,
    station_end: float,
    region_ref: str = "",
) -> list[object]:
    if applied is None or region_model is None:
        return []
    lower = min(float(station_start), float(station_end))
    upper = max(float(station_start), float(station_end))
    active_region = str(region_ref or "").strip()
    resolver = StationContextResolver()
    contexts: list[object] = []
    for section in list(getattr(applied, "sections", []) or []):
        try:
            station = float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            continue
        if station < lower - 1.0e-6 or station > upper + 1.0e-6:
            continue
        if active_region and str(getattr(section, "region_id", "") or "").strip() not in {"", active_region}:
            continue
        try:
            context = resolver.resolve(
                region_model=region_model,
                structure_model=structure_model,
                drainage_model=drainage_model,
                station=station,
            )
        except Exception:
            continue
        context_region = str(getattr(getattr(context, "region_context", None), "region_id", "") or "").strip()
        if active_region and context_region and context_region != active_region:
            continue
        contexts.append(context)
    return contexts


def _drainage_lined_ditch_owner_by_side(drainage_model: DrainageModel | None) -> dict[str, object]:
    if drainage_model is None:
        return {}
    output: dict[str, object] = {}
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        kind = str(getattr(row, "element_kind", "") or "").strip().lower()
        if kind not in {"ditch", "lined_ditch", "lined-ditch", "channel"}:
            continue
        side = _side_from_values(
            str(getattr(row, "side", "") or ""),
            str(getattr(row, "drainage_element_id", "") or ""),
        )
        if side and side not in output:
            output[side] = row
    return output


def _drainage_station_context_for_side(
    applied: AppliedSectionSet | None,
    *,
    side: str,
    stations: list[float],
    region_model: RegionModel | None,
    drainage_model: DrainageModel | None,
):
    if applied is None or region_model is None or drainage_model is None:
        return None
    station_set = {round(float(value), 6) for value in list(stations or [])}
    if not station_set:
        return None
    resolver = StationContextResolver()
    side_key = str(side or "").strip().lower()
    for section in list(getattr(applied, "sections", []) or []):
        try:
            station = float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            continue
        if round(station, 6) not in station_set:
            continue
        try:
            context = resolver.resolve(
                region_model=region_model,
                drainage_model=drainage_model,
                station=station,
            )
        except Exception:
            continue
        refs_by_side = dict(getattr(context, "active_drainage_refs_by_side", {}) or {})
        if side_key and refs_by_side.get(side_key):
            return context
    return None


def _drainage_owner_by_ref(drainage_model: DrainageModel | None, drainage_ref: str):
    if drainage_model is None:
        return None
    active_ref = str(drainage_ref or "").strip()
    if not active_ref:
        return None
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        if str(getattr(row, "drainage_element_id", "") or "").strip() == active_ref:
            return row
    return None


def _lined_ditch_target_notes(
    *,
    side: str,
    drainage_owner,
    drainage_ref: str,
    flow_route_ref: str,
    station_context,
    subassembly_refs: list[str] | None = None,
) -> str:
    notes = f"Lined ditch {side} target discovered from ditch_surface rows and Subassembly ditch context."
    refs = _unique_refs(subassembly_refs or [])
    if refs:
        notes += f" Subassembly refs={_join_refs(refs)}."
    if drainage_owner is not None:
        notes += (
            f" DrainageModel owner={drainage_ref};"
            f" policy={str(getattr(drainage_owner, 'policy_set_ref', '') or '')};"
            f" flow_route={flow_route_ref}."
        )
    if station_context is not None:
        region_id = str(getattr(getattr(station_context, "region_context", None), "region_id", "") or "").strip()
        notes += f" StationContext region={region_id or '-'}."
    return notes


def _section_subassembly_rows(section, *, kind_filter: str = "") -> list[object]:
    """Return active Subassembly rows."""

    normalized_kind = str(kind_filter or "").strip().lower()
    return [
        row
        for row in list(getattr(section, "subassembly_rows", []) or [])
        if not normalized_kind or str(getattr(row, "kind", "") or "").strip().lower() == normalized_kind
    ]


def _drainage_owner_source_refs(drainage_model: DrainageModel | None, drainage_owner: object | None) -> list[str]:
    if drainage_model is None or drainage_owner is None:
        return []
    return _unique_refs(
        [
            str(getattr(drainage_model, "drainage_model_id", "") or ""),
            str(getattr(drainage_owner, "drainage_element_id", "") or ""),
            str(getattr(drainage_owner, "policy_set_ref", "") or ""),
        ]
    )


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


def _station_range(applied: AppliedSectionSet | None) -> tuple[float, float, int]:
    stations = []
    for row in list(getattr(applied, "station_rows", []) or []) if applied is not None else []:
        try:
            stations.append(float(getattr(row, "station", 0.0) or 0.0))
        except Exception:
            pass
    if not stations:
        for section in list(getattr(applied, "sections", []) or []) if applied is not None else []:
            try:
                stations.append(float(getattr(section, "station", 0.0) or 0.0))
            except Exception:
                pass
    if not stations:
        return 0.0, 0.0, 0
    return min(stations), max(stations), len(set(round(value, 6) for value in stations))


def _intersection_control_region_refs(intersection_model: IntersectionModel, intersection) -> list[str]:
    intersection_id = str(getattr(intersection, "intersection_id", "") or "").strip()
    refs = list(getattr(intersection, "control_region_refs", []) or [])
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "").strip() != intersection_id:
            continue
        refs.extend(list(getattr(area, "control_region_refs", []) or []))
    return _unique_refs(refs)


def _intersection_station_range(intersection_model: IntersectionModel, intersection_id: str) -> tuple[float, float]:
    stations: list[float] = []
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "").strip() != str(intersection_id or "").strip():
            continue
        for station_range in list(getattr(area, "station_ranges", []) or []):
            if len(station_range) < 2:
                continue
            try:
                stations.extend([float(station_range[0]), float(station_range[1])])
            except Exception:
                pass
    if not stations:
        return 0.0, 0.0
    return min(stations), max(stations)


def _intersection_applied_section_count(sections: list[object], intersection_id: str, control_refs: list[str]) -> int:
    controls = set(str(value or "").strip() for value in list(control_refs or []) if str(value or "").strip())
    keys: set[str] = set()
    for section in list(sections or []):
        section_id = str(getattr(section, "applied_section_id", "") or "").strip()
        if not section_id:
            section_id = f"{getattr(section, 'alignment_id', '')}:{getattr(section, 'station', '')}"
        if str(getattr(section, "active_intersection_id", "") or "").strip() == str(intersection_id or "").strip():
            keys.add(section_id)
            continue
        if str(getattr(section, "region_id", "") or "").strip() in controls:
            keys.add(section_id)
    return len(keys)


def _source_refs(applied: AppliedSectionSet | None, corridor: CorridorModel | None) -> list[str]:
    output: list[str] = []
    applied_ref = str(getattr(applied, "applied_section_set_id", "") or "").strip()
    corridor_ref = str(getattr(corridor, "corridor_id", "") or "").strip()
    for value in (applied_ref, corridor_ref):
        if value and value not in output:
            output.append(value)
    return output


def _diagnostic(severity: str, kind: str, source_ref: str, message: str, notes: str = "") -> SolidTargetDiagnosticRow:
    return SolidTargetDiagnosticRow(
        diagnostic_id=f"solid-target:{kind}:{_safe_id(source_ref)}",
        severity=severity,
        kind=kind,
        source_ref=source_ref,
        message=message,
        notes=str(notes or ""),
    )


def _safe_id(value: str) -> str:
    text = str(value or "").strip().replace(" ", "-").replace(":", "-").replace("/", "-").replace("\\", "-")
    return text or "unknown"


def _structure_geometry_source_mode(row) -> str:
    mode = str(getattr(row, "geometry_source_mode", "") or "").strip().lower()
    if mode in {"native", "external_ref"}:
        return mode
    reference_mode = str(getattr(row, "reference_mode", "") or "").strip().lower()
    geometry_ref = str(getattr(row, "geometry_ref", "") or "").strip()
    if reference_mode in {"source_ref", "reference_geometry", "external_ref"} or geometry_ref:
        return "external_ref"
    return "native"


def _structure_requires_connection_points(row) -> bool:
    values = [
        str(getattr(row, "structure_kind", "") or ""),
        str(getattr(row, "structure_role", "") or ""),
        str(getattr(row, "native_type", "") or ""),
    ]
    drainage_tokens = {
        "box_culvert",
        "culvert",
        "drainage_crossing",
        "drainage_node",
        "headwall",
        "inlet",
        "junction_box",
        "manhole",
        "outlet",
        "pipe_culvert",
    }
    return any(value.strip().lower() in drainage_tokens for value in values)


def _single_ref(values) -> str:
    refs = []
    for value in list(values or []):
        text = str(value or "").strip()
        if text and text not in refs:
            refs.append(text)
    return refs[0] if len(refs) == 1 else ""


def _unique_refs(values) -> list[str]:
    refs: list[str] = []
    for value in list(values or []):
        text = str(value or "").strip()
        if text and text not in refs:
            refs.append(text)
    return refs


def _join_refs(values) -> str:
    return ", ".join(_unique_refs(values))


def _subassembly_target_family(kind: str) -> str:
    text = str(kind or "").strip().lower()
    if text == "pavement_layer":
        return "pavement_layer_body"
    if text == "subbase":
        return "subbase_body"
    if text == "shoulder":
        return "shoulder_body"
    return ""


def _subassembly_target_family_for_solid_family(solid_family: str) -> str:
    text = str(solid_family or "").strip().lower().replace("-", "_")
    if not text:
        return ""
    if text.endswith("_body"):
        return text
    if text in {"pavement_layer", "pavement"}:
        return "pavement_layer_body"
    if text == "subbase":
        return "subbase_body"
    if text == "shoulder":
        return "shoulder_body"
    if text in {"lined_ditch", "ditch_lining"}:
        return "lined_ditch_body"
    return _subassembly_target_family(text)


def _subassembly_target_prefix(family: str) -> str:
    text = str(family or "").strip().lower()
    if text == "subbase_body":
        return "subbase"
    if text == "shoulder_body":
        return "shoulder"
    return "pavement-layer"


def _subassembly_target_label(family: str) -> str:
    text = str(family or "").strip().lower()
    if text == "subbase_body":
        return "Subbase body"
    if text == "shoulder_body":
        return "Shoulder body"
    return "Pavement layer"


def _ditch_surface_sides(section) -> set[str]:
    sides: set[str] = set()
    for point in list(getattr(section, "point_rows", []) or []):
        if str(getattr(point, "point_role", "") or "").strip().lower() != "ditch_surface":
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if offset > 0.0:
            sides.add("left")
        elif offset < 0.0:
            sides.add("right")
    return sides


def _subassembly_sides(subassembly) -> list[str]:
    side = str(getattr(subassembly, "side", "") or "center").strip().lower()
    if side in {"left", "right"}:
        return [side]
    if side in {"both", "center"}:
        return ["left", "right"]
    return []


def _side_from_values(*values: str) -> str:
    for value in values:
        text = str(value or "").strip().lower()
        if "right" in text:
            return "right"
        if "left" in text:
            return "left"
    return ""


def _ditch_lining_thickness(subassembly) -> float:
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


def _unique_sorted_floats(values: list[float]) -> list[float]:
    output: list[float] = []
    seen: set[float] = set()
    for value in sorted(float(item) for item in list(values or [])):
        key = round(value, 6)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output
