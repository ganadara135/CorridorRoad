"""Exchange output mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from ...models.output.base import OutputModelBase
from ...models.output.exchange_output import ExchangeOutput, ExchangeOutputRef


_SIDE_SLOPE_SUBASSEMBLY_KINDS = {"side_slope", "bench", "daylight"}
_SIDE_SLOPE_QUANTITY_KINDS = {"bench_surface_length", "slope_face_length"}
_SIDE_SLOPE_MEASUREMENT_KINDS = {"section_side_slope_breakline"}


@dataclass(frozen=True)
class ExchangePackageRequest:
    """Input contract for packaging normalized outputs for exchange."""

    project_id: str
    exchange_output_id: str
    format: str
    package_kind: str
    outputs: list[OutputModelBase]


class ExchangeOutputMapper:
    """Package normalized outputs into one exchange output payload."""

    def map_output_package(self, request: ExchangePackageRequest) -> ExchangeOutput:
        """Create one exchange package from normalized output payloads."""

        output_refs = [
            ExchangeOutputRef(
                ref_id=f"{request.exchange_output_id}:output:{index}",
                output_kind=self._output_kind(output),
                output_id=self._output_id(output),
                schema_version=output.schema_version,
            )
            for index, output in enumerate(request.outputs, start=1)
        ]

        source_refs = self._unique_list(
            ref
            for output in request.outputs
            for ref in output.source_refs
        )
        result_refs = self._unique_list(
            ref
            for output in request.outputs
            for ref in output.result_refs
        )
        source_context_rows = self._source_context_rows(request.outputs)
        diagnostic_rows = self._diagnostic_rows(request.outputs)
        surface_span_rows = self._surface_span_rows(request.outputs)
        watertight_solid_rows = self._watertight_solid_rows(request.outputs)
        watertight_solid_segment_rows = self._watertight_solid_segment_rows(request.outputs)

        return ExchangeOutput(
            schema_version=1,
            project_id=request.project_id,
            exchange_output_id=request.exchange_output_id,
            format=request.format,
            package_kind=request.package_kind,
            label=f"{request.format.upper()} Package",
            selection_scope={
                "scope_kind": "exchange_package",
                "format": request.format,
                "package_kind": request.package_kind,
            },
            source_refs=source_refs,
            result_refs=result_refs,
            output_refs=output_refs,
            payload_metadata={
                "output_count": len(request.outputs),
                "formats": [request.format],
                "output_kinds": [row.output_kind for row in output_refs],
                "structure_solid_count": self._structure_solid_count(request.outputs),
                "structure_solid_segment_count": self._structure_solid_segment_count(request.outputs),
                "watertight_solid_count": len(watertight_solid_rows),
                "watertight_solid_segment_count": len(watertight_solid_segment_rows),
                "watertight_solid_volume": self._watertight_solid_volume(watertight_solid_rows),
                "source_context_count": len(source_context_rows),
                "watertight_intersection_source_context_count": self._watertight_intersection_source_context_count(
                    source_context_rows
                ),
                "watertight_intersection_surface_zone_context_count": self._watertight_intersection_surface_zone_context_count(
                    source_context_rows
                ),
                "watertight_intersection_diagnostic_ref_count": self._watertight_intersection_diagnostic_ref_count(
                    source_context_rows
                ),
                "simulation_intersection_handoff_context_count": self._source_context_context_kind_count(
                    source_context_rows,
                    context_kind="simulation_package_intersection_handoff",
                ),
                "simulation_intersection_replacement_blocker_kind": self._first_source_context_value(
                    source_context_rows,
                    context_kind="simulation_package_intersection_handoff",
                    attribute_name="replacement_blocker_kind",
                ),
                "simulation_intersection_replacement_blocker_kinds": self._source_context_values(
                    source_context_rows,
                    context_kind="simulation_package_intersection_handoff",
                    attribute_name="replacement_blocker_kind",
                ),
                "side_slope_source_context_count": self._source_context_count(
                    source_context_rows,
                    scope="side_slope",
                ),
                "bench_source_context_count": self._bench_source_context_count(source_context_rows),
                "region_ref_count": len(self._source_ref_values(request.outputs, "region_ref")),
                "assembly_ref_count": len(self._source_ref_values(request.outputs, "assembly_ref")),
                "subassembly_ref_count": len(self._source_ref_values(request.outputs, "subassembly_ref")),
                "compatibility_ref_count": len(self._source_ref_values(request.outputs, "compatibility_ref")),
                "structure_ref_count": len(self._source_ref_values(request.outputs, "structure_ref")),
                "surface_span_count": len(surface_span_rows),
                "surface_transition_span_count": self._surface_transition_span_count(surface_span_rows),
                "surface_transition_diagnostic_count": self._surface_transition_diagnostic_count(diagnostic_rows),
                "diagnostic_count": len(diagnostic_rows),
                "diagnostic_error_count": self._diagnostic_count(request.outputs, severity="error"),
                "diagnostic_warning_count": self._diagnostic_count(request.outputs, severity="warning"),
            },
            format_payload={
                "package_kind": request.package_kind,
                "output_ids": [row.output_id for row in output_refs],
                "structure_solid_rows": self._structure_solid_rows(request.outputs),
                "structure_solid_segment_rows": self._structure_solid_segment_rows(request.outputs),
                "watertight_solid_rows": watertight_solid_rows,
                "watertight_solid_segment_rows": watertight_solid_segment_rows,
                "surface_span_rows": surface_span_rows,
                "source_context_rows": source_context_rows,
                "diagnostic_rows": diagnostic_rows,
            },
        )

    def _output_kind(self, output: OutputModelBase) -> str:
        """Resolve a stable output kind name from one output payload."""

        name = output.__class__.__name__
        if name.endswith("Output"):
            name = name[:-6]
        return name.lower()

    def _output_id(self, output: OutputModelBase) -> str:
        """Resolve the primary output id for one output payload."""

        for attribute_name in (
            "section_output_id",
            "plan_output_id",
            "profile_output_id",
            "surface_output_id",
            "quantity_output_id",
            "earthwork_output_id",
            "mass_haul_output_id",
            "structure_solid_output_id",
            "watertight_solid_output_id",
            "simulation_package_output_id",
            "exchange_output_id",
        ):
            value = getattr(output, attribute_name, "")
            if isinstance(value, str) and value:
                return value
        return output.label or output.__class__.__name__.lower()

    def _unique_list(self, values: object) -> list[str]:
        """Preserve order while removing duplicate string refs."""

        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _structure_solid_count(self, outputs: list[OutputModelBase]) -> int:
        return sum(
            len(list(getattr(output, "solid_rows", []) or []))
            for output in list(outputs or [])
            if self._is_structure_solid_output(output)
        )

    def _structure_solid_segment_count(self, outputs: list[OutputModelBase]) -> int:
        return sum(
            len(list(getattr(output, "solid_segment_rows", []) or []))
            for output in list(outputs or [])
            if self._is_structure_solid_output(output)
        )

    def _structure_solid_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            if not self._is_structure_solid_output(output):
                continue
            output_id = self._output_id(output)
            for row in list(getattr(output, "solid_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _structure_solid_segment_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            if not self._is_structure_solid_output(output):
                continue
            output_id = self._output_id(output)
            for row in list(getattr(output, "solid_segment_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _watertight_solid_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            if not self._is_watertight_solid_output(output):
                continue
            output_id = self._output_id(output)
            for row in list(getattr(output, "solid_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _watertight_solid_segment_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            if not self._is_watertight_solid_output(output):
                continue
            output_id = self._output_id(output)
            for row in list(getattr(output, "segment_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _watertight_solid_volume(self, rows: list[dict[str, object]]) -> float:
        total = 0.0
        for row in list(rows or []):
            if not bool(row.get("is_watertight", False)) or not bool(row.get("is_valid_solid", False)):
                continue
            try:
                total += float(row.get("volume", 0.0) or 0.0)
            except Exception:
                continue
        return total

    def _surface_span_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            output_id = self._output_id(output)
            for row in list(getattr(output, "span_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _source_context_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        seen: set[tuple[str, str, str, str, str, str, str, str]] = set()
        for output in list(outputs or []):
            output_id = self._output_id(output)
            output_kind = self._output_kind(output)
            for payload in self._source_context_payloads(output):
                key = (
                    output_id,
                    str(payload.get("context_kind", "") or ""),
                    str(payload.get("region_ref", "") or ""),
                    str(payload.get("assembly_ref", "") or ""),
                    str(payload.get("structure_ref", "") or ""),
                    str(payload.get("subassembly_ref", "") or ""),
                    str(payload.get("compatibility_ref", "") or ""),
                    str(payload.get("source_row_ref", "") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                payload["context_row_id"] = f"{output_id}:source-context:{len(rows) + 1}"
                payload["output_ref"] = output_id
                payload["output_kind"] = output_kind
                rows.append(payload)
        return rows

    def _source_context_payloads(self, output: OutputModelBase) -> list[dict[str, object]]:
        payloads: list[dict[str, object]] = []
        for row in list(getattr(output, "solid_rows", []) or []):
            if self._is_watertight_solid_output(output):
                source_refs = [str(ref) for ref in list(getattr(row, "source_refs", []) or []) if str(ref)]
                payloads.append(
                    {
                        "context_kind": "watertight_solid",
                        "region_ref": str(getattr(row, "region_ref", "") or ""),
                        "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                        "structure_ref": str(getattr(row, "structure_ref", "") or ""),
                        "drainage_ref": str(getattr(row, "drainage_ref", "") or ""),
                        "flow_route_ref": str(getattr(row, "flow_route_ref", "") or ""),
                        "subassembly_ref": str(getattr(row, "subassembly_ref", "") or ""),
                        "compatibility_ref": str(getattr(row, "compatibility_ref", "") or ""),
                        "source_row_ref": str(getattr(row, "output_object_id", "") or ""),
                        "target_id": str(getattr(row, "target_id", "") or ""),
                        "target_family": str(getattr(row, "target_family", "") or ""),
                        "scope_kind": str(getattr(row, "scope_kind", "") or ""),
                        "material_ref": str(getattr(row, "material_ref", "") or ""),
                        "validation_status": str(getattr(row, "validation_status", "") or ""),
                        "is_watertight": bool(getattr(row, "is_watertight", False)),
                        "station_start": float(getattr(row, "station_start", 0.0) or 0.0),
                        "station_end": float(getattr(row, "station_end", 0.0) or 0.0),
                        "diagnostic_refs": [str(ref) for ref in list(getattr(row, "diagnostic_refs", []) or []) if str(ref)],
                        "notes": str(getattr(row, "notes", "") or ""),
                        "source_refs": source_refs,
                        "intersection_ref": _first_ref_with_prefix(source_refs, "intersection:"),
                        "intersection_leg_ref": _first_ref_with_prefix(source_refs, "intersection-leg:"),
                        "intersection_control_area_ref": _first_ref_with_prefix(source_refs, "intersection-control-area:"),
                        "intersection_edge_family_ref": _first_ref_with_prefix(source_refs, "intersection-edge-family:"),
                        "intersection_surface_zone_ref": _first_ref_with_prefix(source_refs, "intersection-zone:"),
                        "intersection_edge_network_ref": _first_ref_with_prefix(source_refs, "intersection-edge-network:"),
                        "intersection_surface_zone_result_ref": _first_ref_with_prefix(source_refs, "intersection-surface-zones:"),
                    }
                )
            elif self._is_structure_solid_output(output):
                payloads.append(
                    {
                        "context_kind": "structure_solid",
                        "region_ref": str(getattr(row, "region_ref", "") or ""),
                        "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                        "structure_ref": str(getattr(row, "structure_ref", "") or getattr(row, "structure_id", "") or ""),
                        "source_row_ref": str(getattr(row, "output_object_id", "") or ""),
                    }
                )
        if self._is_simulation_package_output(output):
            blocker_kind = str(getattr(output, "intersection_handoff_replacement_blocker_kind", "") or "")
            handoff_status = str(getattr(output, "intersection_handoff_status", "") or "")
            final_quality = str(getattr(output, "intersection_handoff_final_quality_status", "") or "")
            replacement_readiness = str(getattr(output, "intersection_handoff_replacement_readiness_status", "") or "")
            shared_breakline_audit_status = str(getattr(output, "intersection_handoff_shared_breakline_audit_status", "") or "")
            source_refs = [str(ref) for ref in list(getattr(output, "source_refs", []) or []) if str(ref)]
            if blocker_kind or handoff_status or final_quality or replacement_readiness or shared_breakline_audit_status:
                payloads.append(
                    {
                        "context_kind": "simulation_package_intersection_handoff",
                        "scope": "intersection_handoff",
                        "source_row_ref": str(getattr(output, "simulation_package_output_id", "") or ""),
                        "intersection_ref": _first_ref_with_prefix(source_refs, "intersection:"),
                        "final_quality_status": final_quality,
                        "digital_twin_handoff": handoff_status,
                        "replacement_readiness_status": replacement_readiness,
                        "replacement_blocker_kind": blocker_kind,
                        "replacement_gate_status": str(getattr(output, "intersection_handoff_replacement_gate_status", "") or ""),
                        "downstream_selected_role": str(getattr(output, "intersection_handoff_downstream_selected_role", "") or ""),
                        "legacy_patch_review_visibility": str(getattr(output, "intersection_handoff_legacy_patch_review_visibility", "") or ""),
                        "shared_breakline_audit_status": shared_breakline_audit_status,
                        "shared_breakline_geometry_mismatch_count": int(getattr(output, "intersection_handoff_shared_breakline_geometry_mismatch_count", 0) or 0),
                        "shared_breakline_mesh_mismatch_count": int(getattr(output, "intersection_handoff_shared_breakline_mesh_mismatch_count", 0) or 0),
                        "shared_breakline_missing_consumer_count": int(getattr(output, "intersection_handoff_shared_breakline_missing_consumer_count", 0) or 0),
                        "shared_breakline_reversed_edge_count": int(getattr(output, "intersection_handoff_shared_breakline_reversed_edge_count", 0) or 0),
                        "source_refs": source_refs,
                    }
                )
        for row in list(getattr(output, "subassembly_rows", []) or []):
            if not self._is_side_slope_subassembly_row(row):
                continue
            payloads.append(
                {
                    "context_kind": "section_side_slope_subassembly",
                    "scope": "side_slope",
                    "region_ref": str(getattr(row, "region_ref", "") or ""),
                    "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                    "structure_ref": self._structure_ref_from_notes(str(getattr(row, "notes", "") or "")),
                    "source_row_ref": str(
                        getattr(row, "subassembly_row_id", "") or getattr(row, "subassembly_id", "") or ""
                    ),
                    "subassembly_ref": str(getattr(row, "subassembly_id", "") or ""),
                    "compatibility_ref": "",
                    "template_ref": str(getattr(row, "template_ref", "") or ""),
                    "subassembly_kind": str(getattr(row, "kind", "") or ""),
                    "notes": str(getattr(row, "notes", "") or ""),
                }
            )
        for row in list(getattr(output, "fragment_rows", []) or []):
            is_side_slope = self._is_side_slope_quantity_row(row)
            payloads.append(
                {
                    "context_kind": "side_slope_quantity_fragment" if is_side_slope else "quantity_fragment",
                    "scope": "side_slope" if is_side_slope else "",
                    "region_ref": str(getattr(row, "region_ref", "") or ""),
                    "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                    "structure_ref": str(getattr(row, "structure_ref", "") or ""),
                    "drainage_ref": str(getattr(row, "drainage_ref", "") or ""),
                    "flow_route_ref": str(getattr(row, "flow_route_ref", "") or ""),
                    "source_row_ref": str(getattr(row, "fragment_row_id", "") or getattr(row, "fragment_id", "") or ""),
                    "subassembly_ref": str(getattr(row, "subassembly_ref", "") or ""),
                    "compatibility_ref": str(getattr(row, "compatibility_ref", "") or ""),
                    "quantity_kind": str(getattr(row, "quantity_kind", "") or ""),
                    "measurement_kind": str(getattr(row, "measurement_kind", "") or ""),
                }
            )
        for row in list(getattr(output, "span_rows", []) or []):
            payloads.append(
                {
                    "context_kind": "surface_span",
                    "scope": "surface_transition" if str(getattr(row, "transition_ref", "") or "") else "surface_span",
                    "region_ref": str(getattr(row, "from_region_ref", "") or ""),
                    "assembly_ref": "",
                    "structure_ref": "",
                    "source_row_ref": str(getattr(row, "span_row_id", "") or ""),
                    "surface_ref": str(getattr(row, "surface_ref", "") or ""),
                    "from_region_ref": str(getattr(row, "from_region_ref", "") or ""),
                    "to_region_ref": str(getattr(row, "to_region_ref", "") or ""),
                    "transition_ref": str(getattr(row, "transition_ref", "") or ""),
                    "span_kind": str(getattr(row, "span_kind", "") or ""),
                    "continuity_status": str(getattr(row, "continuity_status", "") or ""),
                }
            )
        return [
            payload
            for payload in (_source_context_compatibility_payload(payload) for payload in payloads)
            if any(str(payload.get(key, "") or "") for key in ("region_ref", "assembly_ref", "structure_ref", "subassembly_ref", "compatibility_ref", "intersection_ref", "replacement_blocker_kind"))
        ]

    def _is_structure_solid_output(self, output: OutputModelBase) -> bool:
        return bool(str(getattr(output, "structure_solid_output_id", "") or ""))

    def _is_watertight_solid_output(self, output: OutputModelBase) -> bool:
        return bool(str(getattr(output, "watertight_solid_output_id", "") or ""))

    def _is_simulation_package_output(self, output: OutputModelBase) -> bool:
        return bool(str(getattr(output, "simulation_package_output_id", "") or ""))

    def _is_side_slope_subassembly_row(self, row: object) -> bool:
        kind = str(getattr(row, "kind", "") or "").strip().lower()
        notes = str(getattr(row, "notes", "") or "").strip().lower()
        return kind in _SIDE_SLOPE_SUBASSEMBLY_KINDS or "scope=side_slope" in notes

    def _is_side_slope_quantity_row(self, row: object) -> bool:
        quantity_kind = str(getattr(row, "quantity_kind", "") or "").strip().lower()
        measurement_kind = str(getattr(row, "measurement_kind", "") or "").strip().lower()
        return quantity_kind in _SIDE_SLOPE_QUANTITY_KINDS or measurement_kind in _SIDE_SLOPE_MEASUREMENT_KINDS

    def _structure_ref_from_notes(self, notes: str) -> str:
        for note in str(notes or "").split(";"):
            key, separator, value = note.strip().partition("=")
            if separator and key.strip() == "structure_refs":
                return str(value or "").split(",", 1)[0].strip()
        return ""

    def _source_context_count(
        self,
        source_context_rows: list[dict[str, object]],
        *,
        scope: str,
    ) -> int:
        expected = str(scope or "").strip().lower()
        return sum(
            1
            for row in source_context_rows
            if str(row.get("scope", "") or "").strip().lower() == expected
        )

    def _source_context_context_kind_count(
        self,
        source_context_rows: list[dict[str, object]],
        *,
        context_kind: str,
    ) -> int:
        expected = str(context_kind or "").strip().lower()
        return sum(
            1
            for row in source_context_rows
            if str(row.get("context_kind", "") or "").strip().lower() == expected
        )

    def _watertight_intersection_source_context_count(self, source_context_rows: list[dict[str, object]]) -> int:
        return sum(
            1
            for row in source_context_rows
            if str(row.get("context_kind", "") or "") == "watertight_solid"
            and str(row.get("intersection_ref", "") or "")
        )

    def _watertight_intersection_surface_zone_context_count(self, source_context_rows: list[dict[str, object]]) -> int:
        return sum(
            1
            for row in source_context_rows
            if str(row.get("context_kind", "") or "") == "watertight_solid"
            and str(row.get("intersection_surface_zone_result_ref", "") or "")
        )

    def _watertight_intersection_diagnostic_ref_count(self, source_context_rows: list[dict[str, object]]) -> int:
        return len(
            self._unique_list(
                str(ref)
                for row in source_context_rows
                if str(row.get("context_kind", "") or "") == "watertight_solid"
                and str(row.get("intersection_ref", "") or "")
                for ref in list(row.get("diagnostic_refs", []) or [])
                if str(ref)
            )
        )

    def _source_context_values(
        self,
        source_context_rows: list[dict[str, object]],
        *,
        context_kind: str,
        attribute_name: str,
    ) -> list[str]:
        expected = str(context_kind or "").strip().lower()
        return self._unique_list(
            str(row.get(attribute_name, "") or "")
            for row in source_context_rows
            if str(row.get("context_kind", "") or "").strip().lower() == expected
            and str(row.get(attribute_name, "") or "")
        )

    def _first_source_context_value(
        self,
        source_context_rows: list[dict[str, object]],
        *,
        context_kind: str,
        attribute_name: str,
    ) -> str:
        values = self._source_context_values(
            source_context_rows,
            context_kind=context_kind,
            attribute_name=attribute_name,
        )
        return values[0] if values else ""

    def _bench_source_context_count(self, source_context_rows: list[dict[str, object]]) -> int:
        return sum(
            1
            for row in source_context_rows
            if str(
                row.get("subassembly_kind", "")
                or ""
            )
            .strip()
            .lower()
            == "bench"
            or str(row.get("quantity_kind", "") or "").strip().lower() == "bench_surface_length"
        )

    def _source_ref_values(self, outputs: list[OutputModelBase], attribute_name: str) -> list[str]:
        return self._unique_list(
            str(row.get(attribute_name, "") or "")
            for row in self._source_context_rows(outputs)
            if str(row.get(attribute_name, "") or "")
        )

    def _diagnostic_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            output_id = self._output_id(output)
            for row in list(getattr(output, "diagnostic_rows", []) or []):
                if hasattr(row, "__dataclass_fields__"):
                    payload = asdict(row)
                else:
                    payload = {
                        "severity": str(getattr(row, "severity", "") or ""),
                        "kind": str(getattr(row, "kind", "") or ""),
                        "message": str(getattr(row, "message", "") or ""),
                        "notes": str(getattr(row, "notes", "") or ""),
                    }
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _diagnostic_count(self, outputs: list[OutputModelBase], *, severity: str) -> int:
        expected = str(severity or "").strip().lower()
        return sum(
            1
            for row in self._diagnostic_rows(outputs)
            if str(row.get("severity", "") or "").strip().lower() == expected
        )

    def _surface_transition_span_count(self, surface_span_rows: list[dict[str, object]]) -> int:
        return sum(1 for row in list(surface_span_rows or []) if str(row.get("transition_ref", "") or ""))

    def _surface_transition_diagnostic_count(self, diagnostic_rows: list[dict[str, object]]) -> int:
        return sum(
            1
            for row in list(diagnostic_rows or [])
            if str(row.get("kind", "") or "").startswith("surface_transition")
        )


def _source_context_compatibility_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize explicitly named compatibility provenance in exchange payloads."""

    row = dict(payload or {})
    row["compatibility_ref"] = str(row.get("compatibility_ref", "") or "").strip()
    return row


def _first_ref_with_prefix(source_refs: list[str], prefix: str) -> str:
    expected = str(prefix or "")
    for ref in list(source_refs or []):
        text = str(ref or "").strip()
        if text.startswith(expected):
            return text
    return ""
