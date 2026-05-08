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
        diagnostic_refs = [row.diagnostic_id for row in diagnostics]
        source_refs = _unique_refs(
            [
                target_id,
                str(getattr(request.profile_set, "profile_set_id", "") or ""),
                str(getattr(request.edge_network, "edge_network_id", "") or ""),
                *list(getattr(target, "source_refs", []) or []),
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
            region_ref=str(getattr(target, "region_ref", "") or ""),
            assembly_ref=str(getattr(target, "assembly_ref", "") or ""),
            component_ref=str(getattr(target, "component_ref", "") or ""),
            structure_ref=str(getattr(target, "structure_ref", "") or ""),
            drainage_ref=str(getattr(target, "drainage_ref", "") or ""),
            material_ref=str(getattr(target, "material_ref", "") or ""),
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
