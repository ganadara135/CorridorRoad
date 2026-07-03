"""Watertight solid output mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...models.output.watertight_solid_output import (
    WatertightSolidOutput,
    WatertightSolidOutputDiagnosticRow,
    WatertightSolidOutputRow,
    WatertightSolidSegmentRow,
)
from ...models.result.applied_section_solid_profile import AppliedSectionSolidProfileSet
from ...models.result.solid_edge_network import SolidEdgeNetwork
from ...models.source.solid_target_model import SolidTargetRow
from .watertight_solid_part_mapper import WatertightSolidPartMappingResult


@dataclass(frozen=True)
class WatertightSolidOutputMappingRequest:
    """Input bundle for mapping one solid build result into output rows."""

    project_id: str
    corridor_id: str
    solid_target: SolidTargetRow
    profile_set: AppliedSectionSolidProfileSet
    edge_network: SolidEdgeNetwork
    part_result: WatertightSolidPartMappingResult
    generated_object_ref: str = ""
    watertight_solid_output_id: str = "watertight-solids:main"
    boundary_trace_rows: list[str] | None = None


class WatertightSolidOutputMapper:
    """Map watertight solid result contracts and shape metadata into output payloads."""

    def map_result(self, request: WatertightSolidOutputMappingRequest) -> WatertightSolidOutput:
        target = request.solid_target
        target_id = str(getattr(target, "target_id", "") or getattr(request.edge_network, "target_ref", "") or "")
        output_object_id = f"watertight-solid:{_safe_id(target_id)}"
        diagnostics = _diagnostic_rows(
            output_object_id,
            list(getattr(request.profile_set, "diagnostic_rows", []) or [])
            + list(getattr(request.edge_network, "diagnostic_rows", []) or [])
            + list(getattr(request.part_result, "diagnostic_rows", []) or []),
        )
        diagnostics.extend(
            _provenance_diagnostic_rows(
                output_object_id,
                target,
                request.profile_set,
                start_index=len(diagnostics) + 1,
            )
        )
        diagnostic_refs = [row.diagnostic_id for row in diagnostics]
        boundary_trace_rows = [str(row) for row in list(request.boundary_trace_rows or []) if str(row)]
        boundary_adjacency_rows = _boundary_adjacency_rows(output_object_id, boundary_trace_rows)
        source_refs = _unique_refs(
            [
                target_id,
                str(getattr(request.profile_set, "profile_set_id", "") or ""),
                str(getattr(request.edge_network, "edge_network_id", "") or ""),
                *list(getattr(target, "source_refs", []) or []),
                str(getattr(target, "subassembly_ref", "") or ""),
                str(getattr(target, "flow_route_ref", "") or ""),
                *list(getattr(request.profile_set, "source_refs", []) or []),
                *list(getattr(request.edge_network, "source_refs", []) or []),
            ]
        )
        solid_row = WatertightSolidOutputRow(
            output_object_id=output_object_id,
            target_id=target_id,
            target_family=str(getattr(target, "target_family", "") or ""),
            scope_kind=str(getattr(target, "scope_kind", "") or ""),
            station_start=float(getattr(target, "station_start", getattr(request.profile_set, "station_start", 0.0)) or 0.0),
            station_end=float(getattr(target, "station_end", getattr(request.profile_set, "station_end", 0.0)) or 0.0),
            source_refs=source_refs,
            generated_object_ref=str(request.generated_object_ref or ""),
            validation_status=str(getattr(request.part_result, "validation_status", "") or ""),
            is_watertight=bool(getattr(request.part_result, "is_watertight", False)),
            is_valid_solid=bool(getattr(request.part_result, "is_valid_solid", False)),
            volume=max(float(getattr(request.part_result, "volume", 0.0) or 0.0), 0.0),
            face_count=int(getattr(request.part_result, "face_count", 0) or getattr(request.edge_network, "face_count", 0) or 0),
            edge_count=int(getattr(request.part_result, "edge_count", 0) or getattr(request.edge_network, "edge_count", 0) or 0),
            profile_count=int(getattr(request.edge_network, "profile_count", 0) or len(list(getattr(request.profile_set, "profile_rows", []) or []))),
            diagnostic_refs=diagnostic_refs,
            boundary_trace_rows=boundary_trace_rows,
            boundary_adjacency_rows=boundary_adjacency_rows,
            region_ref=str(getattr(target, "region_ref", "") or ""),
            assembly_ref=str(getattr(target, "assembly_ref", "") or ""),
            subassembly_ref=str(getattr(target, "subassembly_ref", "") or ""),
            structure_ref=str(getattr(target, "structure_ref", "") or ""),
            drainage_ref=str(getattr(target, "drainage_ref", "") or ""),
            flow_route_ref=str(getattr(target, "flow_route_ref", "") or ""),
            material_ref=str(getattr(target, "material_ref", "") or ""),
            path_source=_profile_path_source(request.profile_set),
            notes=str(getattr(target, "notes", "") or ""),
        )
        segment_rows = _segment_rows(output_object_id, request.edge_network, request.profile_set)
        return WatertightSolidOutput(
            schema_version=1,
            project_id=str(request.project_id or getattr(request.profile_set, "project_id", "") or "corridorroad-v1"),
            watertight_solid_output_id=str(request.watertight_solid_output_id or "watertight-solids:main"),
            corridor_id=str(request.corridor_id or getattr(request.profile_set, "corridor_ref", "") or ""),
            label="Watertight Solids",
            selection_scope={
                "scope_kind": str(getattr(target, "scope_kind", "") or ""),
                "target_id": target_id,
            },
            source_refs=source_refs,
            result_refs=[
                ref
                for ref in [
                    str(getattr(request.profile_set, "profile_set_id", "") or ""),
                    str(getattr(request.edge_network, "edge_network_id", "") or ""),
                    str(request.generated_object_ref or ""),
                ]
                if ref
            ],
            diagnostic_rows=[
                DiagnosticMessage(
                    severity=row.severity,
                    kind=row.kind,
                    message=row.message,
                    notes=row.notes,
                )
                for row in diagnostics
            ],
            solid_rows=[solid_row],
            segment_rows=segment_rows,
            solid_diagnostic_rows=diagnostics,
        )


def _segment_rows(
    output_object_id: str,
    edge_network: SolidEdgeNetwork,
    profile_set: AppliedSectionSolidProfileSet,
) -> list[WatertightSolidSegmentRow]:
    profiles = sorted(
        list(getattr(profile_set, "profile_rows", []) or []),
        key=lambda profile: float(getattr(profile, "station", 0.0) or 0.0),
    )
    rows: list[WatertightSolidSegmentRow] = []
    for index, (start, end) in enumerate(zip(profiles, profiles[1:]), start=1):
        station_start = float(getattr(start, "station", 0.0) or 0.0)
        station_end = float(getattr(end, "station", 0.0) or 0.0)
        face_refs = [
            str(getattr(face, "face_id", "") or "")
            for face in list(getattr(edge_network, "face_rows", []) or [])
            if abs(float(getattr(face, "station_start", 0.0) or 0.0) - station_start) <= 1.0e-9
            and abs(float(getattr(face, "station_end", 0.0) or 0.0) - station_end) <= 1.0e-9
        ]
        rows.append(
            WatertightSolidSegmentRow(
                segment_id=f"{output_object_id}:segment:{index}",
                parent_output_object_id=output_object_id,
                station_start=station_start,
                station_end=station_end,
                face_refs=_unique_refs(face_refs),
                profile_refs=[
                    str(getattr(start, "profile_id", "") or ""),
                    str(getattr(end, "profile_id", "") or ""),
                ],
                notes="profile_span",
            )
        )
    return rows


def _boundary_adjacency_rows(output_object_id: str, boundary_trace_rows: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for index, raw_row in enumerate(boundary_trace_rows, start=1):
        parsed = _parse_boundary_trace_row(raw_row)
        breakline_id = parsed.get("breakline_id") or parsed.get("trace_id") or f"boundary-trace-{index}"
        text = "|".join(
            [
                f"adjacency_id={output_object_id}:shared-breakline-adjacency:{index}",
                f"output_ref={output_object_id}",
                f"breakline_id={breakline_id}",
                f"role={parsed.get('role', '')}",
                f"domain_kind={parsed.get('domain_kind', '')}",
                f"domain_ref={parsed.get('domain_ref', '')}",
                f"material_role={parsed.get('material_role', '')}",
                f"consumer_refs={parsed.get('consumer_refs', '')}",
                f"handoff_target={parsed.get('handoff_target', '')}",
                "adjacency_status=candidate",
                "source=shared_breakline_boundary_trace",
            ]
        )
        if text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _parse_boundary_trace_row(row: str) -> dict[str, str]:
    text = str(row or "").strip()
    if not text:
        return {}
    if "=" in text:
        parsed: dict[str, str] = {}
        for part in text.replace("|", ";").split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            normalized_key = key.strip().lower().replace("-", "_")
            if normalized_key:
                parsed[normalized_key] = value.strip()
        if "role" not in parsed and "breakline_role" in parsed:
            parsed["role"] = parsed["breakline_role"]
        return parsed
    parts = text.split("|")
    keys = [
        "trace_id",
        "role",
        "domain_kind",
        "domain_ref",
        "alignment_ref",
        "station_start",
        "station_end",
        "material_role",
        "status",
        "source_contract_refs",
        "consumer_refs",
        "handoff_target",
    ]
    return {key: parts[index].strip() for index, key in enumerate(keys) if index < len(parts)}


def _diagnostic_rows(output_object_id: str, rows: list[object]) -> list[WatertightSolidOutputDiagnosticRow]:
    output: list[WatertightSolidOutputDiagnosticRow] = []
    seen: set[str] = set()
    for index, row in enumerate(list(rows or []), start=1):
        kind = str(getattr(row, "kind", "") or "diagnostic")
        notes = str(getattr(row, "notes", "") or "")
        diagnostic_id = f"{output_object_id}:diagnostic:{index}:{_safe_id(kind)}"
        if diagnostic_id in seen:
            continue
        seen.add(diagnostic_id)
        output.append(
            WatertightSolidOutputDiagnosticRow(
                diagnostic_id=diagnostic_id,
                severity=str(getattr(row, "severity", "") or "info"),
                kind=kind,
                source_ref=output_object_id,
                message=str(getattr(row, "message", "") or kind),
                notes=notes,
            )
        )
    return output


def _provenance_diagnostic_rows(
    output_object_id: str,
    target: SolidTargetRow,
    profile_set: AppliedSectionSolidProfileSet,
    *,
    start_index: int,
) -> list[WatertightSolidOutputDiagnosticRow]:
    target_family = str(getattr(target, "target_family", "") or "").strip().lower()
    if target_family != "lined_ditch_body":
        return []
    profiles = list(getattr(profile_set, "profile_rows", []) or [])
    if not profiles:
        return []
    first_profile = profiles[0]
    first_notes = _note_pairs(str(getattr(first_profile, "notes", "") or ""))
    top_nodes = [
        node
        for node in list(getattr(first_profile, "node_rows", []) or [])
        if str(getattr(node, "semantic_role", "") or "").startswith("top")
    ]
    bottom_nodes = [
        node
        for node in list(getattr(first_profile, "node_rows", []) or [])
        if str(getattr(node, "semantic_role", "") or "").startswith("bottom")
    ]
    station_values = _unique_refs(
        [
            f"{float(getattr(profile, 'station', 0.0) or 0.0):.12g}"
            for profile in profiles
        ]
    )
    top_source_refs = _unique_refs(
        [
            str(getattr(node, "source_point_ref", "") or "")
            for node in top_nodes
        ]
    )
    subassembly_ref = str(getattr(target, "subassembly_ref", "") or first_notes.get("subassembly_ref", ""))
    notes = ";".join(
        [
            f"target={str(getattr(target, 'target_id', '') or '')}",
            f"drainage_ref={str(getattr(target, 'drainage_ref', '') or first_notes.get('drainage_ref', ''))}",
            f"flow_route_ref={str(getattr(target, 'flow_route_ref', '') or first_notes.get('flow_route_ref', ''))}",
            f"subassembly_ref={subassembly_ref}",
            f"side={first_notes.get('side', _side_from_ref(str(getattr(target, 'drainage_ref', '') or getattr(target, 'target_id', '') or '')))}",
            f"material={str(getattr(target, 'material_ref', '') or first_notes.get('material', ''))}",
            f"lining_thickness={first_notes.get('lining_thickness', '')}",
            "offset_method=section_normal_polyline",
            f"join_policy={first_notes.get('join_policy', '')}",
            f"miter_limit={first_notes.get('miter_limit', '')}",
            f"profile_count={len(profiles)}",
            f"profile_node_count={len(list(getattr(first_profile, 'node_rows', []) or []))}",
            f"top_point_count={len(top_nodes)}",
            f"bottom_point_count={len(bottom_nodes)}",
            f"stations={','.join(station_values)}",
            f"top_source_point_refs={','.join(top_source_refs)}",
        ]
    )
    return [
        WatertightSolidOutputDiagnosticRow(
            diagnostic_id=f"{output_object_id}:diagnostic:{int(start_index)}:lined-ditch-shape-provenance",
            severity="info",
            kind="lined_ditch_shape_provenance",
            source_ref=output_object_id,
            message="Lined ditch solid output records ditch shape and lining policy provenance.",
            notes=notes,
        )
    ]


def _note_pairs(notes: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for chunk in str(notes or "").split(";"):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip()
        if not key:
            continue
        pairs[key] = value.strip()
    return pairs


def _side_from_ref(value: str) -> str:
    text = str(value or "").strip().lower()
    if "right" in text:
        return "right"
    if "left" in text:
        return "left"
    return ""
def _profile_path_source(profile_set: AppliedSectionSolidProfileSet) -> str:
    profiles = list(getattr(profile_set, "profile_rows", []) or [])
    if any("path_source=centerline3d_result" in str(getattr(profile, "notes", "") or "") for profile in profiles):
        return "centerline3d_result"
    if any(str(getattr(profile, "applied_section_ref", "") or "") for profile in profiles):
        return "applied_section_frame"
    return "station_range"


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
