"""Watertight solid target discovery service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.source.drainage_model import DrainageModel
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from ...models.source.solid_target_model import (
    SolidTargetDiagnosticRow,
    SolidTargetModel,
    SolidTargetRow,
)


@dataclass(frozen=True)
class SolidTargetDiscoveryRequest:
    """Input context for discovering watertight solid target candidates."""

    project_id: str = "corridorroad-v1"
    corridor_ref: str = "corridor:main"
    applied_section_set: AppliedSectionSet | None = None
    corridor_model: CorridorModel | None = None
    region_model: RegionModel | None = None
    structure_model: StructureModel | None = None
    drainage_model: DrainageModel | None = None


class SolidTargetDiscoveryService:
    """Discover topology-first watertight solid target candidates from v1 results."""

    def discover(self, request: SolidTargetDiscoveryRequest) -> SolidTargetModel:
        applied = request.applied_section_set
        corridor = request.corridor_model
        region_model = request.region_model
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
                source_refs=source_refs,
            )
            target_rows.extend(region_rows)
            diagnostics.extend(region_diagnostics)

        component_rows, component_diagnostics = _component_target_rows(
            applied,
            source_refs=source_refs,
        )
        target_rows.extend(component_rows)
        diagnostics.extend(component_diagnostics)

        lined_ditch_rows, lined_ditch_diagnostics = _lined_ditch_target_rows(
            applied,
            drainage_model=drainage_model,
            source_refs=source_refs,
        )
        target_rows.extend(lined_ditch_rows)
        diagnostics.extend(lined_ditch_diagnostics)

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
        rows.append(
            SolidTargetRow(
                target_id=f"solid-target:region-body:{_safe_id(region_id)}",
                target_family="region_body",
                scope_kind="region",
                station_start=start,
                station_end=end,
                region_ref=region_id,
                assembly_ref=str(getattr(region, "assembly_ref", "") or ""),
                structure_ref=str(getattr(region, "structure_ref", "") or ""),
                drainage_ref=",".join(str(ref) for ref in list(getattr(region, "drainage_refs", []) or []) if str(ref)),
                enabled=False,
                readiness_status="available" if overlaps else "blocked",
                source_refs=source_refs + [region_id],
                diagnostic_refs=diagnostic_refs,
                notes="Region-scoped body target discovered from RegionModel.",
            )
        )
    return rows, diagnostics


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
        spec = geometry_by_id.get(spec_ref)
        target_id = f"solid-target:structure-body:{_safe_id(structure_id)}"
        diagnostic_refs: list[str] = []
        ready = spec is not None and end > start
        if spec is None:
            diagnostic = _diagnostic(
                "error",
                "missing_structure_geometry_spec",
                target_id,
                f"Structure {structure_id} cannot produce a solid target without a native geometry spec.",
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
                source_refs=source_refs + [str(getattr(structure_model, "structure_model_id", "") or ""), structure_id, spec_ref],
                diagnostic_refs=diagnostic_refs,
                notes=f"Structure body target discovered from StructureModel; structure_kind={str(getattr(structure, 'structure_kind', '') or '')}.",
            )
        )
    return rows, diagnostics


def _component_target_rows(
    applied: AppliedSectionSet | None,
    *,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if applied is None:
        return [], []
    component_targets: dict[tuple[str, str], dict[str, object]] = {}
    for section in list(getattr(applied, "sections", []) or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        for component in list(getattr(section, "component_rows", []) or []):
            kind = str(getattr(component, "kind", "") or "").strip().lower()
            family = _component_target_family(kind)
            if not family:
                continue
            component_id = str(getattr(component, "component_id", "") or "").strip()
            width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
            thickness = max(float(getattr(component, "thickness", 0.0) or 0.0), 0.0)
            if not component_id:
                continue
            key = (family, component_id)
            data = component_targets.setdefault(
                key,
                {
                    "stations": [],
                    "kind": kind,
                    "family": family,
                    "material": str(getattr(component, "material", "") or ""),
                    "region_refs": [],
                    "assembly_refs": [],
                    "invalid_dimension_stations": [],
                },
            )
            data["stations"].append(station)
            data["region_refs"].append(str(getattr(component, "region_id", "") or getattr(section, "region_id", "") or ""))
            data["assembly_refs"].append(str(getattr(section, "assembly_id", "") or ""))
            if width <= 0.0 or thickness <= 0.0:
                data["invalid_dimension_stations"].append(station)
            if not str(data.get("material", "") or ""):
                data["material"] = str(getattr(component, "material", "") or "")

    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for (family, component_id), data in sorted(component_targets.items()):
        stations = sorted(float(value) for value in list(data.get("stations", []) or []))
        station_count = len(set(round(value, 6) for value in stations))
        target_prefix = _component_target_prefix(family)
        target_id = f"solid-target:{target_prefix}:{_safe_id(component_id)}"
        diagnostic_refs: list[str] = []
        if station_count < 2:
            diagnostic = _diagnostic(
                "error",
                "component_target_insufficient_profiles",
                target_id,
                f"Component {component_id} needs at least two Applied Section profiles before it can become a solid target.",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        invalid_stations = _unique_sorted_floats(list(data.get("invalid_dimension_stations", []) or []))
        if invalid_stations:
            diagnostic = _diagnostic(
                "error",
                "component_target_invalid_dimensions",
                target_id,
                f"Component {component_id} needs positive width and thickness at every target station.",
                notes=f"stations={','.join(f'{station:g}' for station in invalid_stations)}",
            )
            diagnostics.append(diagnostic)
            diagnostic_refs.append(diagnostic.diagnostic_id)
        rows.append(
            SolidTargetRow(
                target_id=target_id,
                target_family=family,
                scope_kind="assembly_component",
                station_start=min(stations) if stations else 0.0,
                station_end=max(stations) if stations else 0.0,
                region_ref=_single_ref(data.get("region_refs", [])),
                assembly_ref=_single_ref(data.get("assembly_refs", [])),
                component_ref=component_id,
                enabled=False,
                material_ref=str(data.get("material", "") or ""),
                readiness_status="available" if station_count >= 2 and not invalid_stations else "blocked",
                source_refs=source_refs + [component_id],
                diagnostic_refs=diagnostic_refs,
                notes=f"{_component_target_label(family)} target discovered from Applied Section component rows; component_kind={data.get('kind', '')}.",
            )
        )
    return rows, diagnostics


def _lined_ditch_target_rows(
    applied: AppliedSectionSet | None,
    *,
    drainage_model: DrainageModel | None = None,
    source_refs: list[str],
) -> tuple[list[SolidTargetRow], list[SolidTargetDiagnosticRow]]:
    if applied is None:
        return [], []
    surface_stations_by_side: dict[str, list[float]] = {"left": [], "right": []}
    component_data_by_side: dict[str, dict[str, object]] = {"left": {}, "right": {}}
    drainage_owner_by_side = _drainage_lined_ditch_owner_by_side(drainage_model)
    for section in list(getattr(applied, "sections", []) or []):
        station = float(getattr(section, "station", 0.0) or 0.0)
        section_sides = _ditch_surface_sides(section)
        for side in section_sides:
            surface_stations_by_side.setdefault(side, []).append(station)
        for component in list(getattr(section, "component_rows", []) or []):
            if str(getattr(component, "kind", "") or "").strip().lower() != "ditch":
                continue
            for side in _component_sides(component):
                data = component_data_by_side.setdefault(side, {})
                data.setdefault("stations", []).append(station)
                data.setdefault("component_refs", []).append(str(getattr(component, "component_id", "") or ""))
                data.setdefault("materials", []).append(str(getattr(component, "material", "") or ""))
                data.setdefault("thicknesses", []).append(_ditch_lining_thickness(component))
                data.setdefault("region_refs", []).append(str(getattr(component, "region_id", "") or getattr(section, "region_id", "") or ""))
                data.setdefault("assembly_refs", []).append(str(getattr(section, "assembly_id", "") or ""))

    rows: list[SolidTargetRow] = []
    diagnostics: list[SolidTargetDiagnosticRow] = []
    for side in ("left", "right"):
        surface_stations = _unique_sorted_floats(surface_stations_by_side.get(side, []))
        component_data = component_data_by_side.get(side, {})
        component_stations = _unique_sorted_floats(list(component_data.get("stations", []) or []))
        all_stations = _unique_sorted_floats(surface_stations + component_stations)
        if len(all_stations) < 2:
            continue
        target_id = f"solid-target:lined-ditch:{side}"
        drainage_owner = drainage_owner_by_side.get(side)
        drainage_ref = str(getattr(drainage_owner, "drainage_element_id", "") or "") if drainage_owner is not None else f"lined_ditch:{side}"
        component_refs = _unique_refs(list(component_data.get("component_refs", []) or []))
        materials = _unique_refs(list(component_data.get("materials", []) or []))
        thicknesses = [float(value) for value in list(component_data.get("thicknesses", []) or [])]
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
                component_ref=_single_ref(component_refs),
                drainage_ref=drainage_ref,
                enabled=False,
                material_ref=materials[0] if len(materials) == 1 else "",
                readiness_status="available" if has_surface and has_material and has_lining_thickness else "blocked",
                source_refs=_unique_refs(
                    source_refs
                    + component_refs
                    + [f"ditch_surface:{side}"]
                    + _drainage_owner_source_refs(drainage_model, drainage_owner)
                ),
                diagnostic_refs=diagnostic_refs,
                notes=(
                    f"Lined ditch {side} target discovered from ditch_surface rows and Assembly ditch component context."
                    + (
                        f" DrainageModel owner={drainage_ref}; policy={str(getattr(drainage_owner, 'policy_set_ref', '') or '')}."
                        if drainage_owner is not None
                        else ""
                    )
                ),
            )
        )
    return rows, diagnostics


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


def _component_target_family(kind: str) -> str:
    text = str(kind or "").strip().lower()
    if text == "pavement_layer":
        return "pavement_layer_body"
    if text == "subbase":
        return "subbase_body"
    if text == "shoulder":
        return "shoulder_body"
    return ""


def _component_target_prefix(family: str) -> str:
    text = str(family or "").strip().lower()
    if text == "subbase_body":
        return "subbase"
    if text == "shoulder_body":
        return "shoulder"
    return "pavement-layer"


def _component_target_label(family: str) -> str:
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


def _component_sides(component) -> list[str]:
    side = str(getattr(component, "side", "") or "center").strip().lower()
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


def _ditch_lining_thickness(component) -> float:
    thickness = max(float(getattr(component, "thickness", 0.0) or 0.0), 0.0)
    if thickness > 0.0:
        return thickness
    params = dict(getattr(component, "parameters", {}) or {})
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
